from fastapi import APIRouter

from app.api.routes import cases, files

api_router = APIRouter()


@api_router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


api_router.include_router(cases.router, prefix="/cases", tags=["cases"])
api_router.include_router(files.router, tags=["files"])
