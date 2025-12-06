(() => {
  const TEXT_KEY = "textSize";
  const COLORBLIND_KEY = "colorblindMode";
  const HIGHCONTRAST_KEY = "highContrast";

  const body = document.body;
  const menu = document.getElementById("a11y-menu");
  const toggleBtn = document.getElementById("a11y-toggle");
  const colorblindBtn = document.getElementById("toggle-colorblind");
  const highContrastBtn = document.getElementById("toggle-highcontrast");
  const resetBtn = document.getElementById("reset-a11y");

  function applyTextSize(size) {
    body.classList.remove("text-normal", "text-large", "text-xl");
    const cls =
      size === "large" ? "text-large" : size === "xl" ? "text-xl" : "text-normal";
    body.classList.add(cls);
    localStorage.setItem(TEXT_KEY, cls);
  }

  function applyColorblind(enabled) {
    body.classList.toggle("colorblind-mode", enabled);
    localStorage.setItem(COLORBLIND_KEY, enabled ? "1" : "0");
    if (colorblindBtn) colorblindBtn.setAttribute("aria-pressed", enabled ? "true" : "false");
  }

  function applyHighContrast(enabled) {
    body.classList.toggle("high-contrast", enabled);
    localStorage.setItem(HIGHCONTRAST_KEY, enabled ? "1" : "0");
    if (highContrastBtn) highContrastBtn.setAttribute("aria-pressed", enabled ? "true" : "false");
  }

  function loadSettings() {
    const savedSize = localStorage.getItem(TEXT_KEY) || "text-normal";
    applyTextSize(savedSize.replace("text-", "") || "normal");
    applyColorblind(localStorage.getItem(COLORBLIND_KEY) === "1");
    applyHighContrast(localStorage.getItem(HIGHCONTRAST_KEY) === "1");
  }

  function closeMenu() {
    if (!menu) return;
    menu.hidden = true;
    toggleBtn?.setAttribute("aria-expanded", "false");
  }

  function toggleMenu() {
    if (!menu) return;
    const hidden = menu.hidden;
    menu.hidden = !hidden;
    toggleBtn?.setAttribute("aria-expanded", hidden ? "true" : "false");
  }

  function bindControls() {
    if (toggleBtn) {
      toggleBtn.addEventListener("click", (e) => {
        e.preventDefault();
        toggleMenu();
      });
    }

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeMenu();
    });

    if (menu) {
      menu.addEventListener("keydown", (e) => {
        if (e.key === "Escape") closeMenu();
      });
    }

    document.querySelectorAll("[data-text]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const val = btn.getAttribute("data-text");
        applyTextSize(val);
      });
    });

    colorblindBtn?.addEventListener("click", (e) => {
      e.preventDefault();
      const enabled = !body.classList.contains("colorblind-mode");
      applyColorblind(enabled);
    });

    highContrastBtn?.addEventListener("click", (e) => {
      e.preventDefault();
      const enabled = !body.classList.contains("high-contrast");
      applyHighContrast(enabled);
    });

    resetBtn?.addEventListener("click", (e) => {
      e.preventDefault();
      applyTextSize("normal");
      applyColorblind(false);
      applyHighContrast(false);
      closeMenu();
    });
  }

  loadSettings();
  bindControls();
})();

