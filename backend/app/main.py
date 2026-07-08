from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.routers import common, learning, tools
from app.core.config import API_PREFIX, APP_NAME, FRONTEND_DIR
from app.db.database import initialize_database


initialize_database()

app = FastAPI(title=APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(common.router, prefix=API_PREFIX)
app.include_router(learning.router, prefix=API_PREFIX)
app.include_router(tools.router, prefix=API_PREFIX)

app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
