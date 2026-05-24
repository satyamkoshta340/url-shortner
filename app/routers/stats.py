from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.url import URL
from app.models.click import Click

router = APIRouter()

@router.get("/stats/{short_code}")
def get_stats(short_code: str, db: Session = Depends(get_db)):
    url = db.query(URL).filter(URL.short_code == short_code).first()
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")

    total_clicks = db.query(func.count(Click.id)).filter(Click.short_code == short_code).scalar() or 0

    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    
    # SQLite uses date() func, Postgres uses DATE() or date_trunc
    # func.date() works in many dialects but explicit cast is safer for cross-db
    from sqlalchemy import cast, Date
    
    daily_clicks_query = (
        db.query(
            cast(Click.timestamp, Date).label('date'),
            func.count(Click.id).label('count')
        )
        .filter(Click.short_code == short_code)
        .filter(Click.timestamp >= seven_days_ago)
        .group_by(cast(Click.timestamp, Date))
        .order_by(cast(Click.timestamp, Date))
        .all()
    )

    daily_clicks = [{"date": str(row.date), "clicks": row.count} for row in daily_clicks_query]

    return {
        "short_code": short_code,
        "original_url": url.original_url,
        "created_at": url.created_at,
        "total_clicks": total_clicks,
        "clicks_last_7_days": daily_clicks
    }
