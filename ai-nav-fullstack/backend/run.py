import uvicorn

from app.core.config import API_WORKERS, APP_ENV


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8088,
        reload=APP_ENV == "development",
        workers=API_WORKERS,
    )
