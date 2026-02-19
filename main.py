from contextlib import asynccontextmanager
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlmodel import SQLModel
from core.database import create_db_and_tables
from routers import motor_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

API_KEY = os.getenv("API_KEY")


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    if request.headers.get("X-API-Key") != API_KEY:
        return JSONResponse(status_code=401, content={"detail": "No autorizado"})
    return await call_next(request)


app.include_router(motor_router)
