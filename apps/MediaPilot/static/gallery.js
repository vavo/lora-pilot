console.log("GALLERY JS LOADED");

// Versioned import to keep modules in sync and defeat old caches.
import { openModal } from "./modal.js?v=cb23";
import * as API from "./gallery-api.js?v=cb23";
import { initDragSelect } from "./gallery-drag.js?v=cb23";

/* -----------------------------------------------------
   STATE
----------------------------------------------------- */

let imagesList = [];
let visibleImages = [];
let currentPage = 1;
let totalPages = 1;
let loading = false;
let isEnd = false;

let currentFolder = "_root";
let filterMode = "ALL";
let sortMode = "NEWEST";
let searchQuery = "";
let selectedImages = new Set();
let tagsList = [];
let activeTagMenu = null;
let activeTagMenuHandler = null;
let searchDebounceTimer = null;
let lastTapTime = 0;
let selectionAnchor = null;
const deletedImages = new Set();

const LIMIT = 50;

/* -----------------------------------------------------
   DOM
----------------------------------------------------- */

const gallery = document.getElementById("gallery");
const folderSelect = document.getElementById("folder-select");
const thumbSlider = document.getElementById("thumb-slider");
const filterSelect = document.getElementById("filter-select");
const sortSelect = document.getElementById("sort-select");
const searchInput = document.getElementById("search-input");
const loadingScreen = document.getElementById("loading-screen");
const loadingBar = document.getElementById("loading-progress-bar");
const scrollSentinel = document.getElementById("scroll-sentinel");

const bulkBar = document.getElementById("bulk-bar");
const bulkCount = document.getElementById("bulk-count");
const bulkUpscaleBtn = document.getElementById("bulk-upscale-btn");
const bulkDownloadBtn = document.getElementById("bulk-download-btn");
const bulkLikeBtn = document.getElementById("bulk-like-btn");
const bulkTagBtn = document.getElementById("bulk-tag-btn");
const bulkDeleteBtn = document.getElementById("bulk-delete-btn");

function notify(message) {
  if (window.showToast) window.showToast(message);
}

function isNonEmptyString(value) {
  return typeof value === "string" && value.trim() !== "";
}

function isReservedTagName(value) {
  const name = (value || "").trim().toLowerCase();
  return name === "untagged" || name === "invokeai" || name === "_root";
}

const THUMB_EXT = ".webp";

function encodePathSegment(value) {
  return encodeURIComponent(value);
}

function encodeFolderPath(folder) {
  return (folder || "").split("/").map(encodePathSegment).join("/");
}

function buildThumbUrl(filename, folder) {
  if (!isNonEmptyString(filename)) return "";
  const safeFilename = `${encodeURIComponent(filename)}${THUMB_EXT}`;
  if (folder === "_root") return `./thumbs/${safeFilename}`;
  if (folder === "InvokeAI") return `./thumbs/InvokeAI/${safeFilename}`;
  const safeFolder = encodeFolderPath(folder);
  return `./thumbs/${safeFolder}/${safeFilename}`;
}

function buildFullUrl(filename, folder) {
  if (!isNonEmptyString(filename)) return "";
  const safeFilename = encodeURIComponent(filename);
  if (folder === "_root") return `./output/${safeFilename}`;
  if (folder === "InvokeAI") return `./invoke/${safeFilename}`;
  const safeFolder = encodeFolderPath(folder);
  return `./output/${safeFolder}/${safeFilename}`;
}

const MAX_RETRIES = 2;
const RETRY_DELAY = 1000; // 1 second

