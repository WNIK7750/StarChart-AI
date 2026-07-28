import uvicorn

from app.core.config import API_WORKERS, APP_ENV, APP_HOST, APP_PORT


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=APP_HOST,
        port=APP_PORT,
        reload=APP_ENV == "development",
        workers=API_WORKERS,
    )
