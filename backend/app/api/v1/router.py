from fastapi import APIRouter

from app.api.v1.auth.router import router as auth_router
from app.api.v1.users.router import router as users_router
from app.api.v1.institutions.router import router as institutions_router

# Main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(institutions_router, prefix="/admin/institutions", tags=["Institutions"])

# TODO: Add more routers as they are implemented
# api_router.include_router(templates_router, prefix="/templates", tags=["Templates"])
# api_router.include_router(tests_router, prefix="/tests", tags=["Tests"])
# api_router.include_router(sheets_router, prefix="/sheets", tags=["Sheets"])
# api_router.include_router(surveys_router, prefix="/surveys", tags=["Surveys"])
# api_router.include_router(attendance_router, prefix="/attendance", tags=["Attendance"])
