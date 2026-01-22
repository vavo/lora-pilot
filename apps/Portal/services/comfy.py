import asyncio
import os
from pathlib import Path

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
import httpx
import websockets


def create_router(workspace_root: Path) -> APIRouter:
    router = APIRouter()

    @router.websocket("/ws/comfy")
    async def comfy_websocket(websocket: WebSocket):
        """WebSocket endpoint for ComfyUI live image preview."""
        await websocket.accept()

        comfy_port = os.environ.get("COMFY_PORT", "5555")
        comfy_ws_url = f"ws://localhost:{comfy_port}/ws?clientId=portal_preview"

        try:
            async with websockets.connect(comfy_ws_url) as comfy_ws:
                async def forward_from_comfy():
                    try:
                        async for message in comfy_ws:
                            await websocket.send_text(message)
                    except websockets.exceptions.ConnectionClosed:
                        pass
                    except Exception:
                        pass

                async def forward_to_comfy():
                    try:
                        async for message in websocket.iter_text():
                            await comfy_ws.send(message)
                    except WebSocketDisconnect:
                        pass
                    except Exception:
                        pass

                await asyncio.gather(
                    forward_from_comfy(),
                    forward_to_comfy(),
                    return_exceptions=True,
                )
        except Exception as e:
            try:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Cannot connect to ComfyUI: {str(e)}",
                })
            except Exception:
                pass
        finally:
            try:
                await websocket.close()
            except Exception:
                pass

    @router.get("/api/comfy/status")
    def comfy_status():
        """Check if ComfyUI is running and accessible."""
        comfy_port = os.environ.get("COMFY_PORT", "5555")
        try:
            import requests
            response = requests.get(f"http://localhost:{comfy_port}/system_stats", timeout=5)
            if response.status_code == 200:
                return {"status": "running", "port": comfy_port}
            return {"status": "error", "message": "ComfyUI returned error status"}
        except requests.exceptions.RequestException as e:
            return {"status": "stopped", "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

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
        except Exception as e:
            return {"image": None, "error": str(e)}

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
        except Exception as e:
            return JSONResponse(
                {"error": f"Proxy error: {str(e)}"},
                status_code=500,
            )

    return router
