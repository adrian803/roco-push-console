from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class DeliveryContext:
    message: Any
    sender: Callable[..., Any]
    session_factory: Callable[[], Any]
    timeout: int


@dataclass(frozen=True)
class DeliveryReport:
    success: bool
    mode: str
    results: list[Any]

    def summary(self) -> str:
        if not self.results:
            return "没有可用推送通道"
        ok_count = sum(1 for item in self.results if item.success)
        return f"{ok_count}/{len(self.results)} 个通道成功"

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "mode": self.mode,
            "summary": self.summary(),
            "results": [item.to_dict() for item in self.results],
        }


def send_delivery_with_options(
    providers: list[Any],
    delivery_options: Any,
    context: DeliveryContext,
) -> DeliveryReport:
    enabled = [provider for provider in providers if provider.enabled]
    mode = delivery_options.mode
    if mode not in {"all", "single", "failover"}:
        mode = "all"

    targets = _delivery_targets(enabled, mode, delivery_options)
    if mode == "all":
        with ThreadPoolExecutor(max_workers=len(targets) or 1) as executor:
            results = list(
                executor.map(
                    lambda provider: _send_with_new_session(provider, context),
                    targets,
                )
            )
        return DeliveryReport(any(result.success for result in results), mode, results)

    return _send_sequential(
        targets,
        mode=mode,
        context=context,
        session=delivery_options.session,
    )


def _delivery_targets(enabled: list[Any], mode: str, delivery_options: Any) -> list[Any]:
    if mode == "single":
        return [
            provider
            for provider in enabled
            if provider.id == delivery_options.selected_provider
        ]
    if mode == "failover":
        order = delivery_options.failover_order or [provider.id for provider in enabled]
        provider_map = {provider.id: provider for provider in enabled}
        return [provider_map[item] for item in order if item in provider_map]
    return enabled


def _send_with_new_session(provider: Any, context: DeliveryContext) -> Any:
    with context.session_factory() as provider_session:
        return context.sender(
            provider,
            context.message,
            session=provider_session,
            timeout=context.timeout,
        )


def _send_sequential(
    targets: list[Any],
    *,
    mode: str,
    context: DeliveryContext,
    session: Any,
) -> DeliveryReport:
    if session is not None:
        results = _send_targets(targets, mode=mode, context=context, session=session)
    else:
        with context.session_factory() as client:
            results = _send_targets(targets, mode=mode, context=context, session=client)
    return DeliveryReport(any(result.success for result in results), mode, results)


def _send_targets(
    targets: list[Any],
    *,
    mode: str,
    context: DeliveryContext,
    session: Any,
) -> list[Any]:
    results: list[Any] = []
    for provider in targets:
        result = context.sender(
            provider,
            context.message,
            session=session,
            timeout=context.timeout,
        )
        results.append(result)
        if mode == "failover" and result.success:
            break
    return results
