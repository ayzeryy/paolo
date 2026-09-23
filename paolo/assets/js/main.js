"use strict";

// All essential links, content and video controls work without this enhancement.
document.querySelectorAll("[data-year]").forEach((el) => {
  el.textContent = String(new Date().getFullYear());
});
document.querySelectorAll(".fade-up").forEach((el, index) => {
  el.style.setProperty("--enter-delay", `${Math.min(index * 100, 300)}ms`);
});

const menuButton = document.querySelector(".menu-toggle");
const navigation = document.querySelector("#site-navigation");
if (menuButton && navigation && window.matchMedia) {
  const desktop = window.matchMedia("(min-width: 64rem)");
  let expanded = false;
  const renderNavigation = () => {
    const show = desktop.matches || expanded;
    // Preserve a sensible focus position when a resize hides the current control.
    if (desktop.matches && document.activeElement === menuButton) {
      navigation.hidden = false;
      navigation.querySelector("a").focus();
    } else if (!show && navigation.contains(document.activeElement)) {
      menuButton.hidden = false;
      menuButton.focus();
    }
    menuButton.hidden = desktop.matches;
    menuButton.setAttribute("aria-expanded", String(show));
    navigation.hidden = !show;
  };
  menuButton.addEventListener("click", () => {
    expanded = !expanded;
    renderNavigation();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !desktop.matches && expanded) {
      expanded = false;
      renderNavigation();
      menuButton.focus();
    }
  });
  desktop.addEventListener("change", () => { expanded = false; renderNavigation(); });
  renderNavigation();
}

// No autoplay attribute in HTML: unknown preferences or missing JS fail paused.
const video = document.querySelector("video[data-autoplay]");
if (video && window.matchMedia) {
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  if (!reducedMotion.matches) {
    video.muted = true;
    video.autoplay = true;
    const playback = video.play();
    if (playback) playback.catch(() => { /* Native controls remain available. */ });
  }
  reducedMotion.addEventListener("change", (event) => {
    if (event.matches) {
      video.autoplay = false;
      video.pause();
    }
    // Turning motion back on never overrides an intentional pause.
  });
}
