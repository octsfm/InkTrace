"""V1.1 Workbench health route.

Stage 0 only exposes the health endpoint for the `/api/v1/*` namespace. Business
routes are handled by later stages and must not be added here.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["v1-health"])


@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "scope": "workbench",
        "api": "v1",
    }

