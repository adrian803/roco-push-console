import {escapeHTML, newId} from "./console-format.js";

function hasDefault(field) {
  return Object.prototype.hasOwnProperty.call(field, "default");
}

export function providerLabel(providerTypes, type) {
  return (providerTypes[type] && providerTypes[type].label) || type;
}

export function renderProviderTypeOptions($, providerTypes) {
  $("newProviderType").innerHTML = Object.entries(providerTypes).map(([type, spec]) =>
    `<option value="${escapeHTML(type)}">${escapeHTML(spec.label)}</option>`
  ).join("");
}

export function refreshProviderSelects($, providers, providerTypes, config = {}) {
  const options = ['<option value="">未选择</option>'].concat(providers.map(provider => {
    const label = escapeHTML(provider.name || providerLabel(providerTypes, provider.type));
    return `<option value="${escapeHTML(provider.id)}">${label}</option>`;
  }));
  $("selected_provider").innerHTML = options.join("");
  $("selected_provider").value = config.selected_provider || "";
}

export function renderProviders($, providers, providerTypes, config = {}) {
  const host = $("providers");
  if (!providers.length) {
    host.innerHTML = `<div class="provider-card"><div class="empty-state">还没有通道，先从右上角添加一个。</div></div>`;
    refreshProviderSelects($, providers, providerTypes, config);
    return;
  }
  host.innerHTML = providers.map((provider, index) => {
    const spec = providerTypes[provider.type] || {fields: [], label: provider.type, description: ""};
    const fields = spec.fields.map(field => {
      const value = provider.config[field.name] ?? "";
      const hasValue = provider.config[`has_${field.name}`];
      const placeholder = field.secret && hasValue ? "已配置，留空不改" : (hasDefault(field) ? field.default : "");
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
  refreshProviderSelects($, providers, providerTypes, config);
}

export function collectProviders(root, providers) {
  const next = providers.map(provider => ({
    id: provider.id,
    type: provider.type,
    name: provider.name,
    enabled: provider.enabled,
    config: {...provider.config},
  }));
  root.querySelectorAll("[data-provider-index]").forEach(input => {
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

export function createProvider(type, providerTypes) {
  const spec = providerTypes[type];
  if (!spec) return null;
  const config = {};
  (spec.fields || []).forEach(field => {
    if (hasDefault(field)) config[field.name] = field.default;
  });
  return {id: newId(type), type, name: spec.label, enabled: true, config};
}
