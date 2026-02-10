console.log("MODAL JS LOADED");

// Versioned import to keep modules aligned with cache-busting.
import {
  resetGallery,
  loadImages,
  loadFolders,
  imagesList,
  visibleImages,
  tagsList,
  currentPage,
  totalPages,
  loading,
  currentFolder,
  toggleLike as galleryToggleLike,
  markImageDeleted,
  ensureTagsLoaded,
} from "./gallery.js?v=cb23";
import * as API from "./gallery-api.js?v=cb23";

let modalFilename = null;

let modalFolder = "_root";
let modalPromptText = null;
let promptVisible = false;

let modalCurrentMetaData = null; // NEW: Store current image's full metadata
const LORA_REGEX = /<lora:([^>:]+)/i;

let modal, modalImg, modalDelete, modalDownload, modalTag, modalImageWrap;
let modalNavLeft, modalNavRight;
let filenameOverlay, promptOverlay, modalHeart;
let lastModalTapTime = 0;

// Add styles for delete button and loading state
const style = document.createElement('style');
style.textContent = `
  #modal-delete {
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
  }
  
  #modal-delete.deleting {
    color: transparent !important;
    pointer-events: none;
  }
  
  #modal-delete.deleting::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 20px;
    height: 20px;
    margin: -10px 0 0 -10px;
    border: 2px solid var(--mp-spinner-track, rgba(148, 163, 184, 0.45));
    border-top-color: var(--mp-spinner-color, #ffffff);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
`;
document.head.appendChild(style);

function notify(message) {
  if (window.showToast) window.showToast(message);
}

async function copyTextToClipboard(text) {
  const value = (text || "").trim();
  if (!value) return false;
  try {
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      await navigator.clipboard.writeText(value);
      return true;
    }
  } catch (_) {
    // Fallback below
  }

  const area = document.createElement("textarea");
  area.value = value;
  area.setAttribute("readonly", "");
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.appendChild(area);
  area.select();
  const success = document.execCommand("copy");
  document.body.removeChild(area);
  return success;
}

function isNonEmptyString(value) {
  return typeof value === "string" && value.trim() !== "";
}

function isReservedTagName(value) {
  const name = (value || "").trim().toLowerCase();
  return name === "untagged" || name === "invokeai" || name === "_root";
}

const MAG_SIZE = 160;
const MAG_DELAY = 300;

function initModalDOM() {
    modal = document.getElementById("modal");
    modalImg = document.getElementById("modal-img");
    modalDelete = document.getElementById("modal-delete");
    modalDownload = document.getElementById("modal-download");
    modalTag = document.getElementById("modal-tag");
    modalImageWrap = document.getElementById("modal-image-wrap"); // Use ID for reliability
    modalNavLeft = document.getElementById("modal-nav-left");
    modalNavRight = document.getElementById("modal-nav-right");
    modalHeart = document.getElementById("modal-heart-overlay");

    modal.onclick = (e) => {
      if (e.target.id === "modal") closeModal();
    };

    modalNavLeft.onclick = (e) => {
      e.stopPropagation();
      void navigate(-1);
    };
    modalNavRight.onclick = (e) => {
      e.stopPropagation();
      void navigate(1);
    };
    if (modalHeart) {
      modalHeart.onclick = (e) => {
        e.stopPropagation();
        likeFile();
      };
    }
    if (modalImg) {
      modalImg.addEventListener("click", (e) => {
        const now = Date.now();
        const isDouble =
          e.detail >= 2 || (lastModalTapTime && now - lastModalTapTime < 300);
        lastModalTapTime = now;
        if (isDouble) {
          e.preventDefault();
          e.stopPropagation();
          likeFile();
        }
      });
    }
    if (modal) {
      modal.addEventListener(
        "mousemove",
        (e) => {
          lastMousePos = { x: e.clientX, y: e.clientY };
          if (magnifierActive) {
            updateMagnifierPosition(e.clientX, e.clientY);
          }
        },
        true
      );
      modal.addEventListener("mouseleave", () => {
        lastMousePos = null;
        if (magnifierActive) hideMagnifier();
      });
    }

    if (modalDownload) {
      modalDownload.onclick = (e) => {
        e.stopPropagation();
        downloadFile();
      };
    }
    if (modalDelete) {
      modalDelete.onclick = async (e) => {
        e.stopPropagation();
        e.preventDefault();
        await deleteFile();
      };
    }
    if (modalTag) {
      modalTag.onclick = () => void showTagDropdown();
      modalTag.classList.add("icon-button");
      updateTagIcon(false);
    }
}

