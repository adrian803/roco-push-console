import {requestJSON} from "./console-api.js";
import {escapeHTML, prettyTime} from "./console-format.js";
import {
  collectProviders,
  createProvider,
  refreshProviderSelects,
  renderProviders,
  renderProviderTypeOptions,
} from "./console-providers.js";

const $ = (id) => document.getElementById(id);
const baseFields = [
  "rocom_api_key",
  "game_api_url",
  "schedule_times",
  "http_timeout",
  "delivery_mode",
  "selected_provider",
];
let providerTypes = {};
let providers = [];
let configDirty = false;
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

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem(themeStorageKey, theme);
  } catch {
    // Theme persistence is a convenience; the UI still works without storage.
  }
  renderThemeButton();
}

function renderThemeButton() {
  const button = $("themeBtn");
  const theme = resolvedTheme();
  button.textContent = theme === "dark" ? "浅色" : "深色";
  button.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
  button.setAttribute("aria-label", `切换到${theme === "dark" ? "浅色" : "深色"}模式`);
}

function initTheme() {
  renderThemeButton();
  $("themeBtn").addEventListener("click", () => {
    applyTheme(resolvedTheme() === "dark" ? "light" : "dark");
  });
  if (window.matchMedia) {
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
      if (!storedTheme()) renderThemeButton();
    });
  }
}

function setBusy(isBusy) {
  ["saveBtn", "runBtn", "testBtn", "refreshBtn", "addProviderBtn"].forEach(id => $(id).disabled = isBusy);
}

function updateDraftBadge() {
  $("draftBadge").hidden = !configDirty;
}

function markConfigDirty() {
  configDirty = true;
  updateDraftBadge();
}

function clearConfigDirty() {
  configDirty = false;
  updateDraftBadge();
}

function renderConfigIssue(issue) {
  const box = $("configIssue");
  if (!issue || !issue.message) {
    box.hidden = true;
    box.textContent = "";
    return;
  }
  box.hidden = false;
  box.textContent = issue.backup_path ? `${issue.message}` : issue.message;
}

function renderPushResults(results) {
  const host = $("pushResults");
  host.textContent = "";
  if (!results || !results.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "本轮暂无推送结果";
    host.appendChild(empty);
    return;
  }
  results.forEach(result => {
    const item = document.createElement("div");
    item.className = `result-item ${result.success ? "ok" : "fail"}`;
    const head = document.createElement("div");
    head.className = "result-head";
    const title = document.createElement("strong");
    title.textContent = result.provider_name || result.provider_type || "推送通道";
    const status = document.createElement("span");
    status.className = "result-status";
    status.textContent = result.success ? "成功" : "失败";
    head.append(title, status);

    const message = document.createElement("div");
    message.className = "result-message";
    const statusCode = result.status_code ? `HTTP ${result.status_code} · ` : "";
    message.textContent = `${statusCode}${result.message || "无详情"}`;
    item.append(head, message);
    host.appendChild(item);
  });
}

function renderProviderState(config = {}) {
  renderProviders($, providers, providerTypes, config);
}

function collectProviderState() {
  providers = collectProviders(document, providers);
  return providers;
}

function buildConfigPayload() {
  collectProviderState();
  return {
    rocom_api_key: $("rocom_api_key").value,
    game_api_url: $("game_api_url").value,
    schedule_times: $("schedule_times").value,
    http_timeout: Number($("http_timeout").value || 30),
    notify_empty: $("notify_empty").checked,
    include_price_info: $("include_price_info").checked,
    run_on_start: $("run_on_start").checked,
    delivery_mode: $("delivery_mode").value,
    selected_provider: $("selected_provider").value,
    failover_order: providers.filter(provider => provider.enabled).map(provider => provider.id),
    providers,
  };
}

function applyConfig(config) {
  providers = config.providers || [];
  baseFields.forEach(name => {
    if (name === "rocom_api_key") {
      $(name).value = "";
      $(name).placeholder = config.has_rocom_api_key ? "已配置，留空不改" : "未配置";
    } else if (name !== "selected_provider") {
      $(name).value = config[name] ?? "";
    }
  });
  $("notify_empty").checked = !!config.notify_empty;
  $("include_price_info").checked = !!config.include_price_info;
  $("run_on_start").checked = !!config.run_on_start;
  renderProviderState(config);
}