function loadImageWithRetry(imgElement, src, retryCount = 0) {
  return new Promise((resolve) => {
    if (!imgElement || !isNonEmptyString(src)) {
      if (imgElement) {
        imgElement.classList.add('error');
        imgElement.classList.remove('loading');
        const placeholder = imgElement.nextElementSibling;
        if (placeholder) {
          placeholder.innerHTML = '❌<br>Image failed to load';
        }
      }
      resolve(false);
      return;
    }

    const img = new Image();
    img.decoding = "async";
    
    img.onload = () => {
      if (!imgElement.isConnected) {
        resolve(true);
        return;
      }
      imgElement.src = src;
      imgElement.classList.remove('loading');
      imgElement.classList.remove('error');
      resolve(true);
    };
    
    img.onerror = () => {
      if (retryCount < MAX_RETRIES) {
        // Show retry state
        imgElement.classList.add('error');
        const placeholder = imgElement.nextElementSibling;
        if (placeholder) {
          placeholder.textContent = `Retrying... (${retryCount + 1}/${MAX_RETRIES})`;
        }
        
        // Retry after delay
        setTimeout(() => {
          loadImageWithRetry(imgElement, src, retryCount + 1).then(resolve);
        }, RETRY_DELAY);
        return;
      }

      const fallbackSrc = imgElement.dataset.fallbackSrc;
      if (isNonEmptyString(fallbackSrc) && fallbackSrc !== src) {
        imgElement.dataset.fallbackSrc = "";
        const placeholder = imgElement.nextElementSibling;
        if (placeholder) {
          placeholder.textContent = "Loading full image...";
        }
        loadImageWithRetry(imgElement, fallbackSrc, 0).then(resolve);
        return;
      } else {
        // Max retries reached, show error state
        imgElement.classList.add('error');
        imgElement.classList.remove('loading');
        const placeholder = imgElement.nextElementSibling;
        if (placeholder) {
          placeholder.innerHTML = '❌<br>Image failed to load';
        }
        resolve(false);
      }
    };
    
    img.src = src;
  });
}

const thumbObserver =
  "IntersectionObserver" in window
    ? new IntersectionObserver(
        (entries, obs) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              const img = entry.target;
              if (img.dataset.src) {
                const src = img.dataset.src;
                img.classList.add('loading');
                
                // Create placeholder if it doesn't exist
                if (!img.nextElementSibling || !img.nextElementSibling.classList.contains('thumb-placeholder')) {
                  const placeholder = document.createElement('div');
                  placeholder.className = 'thumb-placeholder';
                  placeholder.innerHTML = '<div class="loading-spinner"></div><div>Loading...</div>';
                  img.parentNode.insertBefore(placeholder, img.nextSibling);
                }
                
                loadImageWithRetry(img, src)
                  .then((loaded) => {
                    if (!loaded) return;
                    // Remove placeholder on success
                    const placeholder = img.nextElementSibling;
                    if (placeholder && placeholder.classList.contains('thumb-placeholder')) {
                      placeholder.remove();
                    }
                  });
                
                img.removeAttribute("data-src");
              }
              obs.unobserve(img);
            }
          });
        },
        { rootMargin: "200px" }
      )
    : null;
const infiniteObserver =
  "IntersectionObserver" in window && scrollSentinel
    ? new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting && !loading && !isEnd) {
              loadImages(currentPage + 1, true);
            }
          });
        },
        { rootMargin: "400px" }
      )
    : null;
if (infiniteObserver && scrollSentinel) {
  infiniteObserver.observe(scrollSentinel);
}

// --- Loading Screen Functions ---
function showLoadingScreen() {
  if (loadingScreen) {
    loadingScreen.classList.remove("hidden");
    if (loadingBar) {
      loadingBar.style.width = "100%"; // Simple indeterminate style
    }
  }
}

function hideLoadingScreen() {
  if (loadingScreen) {
    loadingScreen.classList.add("hidden");
    if (loadingBar) {
      loadingBar.style.width = "0%";
    }
  }
}


/* -----------------------------------------------------
   DRAG SELECT
----------------------------------------------------- */

// Initialize drag selection logic from helper
initDragSelect(gallery, applySelectionRect);

/* -----------------------------------------------------
   LOAD FOLDERS
----------------------------------------------------- */

