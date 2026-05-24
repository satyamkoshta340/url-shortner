from fastapi import FastAPI
from app.routers import shorten, redirect, stats

app = FastAPI()

app.include_router(shorten.router)
app.include_router(stats.router)
app.include_router(redirect.router)

@app.get("/health")
def health():
    return {"status": "ok"}