/* -----------------------------------------------------
   OPEN / CLOSE
----------------------------------------------------- */

function updateModalHeart(liked) {
  if (modalHeart) {
    modalHeart.classList.toggle("liked", !!liked);
    modalHeart.textContent = liked ? "❤️" : "♡";
    modalHeart.setAttribute("aria-label", liked ? "Unlike" : "Like");
    modalHeart.setAttribute("aria-pressed", liked ? "true" : "false");
  }
}

export function openModal(filename, folder, openTag = false) {
  if (!isNonEmptyString(filename)) return;
  modalFilename = filename;
  // No longer assigning to modalImages
  modalFolder = isNonEmptyString(folder) ? folder : "_root";

  modalImg.src = buildFullUrl(filename);

  modal.classList.remove("hidden");
  modal.focus();

  const currentIndex = visibleImages.findIndex((img) => img.filename === filename);
  const currentImage = visibleImages[currentIndex];

  modalPromptText = currentImage?.prompt || null;
  modalCurrentMetaData = currentImage; // NEW: Store the whole object

  promptVisible = false;
  const displayName =
    sanitizeLoraName(currentImage?.lora_name) ||
    extractLoraFromPrompt(currentImage?.prompt) ||
    filename;
  // NEW: hasPrompt check now considers any available metadata
  addFilenameOverlay(
    displayName,
    !!modalPromptText ||
      !!modalCurrentMetaData?.steps ||
      !!modalCurrentMetaData?.cfg ||
      !!modalCurrentMetaData?.sampler ||
      !!modalCurrentMetaData?.scheduler ||
      !!modalCurrentMetaData?.lora_name ||
      !!modalCurrentMetaData?.lora_strength ||
      !!modalCurrentMetaData?.lora_name_2 ||
      !!modalCurrentMetaData?.lora_strength_2
  );
  updatePromptOverlay();
  updateModalHeart(currentImage?.liked ?? false);

  updateTagIcon(currentImage?.tagged ?? false);
  PreloadManager.update(currentIndex, visibleImages);

  if (openTag) void showTagDropdown();
}

export function closeModal() {
  modal.classList.add("hidden");
  modalFilename = null;
  modalPromptText = null;
  modalCurrentMetaData = null; // NEW: Clear metadata on close
  promptVisible = false;
  updatePromptOverlay();
  updateModalHeart(false);
  hideMagnifier();
  if (tagDropdown) {
    tagDropdown.remove();
    tagDropdown = null;
  }

}

function addFilenameOverlay(name, hasPrompt) {
  if (filenameOverlay) {
    filenameOverlay.remove();
    filenameOverlay = null;
  }

  if (!name) return;

  filenameOverlay = document.createElement("div");
  filenameOverlay.className = "filename-overlay";
  filenameOverlay.textContent = name;
  if (hasPrompt) {
    filenameOverlay.classList.add("has-prompt");
    filenameOverlay.onclick = (e) => {
      e.stopPropagation();
      promptVisible = !promptVisible;
      updatePromptOverlay();
    };
  }
  modalImageWrap.appendChild(filenameOverlay);
}

