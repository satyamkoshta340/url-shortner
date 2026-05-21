from fastapi import FastAPI
from app.routers import shorten, redirect

app = FastAPI()

app.include_router(shorten.router)
app.include_router(redirect.router)

@app.get("/health")
def health():
    return {"status": "ok"}
