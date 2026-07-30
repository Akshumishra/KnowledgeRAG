from fastapi import APIRouter, Depends

from src.api.dependencies import get_current_user, get_uow
from src.database.uow import UnitOfWork
from src.models.auth import User
from src.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
async def get_dashboard_metrics(
    uow: UnitOfWork = Depends(get_uow), current_user: User = Depends(get_current_user)
):
    service = AnalyticsService(uow)
    return await service.get_dashboard_metrics(current_user.workspace_id, current_user)
