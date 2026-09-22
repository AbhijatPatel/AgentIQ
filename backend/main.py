"""
ASGI application entry point for uvicorn.
Enables running `uvicorn main:app` directly inside the backend directory,
or executing `python main.py` binding to Render's $PORT and 0.0.0.0.
"""
import os
import uvicorn
from app.main import app

__all__ = ["app"]

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, log_level="info")
