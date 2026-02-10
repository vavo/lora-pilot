/* -----------------------------------------------------
   DRAG SELECT HELPER
----------------------------------------------------- */

export function initDragSelect(container, onSelection) {
  let dragStart = null;
  let selectionBox = null;
  let dragPointerId = null;
  let dragThresholdPassed = false;
  let isDraggingSelect = false;
  let prevUserSelect = "";
  let prevOverflow = "";
  let dragModeEnabled = false;
  let longPressTimer = null;
  const START_THRESHOLD = 6;

  function pointerEligible(target) {
    return !(
      target.closest("button") ||
      target.closest(".heart-overlay") ||
      target.closest(".card-actions")
    );
  }

  function startLongPressTimer(pointerId) {
    clearLongPressTimer();
    longPressTimer = setTimeout(() => {
      if (dragPointerId === pointerId) {
        dragModeEnabled = true;
      }
    }, 350);
  }

  function clearLongPressTimer() {
    if (longPressTimer) {
      clearTimeout(longPressTimer);
      longPressTimer = null;
    }
  }

  container.addEventListener("pointerdown", (e) => {
    if (dragPointerId !== null) return;
    if (e.button !== 0) return;
    if (!pointerEligible(e.target)) return;

    const isDesktop = !("ontouchstart" in window);
    const shiftMode = isDesktop && e.shiftKey;

    if (!shiftMode) {
      // For touch/mobile, require a long-press to enter drag mode
      dragModeEnabled = false;
      dragPointerId = e.pointerId;
      dragStart = { x: e.clientX, y: e.clientY };
      dragThresholdPassed = false;
      // Start long-press timer
      startLongPressTimer(e.pointerId);
      return;
    }

    // Shift pressed: enable drag mode immediately
    dragModeEnabled = true;
    dragPointerId = e.pointerId;
    dragStart = { x: e.clientX, y: e.clientY };
    dragThresholdPassed = false;
    // Prevent immediate scroll kick-off on touchpads/touch
    if (e.cancelable) e.preventDefault();
  });

  window.addEventListener("pointermove", (e) => {
    if (dragPointerId === null || e.pointerId !== dragPointerId) return;
    if (!dragStart) return;

    const dx = e.clientX - dragStart.x;
    const dy = e.clientY - dragStart.y;
    const dist = Math.hypot(dx, dy);

    // Before drag mode activates, treat movement as a normal scroll gesture.
    if (!dragModeEnabled) {
      if (dist > START_THRESHOLD) {
        clearLongPressTimer();
        dragPointerId = null;
        dragStart = null;
      }
      return;
    }

    // Block scroll while dragging
    if (e.cancelable) e.preventDefault();

    if (!dragThresholdPassed && dist > START_THRESHOLD) {
      dragThresholdPassed = true;
      isDraggingSelect = true;
      selectionBox = document.createElement("div");
      selectionBox.className = "selection-box";
      document.body.appendChild(selectionBox);
      prevUserSelect = document.body.style.userSelect;
      prevOverflow = document.documentElement.style.overflow;
      document.body.style.userSelect = "none";
      document.documentElement.style.overflow = "hidden";
    }

    if (!isDraggingSelect || !selectionBox) return;
    e.preventDefault();
    
    const x1 = dragStart.x;
    const y1 = dragStart.y;
    const x2 = e.clientX;
    const y2 = e.clientY;
    
    const left = Math.min(x1, x2);
    const top = Math.min(y1, y2);
    const width = Math.abs(x2 - x1);
    const height = Math.abs(y2 - y1);
    
    selectionBox.style.left = `${left}px`;
    selectionBox.style.top = `${top}px`;
    selectionBox.style.width = `${width}px`;
    selectionBox.style.height = `${height}px`;
  }, { passive: false });

  const endDrag = (e) => {
    if (dragPointerId === null || (e && e.pointerId !== dragPointerId)) return;
    clearLongPressTimer();
    dragPointerId = null;
    
    const box = selectionBox;
    selectionBox = null;
    const started = isDraggingSelect;
    isDraggingSelect = false;
    dragThresholdPassed = false;
    
    document.body.style.userSelect = prevUserSelect;
    document.documentElement.style.overflow = prevOverflow;
    
    let rect = null;
    if (box) {
      rect = box.getBoundingClientRect();
      box.remove();
    }
    
    dragStart = null;
    dragModeEnabled = false;

    if (started && rect && onSelection) {
        onSelection(rect);
    }
  };

  window.addEventListener("pointerup", endDrag);
  window.addEventListener("pointercancel", endDrag);
}
