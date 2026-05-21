import hashlib
import random
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import HttpUrl
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db import get_db
from app.models.url import URL
from app.utils import base62_encode, check_rate_limit, BASE62_ALPHABET

router = APIRouter()

@router.post("/shorten")
def shorten(request: Request, long_url: HttpUrl, db: Session = Depends(get_db)) -> dict:
    long_url_str = str(long_url)
    
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip, "shorten", 10, 60)
    
    hash_obj = hashlib.md5(long_url_str.encode())
    num = int.from_bytes(hash_obj.digest()[:8], "little")
    base_code = base62_encode(num)[:8]
    
    for attempt in range(4):
        code = base_code
        if attempt > 0:
            suffix = "".join(random.choices(BASE62_ALPHABET, k=attempt))
            code += suffix
            
        existing = db.query(URL).filter(URL.short_code == code).first()
        if existing:
            if existing.original_url == long_url_str:
                return {"short_code": code}
            if attempt == 3:
                break
            continue
            
        new_url = URL(original_url=long_url_str, short_code=code)
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