export async function loadFolders() {
  try {
    const json = await API.fetchFolders();

    const foldersRaw = Array.isArray(json.folders) ? json.folders : [];
    const folders = foldersRaw.length > 0 ? foldersRaw : ["Untagged", "InvokeAI"];
    tagsList = folders.filter((f) => f !== "InvokeAI");

    folderSelect.innerHTML = "";
    folders.forEach((f) => {
      const opt = document.createElement("option");
      opt.value = f === "Untagged" ? "_root" : f;
      opt.textContent = f;
      folderSelect.appendChild(opt);
    });

    const availableValues = folders.map((f) => (f === "Untagged" ? "_root" : f));
    if (!availableValues.includes(currentFolder)) {
      currentFolder = "_root";
    }
    folderSelect.value = currentFolder;
  } catch (err) {
    console.error("Failed to load folders", err);
    notify("Failed to load folders.");
    tagsList = ["Untagged"];
    folderSelect.innerHTML = `<option value="_root">Untagged</option><option value="InvokeAI">InvokeAI</option>`;
    folderSelect.value = "_root";
  }
}

folderSelect.onchange = () => {
  currentFolder = folderSelect.value;
  resetGallery();
  showLoadingScreen();
  loadImages(1, false);
};

if (filterSelect) {
  filterSelect.onchange = handleFilterChange;
}

if (sortSelect) {
  sortSelect.onchange = handleSortChange;
}

if (searchInput) {
  searchInput.oninput = handleSearchInput;
  searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      searchInput.value = "";
      handleSearchInput();
    }
  });
}

if (thumbSlider) {
  thumbSlider.oninput = handleThumbSize;
  applyThumbSize(thumbSlider.value);
}

/* -----------------------------------------------------
   RESET
----------------------------------------------------- */

export function resetGallery() {
  gallery.innerHTML = "";
  selectedImages.clear();
  selectionAnchor = null;
  visibleImages = [];
  currentPage = 1;
  isEnd = false;
  if (bulkCount) bulkCount.textContent = "";
  if (infiniteObserver && scrollSentinel) {
    infiniteObserver.observe(scrollSentinel);
  }
}

/* -----------------------------------------------------
   LOAD IMAGES
----------------------------------------------------- */

export async function loadImages(page = 1, append = false) {
  const pageNum = Number(page);
  if (!Number.isFinite(pageNum) || pageNum < 1) {
    console.error("Invalid page number:", page);
    notify("Invalid page number.");
    return;
  }
  if (loading) return;
  loading = true;
  if (!append) {
    showLoadingScreen();
  }

  try {
    const json = await API.fetchImages(
      pageNum,
      LIMIT,
      currentFolder,
      sortMode,
      searchQuery
    );
    const images = Array.isArray(json?.images) ? json.images : [];
    const incoming = filterDeleted(images);

    if (append) {
      imagesList = filterDeleted(imagesList).concat(incoming);
      renderWithFilters(incoming, true);
    } else {
      imagesList = incoming;
      renderWithFilters();
    }

    currentPage = Number.isFinite(json?.page) ? json.page : pageNum;
    totalPages = Number.isFinite(json?.pages) ? json.pages : currentPage;
    if (images.length === 0 || currentPage >= totalPages) isEnd = true;

  } catch (error) {
    console.error("Failed to load images:", error);
    notify("Failed to load images.");
    // Optionally show an error message
  } finally {
    loading = false;
    if (!append) {
      hideLoadingScreen();
    }
  }
}

function renderGallery(imgs) {
  gallery.innerHTML = "";
  imgs.forEach(renderCard);
}

function appendToGallery(imgs) {
  imgs.forEach(renderCard);
}

function passesFilters(img) {
  if (deletedImages.has(img.filename)) return false;
  switch (filterMode) {
    case "LIKED":
      return !!img.liked;
    case "UNLIKED":
      return !img.liked;
    default:
      return true;
  }
}

function filterDeleted(images) {
  return (images || []).filter((img) => !deletedImages.has(img.filename));
}

