import hashlib
import random
import string
import time
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal
from app.models.url import URL
from app.redis import get_redis_client

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

BASE62_ALPHABET = string.digits + string.ascii_lowercase + string.ascii_uppercase

def base62_encode(num: int) -> str:
    if num == 0:
        return BASE62_ALPHABET[0]
    res = []
    base = len(BASE62_ALPHABET)
    while num > 0:
        res.append(BASE62_ALPHABET[num % base])
        num //= base
    return "".join(reversed(res))

def check_rate_limit(client_ip: str, endpoint: str, limit: int, window: int = 60):
    if not client_ip:
        return
        
    redis_client = get_redis_client()
    current_window = int(time.time() // window)
    key = f"rate_limit:{endpoint}:{client_ip}:{current_window}"
    
    try:
        count = redis_client.incr(key)
        if count == 1:
            redis_client.expire(key, window)
            
        if count > limit:
            next_window_time = (current_window + 1) * window
            retry_after = next_window_time - int(time.time())
            raise HTTPException(
                status_code=429,
                detail="Too Many Requests",
                headers={"Retry-After": str(max(retry_after, 1))}
            )
    except HTTPException:
        raise
    except Exception:
        # Fallback if Redis is down
        pass


@app.get("/health")
def health():
  return {"status": "ok"}

@app.post("/shorten")
def shorten(request: Request, long_url: str, db: Session = Depends(get_db)) -> dict:
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip, "shorten", 10, 60)
    # Implement Base62 encoder (characters 0–9, a–z, A–Z) — this is the core algorithm, understand it deeply
    # Handle collision: if code exists, append a random suffix and retry (max 3 attempts)
    hash_obj = hashlib.md5(long_url.encode())
    num = int.from_bytes(hash_obj.digest()[:8], "little")
    base_code = base62_encode(num)[:8]
    
    for attempt in range(4):  # Initial try + max 3 retries
        code = base_code
        if attempt > 0:
            suffix = "".join(random.choices(BASE62_ALPHABET, k=attempt))
            code += suffix
            
        existing = db.query(URL).filter(URL.short_code == code).first()
        if existing:
            if existing.original_url == long_url:
                return {"short_code": code}
            if attempt == 3:
                break
            continue
            
        new_url = URL(original_url=long_url, short_code=code)
        db.add(new_url)
        try:
            db.commit()
            return {"short_code": code}
        except IntegrityError:
            db.rollback()
            if attempt == 3:
                break
            continue
            
    raise HTTPException(status_code=500, detail="Failed to generate short code after 3 retries")


@app.get("/{short_code}")
def redirect(request: Request, short_code: str, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip, "redirect", 100, 60)

    # look up DB, return HTTP 301/302 redirect to original URL
    # Input validation: reject invalid URLs, malformed codes, and expired links (404)
    if not short_code.isalnum():
        raise HTTPException(status_code=400, detail="Malformed short code")

    redis_client = get_redis_client()
    cache_key = f"url:{short_code}"
    hits_key = f"hits:{short_code}"

    # Track hits for popularity
    try:
        hits = redis_client.incr(hits_key)
    except Exception:
        hits = 0

    # 1. Check Redis first
    try:
        cached_url = redis_client.get(cache_key)
        if cached_url:
            return RedirectResponse(url=cached_url, status_code=302)
    except Exception:
        pass

    # 2. On miss, hit Postgres
    url = db.query(URL).filter(URL.short_code == short_code).first()
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")
        
    # 3. Check for expiration
    if url.expires_at and url.expires_at < datetime.utcnow():
        # Expired links = don't cache
        raise HTTPException(status_code=410, detail="URL has expired")

    # 4. Write result to Redis with TTL
    # Popular links = 1hr (3600s), default = 10min (600s)
    ttl = 3600 if hits > 50 else 600
    try:
        redis_client.setex(cache_key, ttl, url.original_url)
    except Exception:
        pass

    return RedirectResponse(url=url.original_url, status_code=302)
