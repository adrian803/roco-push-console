from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


_MANIFEST_PATH = Path(__file__).with_name("shared") / "provider_manifest.json"


def _require_text(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"无效的 provider manifest: {context}")
    return value


def validate_provider_manifest(manifest: Any) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise ValueError("无效的 provider manifest: 根节点必须是对象")

    providers = manifest.get("providers")
    if not isinstance(providers, list):
        raise ValueError("无效的 provider manifest: providers 必须是数组")

    seen_types: set[str] = set()
    for provider_index, provider in enumerate(providers):
        if not isinstance(provider, dict):
            raise ValueError(f"无效的 provider manifest: providers[{provider_index}] 必须是对象")

        provider_type = _require_text(provider.get("type"), f"providers[{provider_index}].type")
        if provider_type in seen_types:
            raise ValueError(f"无效的 provider manifest: 重复的 provider type {provider_type}")
        seen_types.add(provider_type)

        _require_text(provider.get("label"), f"providers[{provider_index}].label")
        _require_text(provider.get("description"), f"providers[{provider_index}].description")
        _require_text(provider.get("envId"), f"providers[{provider_index}].envId")

        env_vars = provider.get("envVars")
        if not isinstance(env_vars, dict):
            raise ValueError(f"无效的 provider manifest: providers[{provider_index}].envVars 必须是对象")

        fields = provider.get("fields")
        if not isinstance(fields, list):
            raise ValueError(f"无效的 provider manifest: providers[{provider_index}].fields 必须是数组")

        field_names: set[str] = set()
        for field_index, field in enumerate(fields):
            if not isinstance(field, dict):
                raise ValueError(
                    f"无效的 provider manifest: providers[{provider_index}].fields[{field_index}] 必须是对象"
                )

            field_name = _require_text(
                field.get("name"),
                f"providers[{provider_index}].fields[{field_index}].name",
            )
            _require_text(
                field.get("label"),
                f"providers[{provider_index}].fields[{field_index}].label",
            )
            if field_name in field_names:
                raise ValueError(
                    f"无效的 provider manifest: providers[{provider_index}] 存在重复字段 {field_name}"
                )
            field_names.add(field_name)

            for flag in ("secret", "required"):
                if flag in field and not isinstance(field[flag], bool):
                    raise ValueError(
                        f"无效的 provider manifest: providers[{provider_index}].fields[{field_index}].{flag} 必须是布尔值"
                    )
            if "default" in field and not isinstance(field["default"], str):
                raise ValueError(
                    f"无效的 provider manifest: providers[{provider_index}].fields[{field_index}].default 必须是字符串"
                )

        for env_name, env_value in env_vars.items():
            _require_text(
                env_name,
                f"providers[{provider_index}].envVars key",
            )
            _require_text(
                env_value,
                f"providers[{provider_index}].envVars[{env_name}]",
            )
            if env_name not in field_names:
                raise ValueError(
                    f"无效的 provider manifest: providers[{provider_index}].envVars[{env_name}] 未在 fields 中声明"
                )

    return manifest


@lru_cache(maxsize=1)
def provider_manifest() -> dict[str, Any]:
    return validate_provider_manifest(json.loads(_MANIFEST_PATH.read_text(encoding="utf-8")))


def _provider_entries() -> list[dict[str, Any]]:
    manifest = provider_manifest()
    providers = manifest.get("providers", [])
    return [provider for provider in providers if isinstance(provider, dict)]


PROVIDER_TYPES: dict[str, dict[str, Any]] = {
    str(provider["type"]): provider
    for provider in _provider_entries()
    if str(provider.get("type") or "").strip()
}


def provider_spec(provider_type: str) -> dict[str, Any]:
    return PROVIDER_TYPES.get(provider_type, {})


def public_provider_types() -> dict[str, dict[str, Any]]:
    return {
        provider_type: {
            "label": provider["label"],
            "description": provider["description"],
            "fields": provider["fields"],
        }
        for provider_type, provider in PROVIDER_TYPES.items()
    }


def provider_secret_fields(provider_type: str) -> set[str]:
    spec = provider_spec(provider_type)
    return {
        str(field["name"])
        for field in spec.get("fields", [])
        if field.get("secret")
    }


def provider_required_fields(provider_type: str) -> set[str]:
    spec = provider_spec(provider_type)
    return {
        str(field["name"])
        for field in spec.get("fields", [])
        if field.get("required")
    }


def provider_field_default(provider_type: str, field_name: str) -> Any:
    spec = provider_spec(provider_type)
    for field in spec.get("fields", []):
        if str(field.get("name") or "") == field_name and "default" in field:
            return field["default"]
    return None


def provider_env_fields(provider_type: str) -> dict[str, str]:
    spec = provider_spec(provider_type)
    env_vars = spec.get("envVars", {})
    return {str(name): str(value) for name, value in dict(env_vars).items()}


def provider_env_binding_names() -> list[str]:
    names: list[str] = []
    for provider_type in PROVIDER_TYPES:
        for env_name in provider_env_fields(provider_type).values():
            if env_name not in names:
                names.append(env_name)
    return names


def provider_env_id(provider_type: str) -> str:
    spec = provider_spec(provider_type)
    env_id = str(spec.get("envId") or "").strip()
    return env_id or f"{provider_type}-env"
