import asyncio
import logging
import os
from pathlib import Path

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response, StreamingResponse, RedirectResponse
from starlette.background import BackgroundTask
import httpx
import websockets

logger = logging.getLogger(__name__)


def create_router(workspace_root: Path, auth_checker=None, gateway_checker=None, policy_reader=None) -> APIRouter:
    router = APIRouter()

    async def bridge_websocket(websocket: WebSocket, query: str, checker=None):
        url = f"ws://127.0.0.1:{os.environ.get('COMFY_PORT', '5555')}/ws"
        if query:
            url += "?" + query
        try:
            async with websockets.connect(url, max_size=None) as upstream:
                await websocket.accept()

                async def to_browser():
                    async for message in upstream:
                        if checker is not None and not checker(websocket):
                            await websocket.close(code=4401)
                            return
                        if isinstance(message, bytes):
                            await websocket.send_bytes(message)
                        else:
                            await websocket.send_text(message)

                async def to_comfy():
                    while True:
                        message = await websocket.receive()
                        if message["type"] == "websocket.disconnect":
                            return
                        if checker is not None and not checker(websocket):
                            await websocket.close(code=4401)
                            return
                        await upstream.send(message.get("bytes") if message.get("bytes") is not None else message["text"])

                tasks = [asyncio.create_task(to_browser()), asyncio.create_task(to_comfy())]
                try:
                    await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                finally:
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
        except (OSError, websockets.exceptions.WebSocketException):
            logger.warning("Comfy WebSocket upstream unavailable")
        finally:
            try:
                await websocket.close(code=1000)
            except RuntimeError:
                pass

    @router.websocket("/ws/comfy")
    async def comfy_websocket(websocket: WebSocket):
        if auth_checker is not None and not auth_checker(websocket.cookies):
            await websocket.close(code=4401)
            return
        await bridge_websocket(websocket, "clientId=portal_preview")

    @router.websocket("/comfy/ws")
    async def gateway_websocket(websocket: WebSocket):
        if gateway_checker is None or not gateway_checker(websocket):
            await websocket.close(code=4401)
            return
        await bridge_websocket(websocket, websocket.url.query, gateway_checker)

    @router.get("/comfy")
    async def gateway_root():
        return RedirectResponse("/comfy/", status_code=307)

    @router.api_route("/comfy/{path:path}", methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    async def gateway_http(request: Request, path: str):
        if gateway_checker is None or not gateway_checker(request):
            if not path and request.method == "GET" and "text/html" in request.headers.get("accept", ""):
                return RedirectResponse("/?open=comfyui", status_code=303)
            return JSONResponse({"detail": "ComfyUI login or API token required"}, status_code=401,
                                headers={"WWW-Authenticate": "Bearer", "Cache-Control": "no-store"})
        # Stream uploads and video responses; never forward ControlPilot credentials.
        excluded = {"host", "authorization", "cookie", "connection", "keep-alive", "proxy-authenticate",
                    "proxy-authorization", "te", "trailer", "transfer-encoding", "upgrade"}
        excluded.update(x.strip().lower() for x in request.headers.get("connection", "").split(","))
        headers = {k: v for k, v in request.headers.items() if k.lower() not in excluded}
        base = f"http://127.0.0.1:{os.environ.get('COMFY_PORT', '5555')}"
        url = base + "/" + path
        if request.url.query:
            url += "?" + request.url.query
        client = httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=5.0), follow_redirects=False)
        try:
            upstream = await client.send(client.build_request(request.method, url, headers=headers,
                                                              content=request.stream()), stream=True)
        except httpx.HTTPError:
            await client.aclose()
            return JSONResponse({"detail": "ComfyUI is unavailable"}, status_code=502)
        response_excluded = excluded | {"set-cookie"}
        response_excluded.update(x.strip().lower() for x in upstream.headers.get("connection", "").split(","))
        response_headers = {k: v for k, v in upstream.headers.items() if k.lower() not in response_excluded}
        location = response_headers.get("location", "")
        if location.startswith(base + "/"):
            response_headers["location"] = "/comfy/" + location[len(base) + 1:]
        elif location.startswith("/") and not location.startswith("//"):
            response_headers["location"] = "/comfy" + location
        response_headers["cache-control"] = "no-store"

        async def close_upstream():
            await upstream.aclose()
            await client.aclose()

        return StreamingResponse(upstream.aiter_raw(), status_code=upstream.status_code,
                                 headers=response_headers, background=BackgroundTask(close_upstream))

    @router.get("/api/comfy/status")
    def comfy_status():
        """Check if ComfyUI is running and accessible."""
        comfy_port = os.environ.get("COMFY_PORT", "5555")
        try:
            import requests
            response = requests.get(f"http://localhost:{comfy_port}/system_stats", timeout=5)
            if response.status_code == 200:
                return {"status": "running", "port": comfy_port,
                        "protected": bool(policy_reader and policy_reader()["enabled"])}
            return {"status": "error", "message": "ComfyUI returned error status"}
        except requests.exceptions.RequestException:
            return {"status": "stopped", "message": "ComfyUI is not reachable"}
        except Exception:
            logger.exception("Failed to query ComfyUI status")
            return {"status": "error", "message": "Unable to query ComfyUI"}

    @router.get("/api/comfy/latest-image")
    def comfy_latest_image():
        """Get the latest generated image from ComfyUI output directory."""
        try:
            from datetime import datetime
            from PIL import Image

            output_dir = workspace_root / "outputs" / "comfy"
            if not output_dir.exists():
                return {"image": None, "message": "No output directory found"}

            image_patterns = ["*.png", "*.jpg", "*.jpeg", "*.webp"]
            latest_file = None
            latest_time = None
            image_count = 0

            for pattern in image_patterns:
                for file_path in output_dir.rglob(pattern):
                    if file_path.is_file():
                        image_count += 1
                        file_time = file_path.stat().st_mtime
                        if latest_time is None or file_time > latest_time:
                            latest_time = file_time
                            latest_file = file_path

            if latest_file:
                stat = latest_file.stat()
                file_size = stat.st_size
                rel_path = latest_file.relative_to(output_dir)
                subfolder = rel_path.parent.as_posix() if rel_path.parent != Path(".") else ""
                try:
                    with Image.open(latest_file) as img:
                        dimensions = f"{img.width}x{img.height}"
                except Exception:
                    dimensions = "Unknown"

                image_url = f"/proxy/comfy/view?filename={rel_path.name}"
                if subfolder:
                    image_url += f"&subfolder={subfolder}"
                return {
                    "image": {
                        "url": image_url,
                        "filename": latest_file.name,
                        "subfolder": subfolder,
                        "dimensions": dimensions,
                        "size": file_size,
                        "generated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    },
                    "image_count": image_count,
                }
            return {"image": None, "message": "No images found", "image_count": 0}
        except Exception:
            logger.exception("Failed to inspect latest ComfyUI image")
            return {"image": None, "error": "Unable to inspect ComfyUI output"}

    @router.get("/proxy/comfy/{path:path}")
    async def proxy_comfy(request: Request, path: str):
        """Proxy ComfyUI requests to avoid mixed content issues."""
        comfy_port = os.environ.get("COMFY_PORT", "5555")
        comfy_url = f"http://localhost:{comfy_port}/{path}"

        query_string = str(request.url.query) if request.url.query else ""
        if query_string:
            comfy_url += f"?{query_string}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    comfy_url,
                    headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
                    timeout=30.0,
                )
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.headers.get("content-type", "application/octet-stream"),
                )
        except Exception:
            logger.exception("Comfy proxy request failed for path %s", path)
            return JSONResponse(
                {"error": "Proxy request failed"},
                status_code=500,
            )

    return router