function updatePromptOverlay() {
  if (promptOverlay) {
    promptOverlay.remove();
    promptOverlay = null;
  }

  if (!promptVisible || !modalCurrentMetaData) return;

  promptOverlay = document.createElement("div");
  promptOverlay.className = "prompt-overlay";
  promptOverlay.onclick = (e) => e.stopPropagation();

  const {
    prompt,
    lora_name,
    lora_strength,
    cfg,
    steps,
    sampler,
    scheduler,
  } = modalCurrentMetaData;

  const normalizedPrompt = isNonEmptyString(prompt) ? prompt.trim() : "";
  const loraName = sanitizeLoraName(lora_name) || extractLoraFromPrompt(normalizedPrompt);

  const container = document.createElement("div");
  container.className = "metadata-container";

  if (normalizedPrompt) {
    const promptLabel = document.createElement("div");
    promptLabel.className = "metadata-label";
    promptLabel.textContent = "Prompt (tap to copy)";

    const promptButton = document.createElement("button");
    promptButton.type = "button";
    promptButton.className = "prompt-text";
    promptButton.textContent = normalizedPrompt;
    promptButton.onclick = async (e) => {
      e.stopPropagation();
      const copied = await copyTextToClipboard(normalizedPrompt);
      notify(copied ? "Prompt copied." : "Copy failed.");
    };

    container.appendChild(promptLabel);
    container.appendChild(promptButton);
  }

  const details = document.createElement("div");
  details.className = "metadata-section";

  const appendLine = (label, value) => {
    if (value === null || value === undefined || value === "") return;
    const line = document.createElement("div");
    line.className = "metadata-line";
    const strong = document.createElement("strong");
    strong.textContent = `${label}:`;
    const span = document.createElement("span");
    span.textContent = ` ${value}`;
    line.appendChild(strong);
    line.appendChild(span);
    details.appendChild(line);
  };

  appendLine("LoRA", loraName || "");
  appendLine("LoRA strength", lora_strength);
  appendLine("CFG", cfg);
  appendLine("Steps", steps);
  appendLine("Sampler", sampler);
  appendLine("Scheduler", scheduler);

  if (!details.childElementCount && !normalizedPrompt) {
    const empty = document.createElement("div");
    empty.className = "metadata-line";
    empty.textContent = "No readable metadata found.";
    details.appendChild(empty);
  }

  container.appendChild(details);
  promptOverlay.appendChild(container);

  const closeButton = document.createElement("button");
  closeButton.className = "close-button";
  closeButton.innerHTML = "&times;";
  closeButton.onclick = (e) => {
    e.stopPropagation();
    promptVisible = false;
    updatePromptOverlay();
  };
  promptOverlay.appendChild(closeButton);

  modalImageWrap.appendChild(promptOverlay);
}

function animateSwipe(direction, callback) {
  if (!modalImg) {
    if (callback) callback();
    return;
  }

  const cls = direction === "right" ? "swipe-right" : "swipe-left";
  modalImg.classList.remove("swipe-left", "swipe-right");
  void modalImg.offsetWidth; // Force reflow
  modalImg.classList.add(cls);

  const runCallback = () => {
    try {
      const result = callback && callback();
      if (result && typeof result.then === "function") {
        result.catch((err) =>
          console.error("Swipe callback error", err)
        );
      }
    } catch (err) {
      console.error("Swipe callback error", err);
    }
  };

  const cleanup = () => {
    modalImg.classList.remove(cls);
    modalImg.removeEventListener("animationend", cleanup);
    runCallback();
  };

  modalImg.addEventListener("animationend", cleanup);
}

function buildFullUrl(filename) {
  return buildFullUrlForFolder(filename, modalFolder);
}

function buildFullUrlForFolder(filename, folder) {
  const safeFilename = encodeURIComponent(filename);
  if (folder === "_root") return `./output/${safeFilename}`;
  if (folder === "InvokeAI") return `./invoke/${safeFilename}`;
  const safeFolder = (folder || "")
    .split("/")
    .map((part) => encodeURIComponent(part))
    .join("/");
  return `./output/${safeFolder}/${safeFilename}`;
}

/* -----------------------------------------------------
   MAGNIFIER
----------------------------------------------------- */
let magnifierEl = null;
let magnifierActive = false;
let lastMousePos = null;

function toggleMagnifierAtCursor() {
  if (!modalImg) return;
  if (magnifierActive) {
    hideMagnifier();
    return;
  }
  if (lastMousePos && isPointInImage(lastMousePos.x, lastMousePos.y)) {
    showMagnifier(lastMousePos.x, lastMousePos.y);
    return;
  }
  if (!lastMousePos) {
    const rect = modalImg.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    showMagnifier(cx, cy);
  }
}

export function showMagnifier(clientX, clientY) {
  if (!modalImg || !modalImageWrap) return;
  
  // Ensure image has loaded and has natural dimensions
  if (modalImg.naturalWidth === 0 || modalImg.naturalHeight === 0) {
    console.warn("Magnifier: Image natural dimensions are 0. Cannot show magnifier.");
    return;
  }
  if (!isPointInImage(clientX, clientY)) return;

  magnifierActive = true;
  if (!magnifierEl) {
    magnifierEl = document.createElement("div");
    magnifierEl.className = "magnifier";
    document.body.appendChild(magnifierEl); // Appending to document.body
  }
  magnifierEl.style.backgroundImage = `url(${modalImg.src})`;
  const natW = modalImg.naturalWidth;
  const natH = modalImg.naturalHeight;
  const zoom = getMagnifierZoom();
  magnifierEl.style.backgroundSize = `${natW * zoom}px ${natH * zoom}px`;
  updateMagnifierPosition(clientX, clientY);
}

