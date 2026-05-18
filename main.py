"""Verity — entry point for local development."""
import uvicorn
from verity.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "verity.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.env == "development",
        log_level=settings.log_level.lower(),
    )
