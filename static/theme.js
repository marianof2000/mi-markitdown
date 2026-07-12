(() => {
  const root = document.documentElement;
  const messages = window.MI_MARKITDOWN_I18N || {};

  try {
    const storedTheme = localStorage.getItem("theme");
    if (storedTheme) {
      root.dataset.theme = storedTheme;
    }
  } catch (_error) {}

  const systemPrefersDark = () => {
    return (
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches
    );
  };

  const activeTheme = () => {
    return root.dataset.theme || (systemPrefersDark() ? "dark" : "light");
  };

  const saveTheme = (theme) => {
    try {
      localStorage.setItem("theme", theme);
    } catch (_error) {}
  };

  const syncToggle = (toggle, icon) => {
    const isDark = activeTheme() === "dark";
    toggle.setAttribute(
      "aria-label",
      isDark
        ? messages.theme_to_light || "Cambiar a modo claro"
        : messages.theme_to_dark || "Cambiar a modo oscuro",
    );
    toggle.setAttribute("aria-pressed", String(isDark));
    if (icon) {
      icon.textContent = isDark ? "☀" : "☾";
    }
  };

  document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.querySelector("#theme-toggle");
    if (!toggle) return;

    const icon = toggle.querySelector("span");
    syncToggle(toggle, icon);

    toggle.addEventListener("click", () => {
      const nextTheme = activeTheme() === "dark" ? "light" : "dark";
      root.dataset.theme = nextTheme;
      saveTheme(nextTheme);
      syncToggle(toggle, icon);
    });
  });
})();
