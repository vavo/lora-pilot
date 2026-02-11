/* -----------------------------------------------------
   API HELPER
----------------------------------------------------- */

import { appUrl } from "./base-path.js";

export async function fetchFolders() {
  const res = await fetch(appUrl("folders"));
  if (!res.ok) throw new Error(`Failed to load folders: ${res.status}`);
  return res.json();
}

export async function createTag(name) {
  assertString("name", name);
  const res = await fetch(appUrl("folders"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error(`Failed to create tag: ${res.status}`);
  return res.json();
}

function assertString(name, value) {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`Invalid ${name}`);
  }
}

function assertNumber(name, value) {
  if (!Number.isFinite(value)) {
    throw new Error(`Invalid ${name}`);
  }
}

function assertOptionalString(name, value) {
  if (value === undefined || value === null) return;
  if (typeof value !== "string") {
    throw new Error(`Invalid ${name}`);
  }
}

function assertStringArray(name, value) {
  if (!Array.isArray(value) || value.length === 0) {
    throw new Error(`Invalid ${name}`);
  }
  value.forEach((item, index) => {
    if (typeof item !== "string" || item.trim() === "") {
      throw new Error(`Invalid ${name}[${index}]`);
    }
  });
}

function parseFilenameFromDisposition(headerValue) {
  if (typeof headerValue !== "string" || headerValue.trim() === "") return null;
  const utf8Match = headerValue.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match && utf8Match[1]) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch {
      return utf8Match[1];
    }
  }
  const plainMatch = headerValue.match(/filename=\"?([^\";]+)\"?/i);
  return plainMatch?.[1] || null;
}

export async function fetchImages(page, limit, folder, sort, search = "") {
  const pageNum = Number(page);
  const limitNum = Number(limit);
  assertNumber("page", pageNum);
  assertNumber("limit", limitNum);
  assertString("folder", folder);
  assertString("sort", sort);
  assertOptionalString("search", search);
  const params = new URLSearchParams({
    page: String(pageNum),
    limit: String(limitNum),
    folder,
    sort,
  });
  if (search && search.trim() !== "") {
    params.set("search", search.trim());
  }
  const res = await fetch(appUrl(`images?${params.toString()}`));
  if (!res.ok) throw new Error(`Failed to load images: ${res.status}`);
  return res.json();
}

export async function sendLike(filename, liked) {
  assertString("filename", filename);
  if (typeof liked !== "boolean") {
    throw new Error("Invalid liked state");
  }
  const endpoint = appUrl(
    liked
      ? `like/${encodeURIComponent(filename)}`
      : `unlike/${encodeURIComponent(filename)}`
  );

  const res = await fetch(endpoint, { method: "POST" });
  if (!res.ok) throw new Error(`Server returned ${res.status}`);
  return true;
}

export async function sendTag(filename, oldFolder, newFolder) {
  assertString("filename", filename);
  assertString("oldFolder", oldFolder);
  assertString("newFolder", newFolder);
  const safeOldFolder = encodeURIComponent(oldFolder);
  const safeNewFolder = encodeURIComponent(newFolder);
  const res = await fetch(
    appUrl(
      `tag?filename=${encodeURIComponent(filename)}&old_folder=${safeOldFolder}&new_folder=${safeNewFolder}`
    ),
    { method: "POST" }
  );
  if (!res.ok) throw new Error(`Failed to tag ${filename}`);
}

export async function deleteImage(filename, folder) {
  assertString("filename", filename);
  assertString("folder", folder);
  const safeFilename = encodeURIComponent(filename);
  const safeFolder = folder
    .split("/")
    .map((part) => encodeURIComponent(part))
    .join("/");
  const endpoint = appUrl(
    folder === "_root"
      ? `image/${safeFilename}`
      : `image/${safeFolder}/${safeFilename}`
  );
  const res = await fetch(endpoint, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete ${filename}`);
}

export async function downloadBulk(folder, filenames) {
  assertString("folder", folder);
  assertStringArray("filenames", filenames);

  const res = await fetch(appUrl("download/bulk"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ folder, filenames }),
  });
  if (!res.ok) throw new Error(`Failed to download selection: ${res.status}`);

  const blob = await res.blob();
  const contentDisposition = res.headers.get("content-disposition");
  const filename =
    parseFilenameFromDisposition(contentDisposition) || "mediapilot-selection.zip";
  return { blob, filename };
}

export async function upscaleBulk(folder, filenames) {
  assertString("folder", folder);
  assertStringArray("filenames", filenames);

  const res = await fetch(appUrl("upscale/bulk"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ folder, filenames }),
  });

  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = body?.detail;
    let message = `Server returned ${res.status}`;
    if (typeof detail === "string" && detail.trim()) {
      message = detail;
    } else if (detail && typeof detail === "object" && Array.isArray(detail.failed)) {
      message = `Failed to queue jobs (${detail.failed.length} failed).`;
    }
    throw new Error(message);
  }
  return body;
}
