document.addEventListener("DOMContentLoaded", () => {
  if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
    return;
  }

  document.querySelectorAll(".nav-menu, .profile-menu").forEach((menu) => {
    let closeTimer;

    menu.addEventListener("mouseenter", () => {
      clearTimeout(closeTimer);
      menu.open = true;
    });

    menu.addEventListener("mouseleave", () => {
      closeTimer = setTimeout(() => {
        menu.open = false;
      }, 250);
    });
  });
});