function getRenderedImageDimensions(img) { // This helper is excellent, keep as is.
  const naturalWidth = img.naturalWidth;
  const naturalHeight = img.naturalHeight;
  const clientWidth = img.clientWidth;
  const clientHeight = img.clientHeight;

  const imgRatio = naturalWidth / naturalHeight;
  const containerRatio = clientWidth / clientHeight;

  let renderedWidth, renderedHeight;

  if (imgRatio > containerRatio) {
    // Image is wider than container, scaled to fit width
    renderedWidth = clientWidth;
    renderedHeight = clientWidth / imgRatio;
  } else {
    // Image is taller than container or same ratio, scaled to fit height
    renderedHeight = clientHeight;
    renderedWidth = clientHeight * imgRatio;
  }

  return {
    width: renderedWidth,
    height: renderedHeight,
    xOffset: (clientWidth - renderedWidth) / 2, // X offset from clientLeft
    yOffset: (clientHeight - renderedHeight) / 2  // Y offset from clientTop
  };
}

function getRenderedBounds() {
  if (!modalImg) return null;
  const rect = modalImg.getBoundingClientRect();
  const rendered = getRenderedImageDimensions(modalImg);
  const left = rect.left + rendered.xOffset;
  const top = rect.top + rendered.yOffset;
  const right = left + rendered.width;
  const bottom = top + rendered.height;
  return { left, top, right, bottom, rendered };
}

function getMagnifierSize() {
  if (!magnifierEl) return MAG_SIZE;
  const size = parseFloat(window.getComputedStyle(magnifierEl).width);
  return Number.isFinite(size) && size > 0 ? size : MAG_SIZE;
}

function getMagnifierZoom() {
  const value = window
    .getComputedStyle(document.documentElement)
    .getPropertyValue("--mag-zoom");
  const zoom = parseFloat(value);
  return Number.isFinite(zoom) && zoom > 0 ? zoom : 4;
}

function isPointInImage(clientX, clientY) {
  const bounds = getRenderedBounds();
  if (!bounds) return false;
  return (
    clientX >= bounds.left &&
    clientX <= bounds.right &&
    clientY >= bounds.top &&
    clientY <= bounds.bottom
  );
}

export function updateMagnifierPosition(clientX, clientY) {
  if (!magnifierEl || !modalImg) return;
  const bounds = getRenderedBounds();
  if (!bounds) return;
  if (!isPointInImage(clientX, clientY)) {
    hideMagnifier();
    return;
  }
  const magSize = getMagnifierSize();
  const zoom = getMagnifierZoom();

  // Calculate cursor position relative to the *rendered image pixels*
  const cursorXInRendered = clientX - bounds.left;
  const cursorYInRendered = clientY - bounds.top;

  // Ratios within the rendered image, clamped to [0, 1]
  const rx = Math.max(0, Math.min(1, cursorXInRendered / bounds.rendered.width));
  const ry = Math.max(0, Math.min(1, cursorYInRendered / bounds.rendered.height));

  const bgX = rx * modalImg.naturalWidth * zoom - magSize / 2;
  const bgY = ry * modalImg.naturalHeight * zoom - magSize / 2;

  magnifierEl.style.left = `${clientX - magSize / 2}px`;
  magnifierEl.style.top = `${clientY - magSize / 2}px`;
  magnifierEl.style.backgroundPosition = `-${bgX}px -${bgY}px`;
}

export function hideMagnifier() {
  magnifierActive = false;
  if (magnifierEl) {
    magnifierEl.remove();
    magnifierEl = null;
  }
}

function extractLoraFromPrompt(text) {
  if (!text) return null;
  const match = text.match(LORA_REGEX);
  let loraName = match ? match[1] : null;
  return sanitizeLoraName(loraName);
}

function sanitizeLoraName(name) {
  if (!name) return null;
  const trimmed = String(name).trim();
  if (!trimmed) return null;
  if (trimmed.toLowerCase().endsWith(".safetensors")) {
    return trimmed.substring(0, trimmed.length - ".safetensors".length);
  }
  return trimmed;
}