export async function ensureTagsLoaded() {
  const select = document.getElementById("folder-select");
  const needsReload =
    tagsList.length === 0 || (select && select.options.length === 0);
  if (!needsReload) return;
  try {
    await loadFolders();
  } catch (err) {
    console.error("Failed to refresh tags", err);
    notify("Failed to load tags.");
  }
}

function renderWithFilters(newImages = null, append = false) {
  const filtered = append
    ? (newImages || []).filter(passesFilters)
    : (imagesList || []).filter(passesFilters);

  if (append) {
    visibleImages = visibleImages.concat(filtered);
    appendToGallery(filtered);
  } else {
    visibleImages = filtered;
    renderGallery(filtered);
  }
}

/* -----------------------------------------------------
   RENDER ONE CARD
----------------------------------------------------- */

function renderCard(img) {
  const card = document.createElement("div");
  card.className = "card";
  card.dataset.filename = img.filename;
  card.dataset.createdAt = img.created_at ?? "";
  if (thumbSlider) {
    card.style.setProperty("--thumb-size", `${thumbSlider.value}px`);
  }
  if (selectedImages.has(img.filename)) {
    card.classList.add("selected");
  }

  const wrap = document.createElement("div");
  wrap.className = "img-wrapper";

  const thumbnail = document.createElement("img");
  thumbnail.loading = "lazy";
  thumbnail.className = "thumb loading";
  
  // Set alt text for accessibility
  thumbnail.alt = img.filename || 'Gallery thumbnail';
  
  if (thumbObserver) {
    const thumbSrc = buildThumbUrl(img.filename, currentFolder);
    const fullSrc = buildFullUrl(img.filename, currentFolder);
    thumbnail.dataset.src = thumbSrc || fullSrc;
    if (fullSrc) {
      thumbnail.dataset.fallbackSrc = fullSrc;
    }
    thumbObserver.observe(thumbnail);
  } else {
    // If no IntersectionObserver, load immediately with retry
    thumbnail.classList.add('loading');
    const placeholder = document.createElement('div');
    placeholder.className = 'thumb-placeholder';
    placeholder.innerHTML = '<div class="loading-spinner"></div><div>Loading...</div>';
    
    wrap.appendChild(thumbnail);
    wrap.appendChild(placeholder);
    
    const thumbSrc = buildThumbUrl(img.filename, currentFolder);
    const fullSrc = buildFullUrl(img.filename, currentFolder);
    if (fullSrc) {
      thumbnail.dataset.fallbackSrc = fullSrc;
    }
    loadImageWithRetry(thumbnail, thumbSrc || fullSrc)
      .then((loaded) => {
        if (!loaded) return;
        // Remove placeholder on success
        if (placeholder.parentNode === wrap) {
          wrap.removeChild(placeholder);
        }
      });
  }

  thumbnail.onclick = (e) => {
    e.stopPropagation();
    const now = Date.now();
    const isDouble =
      e.detail >= 2 || (lastTapTime && now - lastTapTime < 300);
    lastTapTime = now;
    if (isDouble) {
      openModal(img.filename, currentFolder);
    } else {
      if (e.shiftKey && selectionAnchor) {
        selectRange(selectionAnchor, img.filename);
      } else {
        toggleSelect(img.filename, card);
      }
    }
  };

  const heart = document.createElement("div");
  heart.className = "heart-overlay";
  if (img.liked) heart.classList.add("liked");
  heart.textContent = "❤️";
  heart.onclick = async (e) => {
    e.stopPropagation();
    await toggleLike(card, img.filename);
  };
  card.appendChild(heart);

  // Only append here if not already appended (happens in the else case above)
  if (!wrap.contains(thumbnail)) {
    wrap.appendChild(thumbnail);
  }
  card.appendChild(wrap);

  gallery.appendChild(card);
}

/* -----------------------------------------------------
   SELECT + BULK BAR
----------------------------------------------------- */