function applyState(data, options = {}) {
  const config = data.config;
  providerTypes = data.provider_types || providerTypes;
  renderConfigIssue(data.config_issue);
  renderProviderTypeOptions($, providerTypes);
  if (!options.preserveDraft) {
    applyConfig(config);
  } else {
    refreshProviderSelects($, providers, providerTypes, {selected_provider: $("selected_provider").value});
  }

  const savedProviders = config.providers || [];
  const configured = config.has_rocom_api_key && savedProviders.some(provider => provider.enabled);
  $("configuredBadge").textContent = configured ? "已配置" : "未配置";
  $("configuredBadge").className = configured ? "badge ok" : "badge warn";
  const state = data.scheduler;
  $("runningBadge").textContent = state.running ? "调度中" : "未运行";
  $("busyBadge").textContent = state.in_progress ? "执行中" : "空闲";
  $("busyBadge").className = state.in_progress ? "badge warn" : "badge ok";
  $("nowBadge").textContent = prettyTime(data.now);
  $("logoutBtn").hidden = !data.auth_enabled;
  $("nextRun").textContent = prettyTime(state.next_run_at);
  $("lastStart").textContent = prettyTime(state.last_started_at);
  $("lastFinish").textContent = prettyTime(state.last_finished_at);
  $("lastCode").textContent = state.last_exit_code ?? "-";
  $("message").textContent = state.last_message || "-";
  renderPushResults(state.last_push_results || []);
  updateDraftBadge();
}

async function loadState(options = {}) {
  const data = await requestJSON("/api/state");
  applyState(data, options);
}

$("providers").addEventListener("click", async event => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const index = Number(button.dataset.index);
  if (button.dataset.action === "remove") {
    collectProviderState();
    providers.splice(index, 1);
    renderProviderState({selected_provider: $("selected_provider").value});
    markConfigDirty();
  }
  if (button.dataset.action === "move-up" && index > 0) {
    collectProviderState();
    [providers[index - 1], providers[index]] = [providers[index], providers[index - 1]];
    renderProviderState({selected_provider: $("selected_provider").value});
    markConfigDirty();
  }
  if (button.dataset.action === "move-down" && index < providers.length - 1) {
    collectProviderState();
    [providers[index + 1], providers[index]] = [providers[index], providers[index + 1]];
    renderProviderState({selected_provider: $("selected_provider").value});
    markConfigDirty();
  }
  if (button.dataset.action === "test") {
    setBusy(true);
    try {
      const payload = buildConfigPayload();
      const provider = providers[index];
      const data = await requestJSON("/api/test-push", {
        method: "POST",
        body: JSON.stringify({provider_id: provider.id, config: payload}),
      });
      $("message").textContent = data.message;
    } catch (error) {
      $("message").textContent = error.message;
    } finally {
      setBusy(false);
    }
  }
});

$("addProviderBtn").addEventListener("click", () => {
  const provider = createProvider($("newProviderType").value, providerTypes);
  if (!provider) {
    $("message").textContent = "通道类型还未加载完成，请稍后再试";
    return;
  }
  collectProviderState();
  providers.push(provider);
  renderProviderState({selected_provider: $("selected_provider").value});
  markConfigDirty();
});

async function saveConfig(showMessage = true) {
  const payload = buildConfigPayload();
  await requestJSON("/api/config", {method: "POST", body: JSON.stringify(payload)});
  clearConfigDirty();
  await loadState({preserveDraft: false});
  if (showMessage) $("message").textContent = "配置已保存";
}

$("configForm").addEventListener("input", event => {
  if (event.target && event.target.id !== "newProviderType") markConfigDirty();
});

$("configForm").addEventListener("change", event => {
  if (event.target && event.target.id !== "newProviderType") markConfigDirty();
});

$("configForm").addEventListener("submit", async event => {
  event.preventDefault();
  setBusy(true);
  try {
    await saveConfig(true);
  } catch (error) {
    $("message").textContent = error.message;
  } finally {
    setBusy(false);
  }
});

$("runBtn").addEventListener("click", async () => {
  if (configDirty) {
    $("message").textContent = "有未保存修改，请先保存配置再立即执行";
    updateDraftBadge();
    return;
  }
  setBusy(true);
  try {
    const data = await requestJSON("/api/run-now", {method: "POST", body: "{}"});
    $("message").textContent = data.message;
    await loadState({preserveDraft: configDirty});
  } catch (error) {
    $("message").textContent = error.message;
  } finally {
    setBusy(false);
  }
});

$("testBtn").addEventListener("click", async () => {
  setBusy(true);
  try {
    const data = await requestJSON("/api/test-push", {
      method: "POST",
      body: JSON.stringify({config: buildConfigPayload()}),
    });
    $("message").textContent = data.message;
  } catch (error) {
    $("message").textContent = error.message;
  } finally {
    setBusy(false);
  }
});

$("logoutBtn").addEventListener("click", async () => {
  try {
    await requestJSON("/api/logout", {method: "POST", body: "{}"});
  } finally {
    window.location.assign("/login");
  }
});

$("refreshBtn").addEventListener("click", () => loadState({preserveDraft: configDirty}));
initTheme();
loadState().catch(error => $("message").textContent = error.message);
setInterval(() => loadState({preserveDraft: configDirty}).catch(() => {}), 5000);
