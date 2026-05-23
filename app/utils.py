import os
import time
import string
from fastapi import HTTPException
from app.redis import get_redis_client

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
    if os.getenv("DISABLE_RATE_LIMITING") == "true":
        return
        
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

def log_click(short_code: str, referrer: str | None, user_agent: str | None, country: str | None):
    from app.db import SessionLocal
    from app.models.click import Click
    
    db = SessionLocal()
    try:
        new_click = Click(
            short_code=short_code,
            referrer=referrer,
            user_agent=user_agent,
            country=country
        )
        db.add(new_click)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
