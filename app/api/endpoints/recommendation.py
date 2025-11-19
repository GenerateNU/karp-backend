from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.endpoints.user import get_current_user
from app.schemas.event import Event
from app.schemas.user import User, UserType
from app.services.recommendation import recommendation_service

router = APIRouter()


@router.get("/events", response_model=list[Event])
async def get_event_recommendations(
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[Event]:
    if current_user.user_type != UserType.VOLUNTEER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only volunteers can access recommendations",
        )

    if current_user.entity_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must be associated with a volunteer profile",
        )

    recommendations = await recommendation_service.get_recommendations_for_volunteer(
        current_user.entity_id
    )

    events = [rec["event"] for rec in recommendations]

    return events


@router.get("/events/scores")
async def get_event_recommendations_with_scores(
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.user_type != UserType.VOLUNTEER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only volunteers can access recommendations",
        )

    if current_user.entity_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must be associated with a volunteer profile",
        )

    recommendations = await recommendation_service.get_recommendations_for_volunteer(
        current_user.entity_id
    )

    return {
        "volunteer_id": current_user.entity_id,
        "total_recommendations": len(recommendations),
        "recommendations": [
            {"event": rec["event"], "score": rec["score"]} for rec in recommendations
        ],
    }
