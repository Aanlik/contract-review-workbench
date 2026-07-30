from fastapi import APIRouter

from app.api.routes import ai, audit, cases, exports, files, issues, review_runs, settings, tasks

api_router = APIRouter()


@api_router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


api_router.include_router(cases.router, prefix="/cases", tags=["cases"])
api_router.include_router(files.router, tags=["files"])
api_router.include_router(issues.router, tags=["issues"])
api_router.include_router(exports.router, tags=["exports"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(ai.router, tags=["ai"])
api_router.include_router(review_runs.router, tags=["review"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(audit.router, tags=["audit"])
