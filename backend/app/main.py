from fastapi import FastAPI

from app.api.router import api_router
from app.core.database import engine
from app.models.base import Base
from app.models import review  # noqa: F401


def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)
    app = FastAPI(title="Contract Review Workbench")
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