/* -----------------------------------------------------
   NAV
----------------------------------------------------- */

async function navigate(delta) {
  const idx = visibleImages.findIndex((i) => i.filename === modalFilename);
  if (idx === -1) return;
  const next = idx + delta;

  // Load more images if approaching the end (or at the end in modal).
  if (next >= visibleImages.length - 5 && currentPage < totalPages && !loading) {
    if (next >= visibleImages.length) {
      await loadImages(currentPage + 1, true);
    } else {
      loadImages(currentPage + 1, true);
    }
  }

  if (next < 0 || next >= visibleImages.length) return;

  openModal(visibleImages[next].filename, modalFolder);
}

function getGridColumns() {
  const cards = Array.from(document.querySelectorAll("#gallery .card"));
  if (cards.length === 0) return 1;
  const firstTop = cards[0].getBoundingClientRect().top;
  let cols = 0;
  for (const card of cards) {
    const top = card.getBoundingClientRect().top;
    if (Math.abs(top - firstTop) <= 2) {
      cols += 1;
    } else {
      break;
    }
  }
  return Math.max(1, cols);
}

async function moveVertical(direction) {
  const idx = visibleImages.findIndex((i) => i.filename === modalFilename);
  if (idx === -1) return;
  const cols = getGridColumns();
  const nextIndex = idx + direction * cols;

  if (nextIndex < 0) return;

  if (nextIndex >= visibleImages.length && currentPage < totalPages && !loading) {
    await loadImages(currentPage + 1, true);
  }

  if (nextIndex < 0 || nextIndex >= visibleImages.length) return;

  openModal(visibleImages[nextIndex].filename, modalFolder);
}

/* -----------------------------------------------------
   KEYBOARD SHORTCUTS
----------------------------------------------------- */

window.addEventListener("keydown", (e) => {
  if (!modalFilename) return;

  if (e.key === "Escape") {
    e.preventDefault();
    closeModal();
    return;
  }

  if (e.key === "Backspace") {
    e.preventDefault();
    deleteFile();
    return;
  }

  if (e.key === "Delete") {
    e.preventDefault();
    deleteFile();
    return;
  }

  if (e.key === "ArrowLeft") {
    e.preventDefault();
    void navigate(-1);
  }

  if (e.key === "ArrowRight") {
    e.preventDefault();
    void navigate(1);
  }

  if (e.key === "ArrowUp") {
    e.preventDefault();
    void moveVertical(-1);
  }

  if (e.key === "ArrowDown") {
    e.preventDefault();
    void moveVertical(1);
  }

  if (e.key === " ") {
    e.preventDefault();
    likeFile();
  }

  if (e.key === "Enter") {
    e.preventDefault();
    void showTagDropdown();
    return;
  }

  if ((e.key || "").toLowerCase() === "m") {
    e.preventDefault();
    toggleMagnifierAtCursor();
  }
});

/* -----------------------------------------------------
   ACTIONS
----------------------------------------------------- */

function updateTagIcon(isTagged) {
  if (modalTag) {
    modalTag.classList.toggle("tagged", !!isTagged);
    modalTag.setAttribute("aria-pressed", isTagged ? "true" : "false");
  }
}

async function likeFile() {
    if (!modalFilename) return;
    const card = document.querySelector(`.card[data-filename="${modalFilename}"]`);
    const currentLiked = isLiked(modalFilename);
    const success = await galleryToggleLike(card, modalFilename);
    if (success) setLikedState(modalFilename, !currentLiked);
}

function isLiked(filename) {
  const modalEntry = visibleImages.find((img) => img.filename === filename);
  if (modalEntry && typeof modalEntry.liked === "boolean") return modalEntry.liked;

  const galleryEntry = imagesList.find((img) => img.filename === filename);
  if (galleryEntry && typeof galleryEntry.liked === "boolean") return galleryEntry.liked;

  const card = document.querySelector(`.card[data-filename="${filename}"]`);
  if (card) {
    const heart = card.querySelector(".heart-overlay");
    if (heart) return heart.classList.contains("liked");
  }

  return false;
}

function setLikedState(filename, liked) {
  const updateList = (list) => {
    const entry = list.find((img) => img.filename === filename);
    if (entry) entry.liked = liked;
  };
  updateList(imagesList);
  updateList(visibleImages);
  updateModalHeart(liked);
}

