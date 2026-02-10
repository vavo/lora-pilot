const loadingScreen = document.getElementById("loading-screen");

export function showLoadingScreen() {
  if (loadingScreen) loadingScreen.classList.remove("hidden");
}

export function hideLoadingScreen() {
  if (loadingScreen) loadingScreen.classList.add("hidden");
}