function toggleSelect(filename, card) {
  if (!card) return;
  if (selectedImages.has(filename)) {
    selectedImages.delete(filename);
    card.classList.remove("selected");
  } else {
    selectedImages.add(filename);
    card.classList.add("selected");
  }

  selectionAnchor = filename;
  updateBulkBar();
}

function updateBulkBar() {
  if (bulkCount) {
    bulkCount.textContent =
      selectedImages.size > 0 ? `${selectedImages.size} selected` : "";
  }
}

function selectRange(anchorFilename, targetFilename) {
  const anchorIndex = visibleImages.findIndex(
    (img) => img.filename === anchorFilename
  );
  const targetIndex = visibleImages.findIndex(
    (img) => img.filename === targetFilename
  );
  if (anchorIndex === -1 || targetIndex === -1) {
    const targetCard = document.querySelector(
      `.card[data-filename="${targetFilename}"]`
    );
    if (targetCard) {
      toggleSelect(targetFilename, targetCard);
    }
    return;
  }

  const start = Math.min(anchorIndex, targetIndex);
  const end = Math.max(anchorIndex, targetIndex);
  for (let i = start; i <= end; i++) {
    const filename = visibleImages[i]?.filename;
    if (!filename) continue;
    selectedImages.add(filename);
    const card = document.querySelector(`.card[data-filename="${filename}"]`);
    if (card) card.classList.add("selected");
  }

  selectionAnchor = targetFilename;
  updateBulkBar();
}

/* -----------------------------------------------------
   LIKE
----------------------------------------------------- */

function syncLikedFlag(filename, liked) {
  const updateList = (list) => {
    const entry = list.find((img) => img.filename === filename);
    if (entry) entry.liked = liked;
  };
  updateList(imagesList);
  updateList(visibleImages);
}

function setCardLiked(card, liked) {
  if (!card) return;
  const heart = card.querySelector(".heart-overlay");
  if (heart) {
    heart.classList.toggle("liked", liked);
  }
  const filename = card.dataset.filename;
  if (filename) syncLikedFlag(filename, liked);
}

function isLiked(filename, card) {
  const entry = imagesList.find((img) => img.filename === filename);
  if (entry && typeof entry.liked === "boolean") return entry.liked;
  if (card) {
    const heart = card.querySelector(".heart-overlay");
    return heart?.classList.contains("liked") ?? false;
  }
  return false;
}

export async function toggleLike(card, filename) {
  if (!isNonEmptyString(filename)) return false;
  const current = isLiked(filename, card);
  const next = !current;

  // Optimistic UI update
  setCardLiked(card, next);
  try {
    await API.sendLike(filename, next);
  } catch (error) {
    console.error("Failed to update like:", error);
    notify("Failed to update like.");
    setCardLiked(card, current);
    return false;
  }
  return true;
}

/* -----------------------------------------------------
   TAGGING (inline)
----------------------------------------------------- */

function closeTagMenu() {
  if (activeTagMenu) {
    activeTagMenu.remove();
    activeTagMenu = null;
  }
  if (activeTagMenuHandler) {
    document.removeEventListener("click", activeTagMenuHandler);
    activeTagMenuHandler = null;
  }
}

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

