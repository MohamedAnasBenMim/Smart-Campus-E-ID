from fastapi import FastAPI
from app.routers import recognition

app = FastAPI(
    title="Smart Campus E-ID — Service de reconnaissance faciale",
    version="0.1.0",
)

app.include_router(recognition.router)