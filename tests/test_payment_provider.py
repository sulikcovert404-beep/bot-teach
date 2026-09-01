from typing import Self

import pytest

from app.services.payment_provider import HttpPaymentProvider


@pytest.mark.asyncio
async def test_http_payment_provider_creates_checkout(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"provider_transaction_id": "gateway-123", "checkout_url": "https://pay.test/123"}

    class Client:
        def __init__(self, **kwargs: object) -> None:
            captured["timeout"] = kwargs["timeout"]

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, url: str, *, headers: dict[str, str], json: dict[str, object]) -> Response:
            captured.update(url=url, headers=headers, json=json)
            return Response()

    monkeypatch.setattr("httpx.AsyncClient", Client)
    checkout = await HttpPaymentProvider("https://gateway.test", "api-key").create_checkout(
        amount=250_000,
        plan="STUDENT_PLUS",
        merchant_transaction_id="merchant-1",
    )

    assert checkout.provider_transaction_id == "gateway-123"
    assert checkout.checkout_url == "https://pay.test/123"
    assert captured == {
        "timeout": 10.0,
        "url": "https://gateway.test/v1/checkout",
        "headers": {"Authorization": "Bearer api-key"},
        "json": {"amount": 250_000, "plan": "STUDENT_PLUS", "merchant_transaction_id": "merchant-1"},
    }


def test_http_payment_provider_rejects_missing_configuration() -> None:
    with pytest.raises(ValueError):
        HttpPaymentProvider("", "")
