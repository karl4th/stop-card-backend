from fastapi import APIRouter

from app.api.routes import admin, reference, stopcards

api_router = APIRouter()
api_router.include_router(stopcards.router)
api_router.include_router(reference.router)
api_router.include_router(admin.router)