async function openTagMenu(anchorEl, filenames) {
  closeTagMenu();
  if (!anchorEl || !Array.isArray(filenames) || filenames.length === 0) return;

  await ensureTagsLoaded();

  const rect = anchorEl.getBoundingClientRect();

  const menu = document.createElement("div");
  menu.className = "tag-dropdown";
  menu.style.position = "fixed";
  menu.style.visibility = "hidden";
  menu.style.maxWidth = "calc(100vw - 16px)";
  menu.style.maxHeight = "60vh";
  menu.style.overflowY = "auto";

  if (tagsList.length === 0) {
    const empty = document.createElement("div");
    empty.className = "tag-dropdown-empty";
    empty.textContent = "No tags found";
    menu.appendChild(empty);
  } else {
    tagsList.forEach((tag) => {
      const btn = document.createElement("button");
      btn.className = "tag-dropdown-option";
      btn.textContent = tag;
      btn.onclick = async (e) => {
        e.stopPropagation();
        await applyTags(filenames, tag);
        closeTagMenu();
      };
      menu.appendChild(btn);
    });
  }

  appendAddTagOption(menu, async () => {
    closeTagMenu();
    await openTagMenu(anchorEl, filenames);
  });

  document.body.appendChild(menu);

  const padding = 8;
  const gap = 6;
  const menuHeight = menu.offsetHeight;
  const menuWidth = menu.offsetWidth;
  const spaceBelow = window.innerHeight - rect.bottom - gap;
  const spaceAbove = rect.top - gap;
  let top = rect.bottom + gap;
  if (spaceBelow < menuHeight && spaceAbove > 0) {
    top = rect.top - menuHeight - gap;
  }
  top = Math.max(padding, Math.min(top, window.innerHeight - menuHeight - padding));

  const maxLeft = window.innerWidth - menuWidth - padding;
  let left = Math.min(Math.max(padding, rect.left), maxLeft);
  if (Number.isNaN(left) || left < padding) left = padding;

  menu.style.top = `${top}px`;
  menu.style.left = `${left}px`;
  menu.style.visibility = "visible";
  activeTagMenu = menu;

  activeTagMenuHandler = (e) => {
    if (menu && !menu.contains(e.target)) {
      closeTagMenu();
    }
  };
  setTimeout(() => {
    if (activeTagMenuHandler) {
      document.addEventListener("click", activeTagMenuHandler);
    }
  }, 0);
}

async function applyTags(filenames, tag) {
  if (!Array.isArray(filenames) || filenames.length === 0) return;
  if (!isNonEmptyString(tag)) return;
  const newFolder = tag === "Untagged" ? "_root" : tag;

  for (let filename of filenames) {
    try {
      await API.sendTag(filename, currentFolder, newFolder);

      const card = document.querySelector(`.card[data-filename="${filename}"]`);
      if (card) card.remove();

      removeImageEntry(filename);
      selectedImages.delete(filename);
    } catch (error) {
      console.error(`Failed to tag ${filename}:`, error);
      notify("Failed to tag image.");
    }
  }

  updateBulkBar();
}

