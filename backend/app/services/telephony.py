import logging
import hmac
import hashlib
import time

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

ZADARMA_BASE = "https://api.zadarma.com"


class ZadarmaService:
    def _auth_header(self, params: str) -> dict:
        sign = hmac.new(
            settings.zadarma_secret.encode(),
            params.encode(),
            hashlib.sha1,
        ).hexdigest()
        return {"Authorization": f"{settings.zadarma_key}:{sign}"}

    async def initiate_call(self, from_number: str, to_number: str) -> dict:
        if not settings.zadarma_key:
            logger.info("Zadarma not configured, mock call: %s → %s", from_number, to_number)
            return {"status": "mock", "from": from_number, "to": to_number}

        params = f"from={from_number}&to={to_number}&predicted=1"
        headers = self._auth_header(params)
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{ZADARMA_BASE}/v1/request/callback/",
                params={"from": from_number, "to": to_number, "predicted": 1},
                headers=headers,
            )
            return r.json()

    async def get_call_record(self, call_id: str) -> dict:
        if not settings.zadarma_key:
            return {"status": "mock", "call_id": call_id}
        params = f"call_id={call_id}"
        headers = self._auth_header(params)
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{ZADARMA_BASE}/v1/pbx/record/request/",
                params={"call_id": call_id},
                headers=headers,
            )
            return r.json()


zadarma = ZadarmaService()
