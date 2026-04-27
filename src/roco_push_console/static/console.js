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

    function newId(type) {
      return `${type}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;
    }
    function prettyTime(value) {
      if (!value) return "-";
      return value.replace("T", " ").replace("+08:00", "");
    }
    function escapeHTML(value) {
      return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "\"": "&quot;",
        "'": "&#39;",
      }[char]));
    }
    async function requestJSON(url, options = {}) {
      const response = await fetch(url, {
        headers: {"Content-Type": "application/json"},
        ...options,
      });
      const text = await response.text();
      let data = {};
      try {
        data = text ? JSON.parse(text) : {};
      } catch (error) {
        data = {message: text || "请求失败"};
      }
      if (!response.ok) throw new Error(data.detail || data.message || "请求失败");
      return data;
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
    function providerLabel(type) {
      return (providerTypes[type] && providerTypes[type].label) || type;
    }
    function renderProviderTypeOptions() {
      $("newProviderType").innerHTML = Object.entries(providerTypes).map(([type, spec]) =>
        `<option value="${escapeHTML(type)}">${escapeHTML(spec.label)}</option>`
      ).join("");
    }
    function refreshProviderSelects(config = {}) {
      const options = ['<option value="">未选择</option>'].concat(providers.map(provider => {
        const label = escapeHTML(provider.name || providerLabel(provider.type));
        return `<option value="${escapeHTML(provider.id)}">${label}</option>`;
      }));
      $("selected_provider").innerHTML = options.join("");
      $("selected_provider").value = config.selected_provider || "";
    }
    function renderProviders() {
      const host = $("providers");
      if (!providers.length) {
        host.innerHTML = `<div class="provider-card"><div class="empty-state">还没有通道，先从右上角添加一个。</div></div>`;
        refreshProviderSelects();
        return;
      }
      host.innerHTML = providers.map((provider, index) => {
        const spec = providerTypes[provider.type] || {fields: [], label: provider.type, description: ""};
        const fields = spec.fields.map(field => {
          const value = provider.config[field.name] ?? "";
          const hasValue = provider.config[`has_${field.name}`];
          const placeholder = field.secret && hasValue ? "已配置，留空不改" : (field.default || "");
          const fieldName = escapeHTML(field.name);
          const inputType = field.secret ? "password" : "text";
          return `
            <div class="field">
              <label>${escapeHTML(field.label)}${field.required ? " *" : ""}</label>
              <input
                data-provider-index="${index}"
                data-config-field="${fieldName}"
                type="${inputType}"
                value="${escapeHTML(value || "")}"
                placeholder="${escapeHTML(placeholder)}"
              >
            </div>`;
        }).join("");
        return `
          <div class="provider-card" data-provider-index="${index}">
            <div class="provider-head">
              <div>
                <h3>${escapeHTML(provider.name || spec.label)}</h3>
                <div class="provider-meta">${escapeHTML(spec.label)} · ${escapeHTML(spec.description || "")}</div>
              </div>
              <div class="actions" style="margin-top:0;">
                <button type="button" class="subtle" data-action="move-up"
                  data-index="${index}" ${index === 0 ? "disabled" : ""}>上移</button>
                <button type="button" class="subtle" data-action="move-down"
                  data-index="${index}" ${index === providers.length - 1 ? "disabled" : ""}>下移</button>
                <button type="button" class="subtle" data-action="test" data-index="${index}">测试</button>
                <button type="button" class="danger" data-action="remove" data-index="${index}">删除</button>
              </div>
            </div>
            <div class="grid">
              <div class="field">
                <label>名称</label>
                <input data-provider-index="${index}" data-provider-field="name"
                  value="${escapeHTML(provider.name || "")}">
              </div>
              <label class="checkline">
                <input data-provider-index="${index}" data-provider-field="enabled"
                  type="checkbox" ${provider.enabled ? "checked" : ""}>
                启用
              </label>
              ${fields}
            </div>
          </div>`;
      }).join("");
      refreshProviderSelects({selected_provider: $("selected_provider").value});
    }
    function collectProviders() {
      const next = providers.map(provider => ({
        id: provider.id,
        type: provider.type,
        name: provider.name,
        enabled: provider.enabled,
        config: {...provider.config},
      }));
      document.querySelectorAll("[data-provider-index]").forEach(input => {
        const index = Number(input.dataset.providerIndex);
        if (!next[index]) return;
        if (input.dataset.providerField) {
          const name = input.dataset.providerField;
          next[index][name] = input.type === "checkbox" ? input.checked : input.value.trim();
        }
        if (input.dataset.configField) {
          next[index].config[input.dataset.configField] = input.value.trim();
        }
      });
      return next;
    }
    function buildConfigPayload() {
      providers = collectProviders();
      return {
        rocom_api_key: $("rocom_api_key").value,
        game_api_url: $("game_api_url").value,
        schedule_times: $("schedule_times").value,
        http_timeout: Number($("http_timeout").value || 30),
        notify_empty: $("notify_empty").checked,
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
      $("run_on_start").checked = !!config.run_on_start;
      renderProviders();
      refreshProviderSelects(config);
    }
    function applyState(data, options = {}) {
      const config = data.config;
      providerTypes = data.provider_types || providerTypes;
      renderConfigIssue(data.config_issue);
      renderProviderTypeOptions();
      if (!options.preserveDraft) {
        applyConfig(config);
      } else {
        refreshProviderSelects({selected_provider: $("selected_provider").value});
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
        providers = collectProviders();
        providers.splice(index, 1);
        renderProviders();
        markConfigDirty();
      }
      if (button.dataset.action === "move-up" && index > 0) {
        providers = collectProviders();
        [providers[index - 1], providers[index]] = [providers[index], providers[index - 1]];
        renderProviders();
        markConfigDirty();
      }
      if (button.dataset.action === "move-down" && index < providers.length - 1) {
        providers = collectProviders();
        [providers[index + 1], providers[index]] = [providers[index], providers[index + 1]];
        renderProviders();
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
      const type = $("newProviderType").value;
      const spec = providerTypes[type];
      if (!spec) {
        $("message").textContent = "通道类型还未加载完成，请稍后再试";
        return;
      }
      providers = collectProviders();
      const config = {};
      (spec.fields || []).forEach(field => {
        if (field.default) config[field.name] = field.default;
      });
      providers.push({id: newId(type), type, name: spec.label, enabled: true, config});
      renderProviders();
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
    loadState().catch(error => $("message").textContent = error.message);
    setInterval(() => loadState({preserveDraft: configDirty}).catch(() => {}), 5000);