/* -----------------------------------------------------
   DELETE
----------------------------------------------------- */

let deleteInFlight = false;

async function invalidateImageCache(url) {
  if (!url || !("caches" in window)) return;
  try {
    const keys = await caches.keys();
    await Promise.all(
      keys.map(async (key) => {
        const cache = await caches.open(key);
        await cache.delete(url);
      })
    );
  } catch (error) {
    console.warn("Failed to invalidate cache:", error);
  }
}

async function deleteFile() {
  if (deleteInFlight || !isNonEmptyString(modalFilename)) return;
  deleteInFlight = true;
  if (modalDelete) modalDelete.disabled = true;

  const currentIndex = visibleImages.findIndex(
    (img) => img.filename === modalFilename
  );
  if (currentIndex === -1) {
    deleteInFlight = false;
    if (modalDelete) modalDelete.disabled = false;
    closeModal();
    return;
  }

  const currentImage = visibleImages[currentIndex];
  const folderToDelete =
    isNonEmptyString(modalFolder)
      ? modalFolder
      : isNonEmptyString(currentFolder)
        ? currentFolder
        : "_root";
  modalFolder = folderToDelete;

  try {
    await API.deleteImage(modalFilename, folderToDelete);
  } catch (error) {
    console.error("Failed to delete image:", error);
    notify("Failed to delete image.");
    deleteInFlight = false;
    if (modalDelete) modalDelete.disabled = false;
    return;
  }

  void invalidateImageCache(buildFullUrlForFolder(modalFilename, folderToDelete));
  if (currentImage?.thumb_url) {
    void invalidateImageCache(currentImage.thumb_url);
  }
  PreloadManager.forget?.(modalFilename);

  const card = document.querySelector(`.card[data-filename="${modalFilename}"]`);
  if (card) card.remove();

  markImageDeleted(modalFilename);

  if (visibleImages.length === 0 && currentPage < totalPages && !loading) {
    await loadImages(currentPage + 1, true);
  }
  if (visibleImages.length === 0) {
    deleteInFlight = false;
    if (modalDelete) modalDelete.disabled = false;
    closeModal();
    return;
  }

  const nextIndex = Math.min(currentIndex, visibleImages.length - 1);
  openModal(visibleImages[nextIndex].filename, folderToDelete);

  deleteInFlight = false;
  if (modalDelete) modalDelete.disabled = false;
}

function downloadFile() {
  if (!modalFilename || !modalImg.src) return;

  const a = document.createElement("a");
  a.href = modalImg.src;
  a.download = modalFilename; // Use modalFilename as the download name
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

/* -----------------------------------------------------
   TAGGING
----------------------------------------------------- */

let tagDropdown = null;

function appendAddTagOption(container, onCreated) {
  const wrap = document.createElement("div");
  wrap.className = "tag-add";
  const addBtn = document.createElement("button");
  addBtn.type = "button";
  addBtn.className = "tag-add-button";
  addBtn.textContent = "Add new tag";
  wrap.appendChild(addBtn);
  container.appendChild(wrap);

  const reset = () => {
    wrap.innerHTML = "";
    wrap.appendChild(addBtn);
  };

  const showForm = () => {
    wrap.innerHTML = "";
    const label = document.createElement("label");
    label.className = "tag-add-label";
    label.textContent = "Name your tag";
    const input = document.createElement("input");
    input.type = "text";
    input.className = "tag-add-input";
    input.autocomplete = "off";
    const actions = document.createElement("div");
    actions.className = "tag-add-actions";
    const createBtn = document.createElement("button");
    createBtn.type = "button";
    createBtn.className = "tag-add-submit";
    createBtn.textContent = "Create";
    const cancelBtn = document.createElement("button");
    cancelBtn.type = "button";
    cancelBtn.className = "tag-add-cancel";
    cancelBtn.textContent = "Cancel";
    actions.append(createBtn, cancelBtn);
    wrap.append(label, input, actions);
    input.focus();

    const submit = async () => {
      const name = input.value.trim();
      if (!name) {
        input.focus();
        return;
      }
      if (isReservedTagName(name)) {
        notify("That tag name is reserved.");
        input.focus();
        return;
      }
      createBtn.disabled = true;
      cancelBtn.disabled = true;
      try {
        await API.createTag(name);
        await loadFolders();
        await onCreated();
      } catch (error) {
        console.error("Failed to create tag:", error);
        notify("Failed to create tag.");
        createBtn.disabled = false;
        cancelBtn.disabled = false;
      }
    };

    createBtn.onclick = (e) => {
      e.stopPropagation();
      void submit();
    };
    cancelBtn.onclick = (e) => {
      e.stopPropagation();
      reset();
    };
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        void submit();
      } else if (e.key === "Escape") {
        e.preventDefault();
        reset();
      }
    });
  };

  addBtn.onclick = (e) => {
    e.stopPropagation();
    showForm();
  };
}