function removeImageEntry(filename) {
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

export function markImageDeleted(filename) {
  if (!isNonEmptyString(filename)) return;
  deletedImages.add(filename);
  removeImageEntry(filename);
  selectedImages.delete(filename);
  updateBulkBar();
}

/* -----------------------------------------------------
   BULK UPSCALE
----------------------------------------------------- */

if (bulkUpscaleBtn) {
  bulkUpscaleBtn.onclick = async () => {
    const selected = Array.from(selectedImages);
    if (selected.length === 0) return;

    bulkUpscaleBtn.disabled = true;
    try {
      const result = await API.upscaleBulk(currentFolder, selected);
      const queued = Number(result?.queued) || 0;
      const failed = Array.isArray(result?.failed) ? result.failed.length : 0;
      if (queued > 0 && failed === 0) {
        notify(`Queued ${queued} upscale job${queued === 1 ? "" : "s"}.`);
      } else if (queued > 0) {
        notify(`Queued ${queued} job${queued === 1 ? "" : "s"}, ${failed} failed.`);
      } else {
        notify("No upscale jobs were queued.");
      }
    } catch (err) {
      console.error("Failed to queue upscale jobs:", err);
      notify(err?.message || "Failed to queue upscale jobs.");
    } finally {
      bulkUpscaleBtn.disabled = false;
    }
  };
}

/* -----------------------------------------------------
   BULK DOWNLOAD
----------------------------------------------------- */

bulkDownloadBtn.onclick = async () => {
  const selected = Array.from(selectedImages);
  if (selected.length === 0) return;

  bulkDownloadBtn.disabled = true;
  try {
    const { blob, filename } = await API.downloadBulk(currentFolder, selected);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (err) {
    console.error("Failed to download selected images:", err);
    notify("Failed to download selected images.");
  } finally {
    bulkDownloadBtn.disabled = false;
  }
};

/* -----------------------------------------------------
   BULK DELETE (instant)
----------------------------------------------------- */

bulkDeleteBtn.onclick = async () => {
  const toDelete = Array.from(selectedImages);

  for (let filename of toDelete) {
    try {
      await API.deleteImage(filename, currentFolder);
      const card = document.querySelector(`.card[data-filename="${filename}"]`);
      if (card) card.remove();

      markImageDeleted(filename);
    } catch (err) {
      console.error(`Error deleting ${filename}:`, err);
      notify("Failed to delete image.");
      // If there was a network error, do not remove from client-side UI/lists
    }
  }

  selectedImages.clear();
  updateBulkBar();
};

/* -----------------------------------------------------
   BULK LIKE
----------------------------------------------------- */

bulkLikeBtn.onclick = async () => {
  for (let filename of selectedImages) {
    const card = document.querySelector(`.card[data-filename="${filename}"]`);
    await toggleLike(card, filename);
  }
};

/* -----------------------------------------------------
   BULK TAG (opens modal on first selected)
----------------------------------------------------- */

bulkTagBtn.onclick = async () => {
  const arr = Array.from(selectedImages);
  if (arr.length === 0) return;

  await openTagMenu(bulkTagBtn, arr);
};

/* -----------------------------------------------------
   KEYBOARD SHORTCUTS (gallery)
----------------------------------------------------- */

window.addEventListener("keydown", (e) => {
  if (selectedImages.size === 0) return;

  // Ignore typing into inputs
  const target = e.target;
  if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable)) {
    return;
  }

  if (e.key === "Delete" || e.key === "Backspace") {
    e.preventDefault();
    bulkDeleteBtn?.click();
    return;
  }

  if (e.key === " " || e.key === "Spacebar") {
    e.preventDefault();
    bulkLikeBtn?.click();
    return;
  }

  if (e.key === "Enter") {
    e.preventDefault();
    bulkTagBtn?.click();
  }
});

function handleFilterChange() {
  filterMode = filterSelect?.value || "ALL";
  renderWithFilters();
}

function handleSortChange() {
  sortMode = sortSelect?.value || "NEWEST";
  resetGallery();
  loadImages(1, false);
}

function handleSearchInput() {
  searchQuery = (searchInput?.value || "").trim();
  if (searchDebounceTimer) {
    clearTimeout(searchDebounceTimer);
  }
  searchDebounceTimer = setTimeout(() => {
    resetGallery();
    loadImages(1, false);
  }, 250);
}

function applyThumbSize(size) {
  const px = `${size}px`;
  gallery.style.setProperty("--thumb-size", px);
  gallery.style.setProperty("--thumb-gap", `${Math.max(8, Math.min(24, size / 12))}px`);
}

function handleThumbSize(e) {
  const value = e?.target?.value || thumbSlider?.value || 225;
  applyThumbSize(value);
}

function applySelectionRect(rect) {
  if (!rect || rect.width === 0 || rect.height === 0) return;
  const cards = Array.from(gallery.querySelectorAll(".card"));
  selectedImages.clear();
  cards.forEach((card) => card.classList.remove("selected"));

  cards.forEach((card) => {
    const cRect = card.getBoundingClientRect();
    const overlap =
      rect.left < cRect.right &&
      rect.right > cRect.left &&
      rect.top < cRect.bottom &&
      rect.bottom > cRect.top;
    if (overlap) {
      const filename = card.dataset.filename;
      if (filename) {
        selectedImages.add(filename);
        card.classList.add("selected");
      }
    }
  });

  updateBulkBar();
}

/* -----------------------------------------------------
   EXPORTS
----------------------------------------------------- */

export { imagesList, visibleImages, currentFolder, tagsList, currentPage, totalPages, loading };
