from fastapi import APIRouter, Depends
from typing import List
from src.schemas.user import UserResponse
from src.services.user_service import UserService
from src.api.dependencies import get_service, get_current_user
from src.models.auth import User

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=List[UserResponse])
async def list_users(
    service: UserService = Depends(get_service(UserService)),
    current_user: User = Depends(get_current_user),
):
    users = await service.list(current_user.workspace_id)
    return [
        UserResponse(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role="user",
            is_active=u.is_active,
            last_login=u.last_login,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.delete("/{user_id}", status_code=204)
async def remove_user_from_workspace(
    user_id: str,
    service: UserService = Depends(get_service(UserService)),
    current_user: User = Depends(get_current_user),
):
    await service.remove_from_workspace(
        user_id, current_user.workspace_id, current_user
    )


from src.schemas.user import UserActivityRequest, UserActivityResponse


@router.get("/activity", response_model=UserActivityResponse)
async def get_user_activity(
    service: UserService = Depends(get_service(UserService)),
    current_user: User = Depends(get_current_user),
):
    activity = await service.get_activity(current_user.id)
    return UserActivityResponse.model_validate(activity)


@router.post("/activity", response_model=UserActivityResponse)
async def update_user_activity(
    request: UserActivityRequest,
    service: UserService = Depends(get_service(UserService)),
    current_user: User = Depends(get_current_user),
):
    activity = await service.update_activity(
        current_user.id, request.last_route, request.last_conversation_id
    )
    return UserActivityResponse.model_validate(activity)