async function showTagDropdown() {
  if (tagDropdown) tagDropdown.remove();

  await ensureTagsLoaded();

  tagDropdown = document.createElement("div");
  tagDropdown.className = "tag-dropdown";
  tagDropdown.style.position = "absolute";
  tagDropdown.style.bottom = "-10px";
  tagDropdown.style.left = "50%";
  tagDropdown.style.transform = "translateX(-50%)";

  if (tagsList.length === 0) {
    const empty = document.createElement("div");
    empty.className = "tag-dropdown-empty";
    empty.textContent = "No tags found";
    tagDropdown.appendChild(empty);
  } else {
    tagsList.forEach((tag) => {
      const btn = document.createElement("button");
      btn.className = "tag-dropdown-option";
      btn.textContent = tag;
      btn.onclick = () => applyTag(tag);
      tagDropdown.appendChild(btn);
    });
  }

  appendAddTagOption(tagDropdown, async () => {
    await showTagDropdown();
  });

  document.querySelector(".modal-inner").appendChild(tagDropdown);
}

async function applyTag(tag) {
  if (!isNonEmptyString(tag) || !isNonEmptyString(modalFilename)) return;
  const newFolder = tag === "Untagged" ? "_root" : tag;

  try {
    await API.sendTag(modalFilename, modalFolder, newFolder);
  } catch (error) {
    console.error("Failed to tag image:", error);
    notify("Failed to tag image.");
    return;
  }

  const currentIndex = visibleImages.findIndex((img) => img.filename === modalFilename);

  const card = document.querySelector(`.card[data-filename="${modalFilename}"]`);
  if (card) card.remove();

  removeFromLists(modalFilename);
  if (tagDropdown) {
    tagDropdown.remove();
    tagDropdown = null;
  }

  updateTagIcon(newFolder !== "_root");

  advanceAfterRemoval(currentIndex);
  resetGallery();
  loadImages(1, false);
}

function removeFromLists(filename) {
  const removeFrom = (list) => {
    for (let i = list.length - 1; i >= 0; i--) {
      if (list[i].filename === filename) {
        list.splice(i, 1);
      }
    }
  };

  removeFrom(imagesList);
  removeFrom(visibleImages);
}

function advanceAfterRemoval(previousIndex) {
  if (visibleImages.length === 0) {
    closeModal();
    return;
  }

  const nextIndex =
    previousIndex >= visibleImages.length
      ? visibleImages.length - 1
      : previousIndex;

  openModal(visibleImages[nextIndex].filename, modalFolder);
}

/* -----------------------------------------------------
   INTERACTION MANAGER (New)
----------------------------------------------------- */

class InteractionManager {
    constructor(element, options) {
        this.element = element;
        this.options = {
            swipeThreshold: 120,
            maxVerticalSwipe: 120,
            longPressDelay: 300,
            ...options,
        };

        this.activePointers = new Map();
        this.longPressTimer = null;
        this.interactionState = 'idle'; // 'idle', 'pressing', 'swiping', 'magnifying', 'pinching'

        this.element.addEventListener('pointerdown', this.onPointerDown.bind(this));
        window.addEventListener('pointermove', this.onPointerMove.bind(this), { passive: false });
        window.addEventListener('pointerup', this.onPointerUp.bind(this));
        window.addEventListener('pointercancel', this.onPointerUp.bind(this));
        this.element.addEventListener('click', (e) => {
            if (this.interactionState !== 'idle') e.preventDefault();
        }, true);
    }

