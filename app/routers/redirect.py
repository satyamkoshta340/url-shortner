from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.url import URL
from app.redis import get_redis_client
from app.utils import check_rate_limit

router = APIRouter()

@router.get("/{short_code}")
def redirect(request: Request, short_code: str, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip, "redirect", 100, 60)

    if not short_code.isalnum():
        raise HTTPException(status_code=400, detail="Malformed short code")

    redis_client = get_redis_client()
    cache_key = f"url:{short_code}"
    hits_key = f"hits:{short_code}"

    try:
        hits = redis_client.incr(hits_key)
    except Exception:
        hits = 0

    try:
        cached_url = redis_client.get(cache_key)
        if cached_url:
            return RedirectResponse(url=cached_url, status_code=302)
    except Exception:
        pass

    url = db.query(URL).filter(URL.short_code == short_code).first()
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")
        
    if url.expires_at and url.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="URL has expired")

    ttl = 3600 if hits > 50 else 600
    try:
        redis_client.setex(cache_key, ttl, url.original_url)
    except Exception:
        pass

    return RedirectResponse(url=url.original_url, status_code=302)
