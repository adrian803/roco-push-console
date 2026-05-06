    const form = document.getElementById("loginForm");
    const button = document.getElementById("loginBtn");
    const message = document.getElementById("message");
    const themeButton = document.getElementById("themeBtn");
    const themeStorageKey = "roco-console-theme";

    function storedTheme() {
      try {
        return localStorage.getItem(themeStorageKey);
      } catch {
        return "";
      }
    }

    function systemPrefersDark() {
      return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    }

    function resolvedTheme() {
      const theme = document.documentElement.dataset.theme || storedTheme();
      if (theme === "light" || theme === "dark") return theme;
      return systemPrefersDark() ? "dark" : "light";
    }

    function renderThemeButton() {
      const theme = resolvedTheme();
      themeButton.textContent = theme === "dark" ? "浅色" : "深色";
      themeButton.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
      themeButton.setAttribute("aria-label", `切换到${theme === "dark" ? "浅色" : "深色"}模式`);
    }

    function applyTheme(theme) {
      document.documentElement.dataset.theme = theme;
      try {
        localStorage.setItem(themeStorageKey, theme);
      } catch {
        // Theme persistence is optional; rendering still works without storage.
      }
      renderThemeButton();
    }

    function nextUrl() {
      const params = new URLSearchParams(window.location.search);
      const next = params.get("next") || "/";
      return next.startsWith("/") ? next : "/";
    }

    themeButton.addEventListener("click", () => {
      applyTheme(resolvedTheme() === "dark" ? "light" : "dark");
    });

    if (window.matchMedia) {
      window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
        if (!storedTheme()) renderThemeButton();
      });
    }

    renderThemeButton();

    form.addEventListener("submit", async event => {
      event.preventDefault();
      button.disabled = true;
      message.textContent = "";
      try {
        const response = await fetch("/api/login", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            username: document.getElementById("username").value.trim(),
            password: document.getElementById("password").value,
          }),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.detail || data.message || "登录失败");
        window.location.assign(nextUrl());
      } catch (error) {
        message.textContent = error.message;
      } finally {
        button.disabled = false;
      }
    });