    onPointerDown(e) {
        if (e.button !== 0) return;
        this.activePointers.set(e.pointerId, { x: e.clientX, y: e.clientY, startX: e.clientX, startY: e.clientY });

        if (this.activePointers.size >= 2) {
            this.clearLongPress();
            this.interactionState = 'pinching';
            this.options.onPinchStart?.(this.getCenter());
        } else if (this.interactionState === 'idle') {
            this.interactionState = 'pressing';
            this.longPressTimer = setTimeout(() => {
                if (this.interactionState === 'pressing') {
                    this.interactionState = 'magnifying';
                    this.options.onLongPress?.(this.activePointers.get(e.pointerId));
                }
            }, this.options.longPressDelay);
        }
    }

    onPointerMove(e) {
        if (!this.activePointers.has(e.pointerId)) return;
        this.activePointers.get(e.pointerId).x = e.clientX;
        this.activePointers.get(e.pointerId).y = e.clientY;

        if (this.interactionState === 'pinching') {
            e.preventDefault();
            this.options.onPinchMove?.(this.getCenter());
        } else if (this.interactionState === 'magnifying') {
            e.preventDefault();
            this.options.onMagnifyMove?.({ x: e.clientX, y: e.clientY });
        } else if (this.interactionState === 'pressing') {
            const pointer = this.activePointers.get(e.pointerId);
            const dx = e.clientX - pointer.startX;
            const dy = e.clientY - pointer.startY;

            if (Math.abs(dx) > 10 || Math.abs(dy) > 10) {
                this.clearLongPress();
            }

            if (Math.abs(dx) > this.options.swipeThreshold && Math.abs(dy) < this.options.maxVerticalSwipe) {
                this.interactionState = 'swiping';
                this.options.onSwipe?.(dx > 0 ? 'right' : 'left');
            }
        }
    }

    onPointerUp(e) {
        this.clearLongPress();
        const wasMagnifying = this.interactionState === 'magnifying';
        const wasPinching = this.interactionState === 'pinching';

        this.activePointers.delete(e.pointerId);

        if (wasMagnifying || wasPinching) {
            this.options.onMagnifyEnd?.();
        }

        if (this.activePointers.size < 2 && wasPinching) {
            this.interactionState = this.activePointers.size > 0 ? 'pressing' : 'idle';
        } else if (this.activePointers.size === 0) {
            this.interactionState = 'idle';
        }
    }

    getCenter() {
        const pointers = Array.from(this.activePointers.values());
        if (pointers.length < 2) return null;
        return {
            x: (pointers[0].x + pointers[1].x) / 2,
            y: (pointers[0].y + pointers[1].y) / 2,
        };
    }

    clearLongPress() {
        if (this.longPressTimer) clearTimeout(this.longPressTimer);
        this.longPressTimer = null;
    }
}

initModalDOM();

new InteractionManager(modalImg, {
    onSwipe: (dir) => {
      if (dir === "left") {
        animateSwipe("left", () => navigate(1));
        return;
      }
      animateSwipe("right", () => navigate(-1));
    },
    onLongPress: (pos) => showMagnifier(pos.x, pos.y),
    onPinchStart: (center) => showMagnifier(center.x, center.y),
    onMagnifyMove: (pos) => updateMagnifierPosition(pos.x, pos.y),
    onPinchMove: (center) => updateMagnifierPosition(center.x, center.y),
    onMagnifyEnd: hideMagnifier,
});

/* -----------------------------------------------------
   PRELOAD MANAGER (New)
----------------------------------------------------- */

const PreloadManager = (() => {
    const PRELOAD_AHEAD = 3;
    const PRELOAD_BEHIND = 2;
    let preloadedUrls = new Set();

    function preload(filename) {
        const url = buildFullUrl(filename);
        if (preloadedUrls.has(url)) {
            return;
        }
        preloadedUrls.add(url);
        const img = new Image();
        img.src = url;
    }

    function update(currentIndex, imageList) {
        if (!Array.isArray(imageList)) return;

        // Preload images ahead
        for (let i = 1; i <= PRELOAD_AHEAD; i++) {
            const nextIndex = currentIndex + i;
            if (nextIndex < imageList.length) {
                preload(imageList[nextIndex].filename);
            }
        }

        // Preload images behind
        for (let i = 1; i <= PRELOAD_BEHIND; i++) {
            const prevIndex = currentIndex - i;
            if (prevIndex >= 0) {
                preload(imageList[prevIndex].filename);
            }
        }
    }

    function forget(filename) {
        const url = buildFullUrl(filename);
        preloadedUrls.delete(url);
    }

    return { update, forget };
})();
