from dataclasses import dataclass
from typing import Protocol

import httpx


@dataclass(frozen=True)
class PaymentCheckout:
    provider_transaction_id: str
    checkout_url: str | None = None


class PaymentProvider(Protocol):
    async def create_checkout(
        self, *, amount: int, plan: str, merchant_transaction_id: str
    ) -> PaymentCheckout: ...


class HttpPaymentProvider:
    """Provider-neutral HTTP adapter; provider-specific gateways implement this contract."""

    def __init__(self, base_url: str, api_key: str, *, timeout_seconds: float = 10.0) -> None:
        if (
            not base_url.startswith(("https://", "http://"))
            or not api_key.strip()
            or timeout_seconds <= 0
        ):
            raise ValueError("Payment provider URL and API key are required")
        self._endpoint = base_url.rstrip("/") + "/v1/checkout"
        self._api_key = api_key
        self._timeout = timeout_seconds

    async def create_checkout(
        self, *, amount: int, plan: str, merchant_transaction_id: str
    ) -> PaymentCheckout:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                self._endpoint,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "amount": amount,
                    "plan": plan,
                    "merchant_transaction_id": merchant_transaction_id,
                },
            )
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("provider_transaction_id"), str):
            raise TypeError("Payment provider returned an invalid checkout")
        checkout_url = payload.get("checkout_url")
        if checkout_url is not None and not isinstance(checkout_url, str):
            raise TypeError("Payment provider returned an invalid checkout URL")
        return PaymentCheckout(payload["provider_transaction_id"], checkout_url)
