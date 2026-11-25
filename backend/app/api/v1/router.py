"""Main v1 API router that includes all sub-routers."""

from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.verify import router as verify_router
from app.api.v1.rag import router as rag_router
from app.api.v1.reports import router as reports_router
from app.api.v1.history import router as history_router
from app.api.v1.admin import router as admin_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(verify_router)
api_router.include_router(rag_router)
api_router.include_router(reports_router)
api_router.include_router(history_router)
api_router.include_router(admin_router)
