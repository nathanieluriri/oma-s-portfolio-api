import logging
import os

import httpx


logger = logging.getLogger(__name__)

NEXT_SITE_URL = os.getenv("NEXT_SITE_URL") or os.getenv("NEXT_PUBLIC_SITE_URL")
REVALIDATE_SECRET = os.getenv("REVALIDATE_SECRET")


async def trigger_portfolio_revalidate() -> bool:
    if not NEXT_SITE_URL or not REVALIDATE_SECRET:
        logger.warning("Next.js revalidate skipped: missing NEXT_SITE_URL/REVALIDATE_SECRET")
        return False

    url = f"{NEXT_SITE_URL.rstrip('/')}/api/revalidate"
    headers = {"x-revalidate-token": REVALIDATE_SECRET}

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(url, headers=headers)
        if response.status_code != 200:
            logger.warning("Next.js revalidate failed: %s", response.status_code)
            return False
        return True
    except Exception:
        logger.exception("Next.js revalidate error")
        return False
