from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from app.api.endpoints.user import get_current_user
from app.models.organization import org_model
from app.models.user import user_model
from app.schemas.organization import (
    CreateOrganizationRequest,
    Organization,
    UpdateOrganizationRequest,
)
from app.schemas.user import User, UserType
from app.services.geocoding import geocoding_service

router = APIRouter()


@router.get("/me", response_model=Organization)
async def get_self(
    current_user: Annotated[User, Depends(get_current_user)],
) -> Organization:
    return await org_model.get_organization_by_id(current_user.entity_id)


@router.get("/all", response_model=list[Organization])
async def get_organizations(
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lng: Annotated[float | None, Query(ge=-180, le=180)] = None,
    distance_km: Annotated[float | None, Query(gt=0, le=200)] = None,
) -> list[Organization]:
    return await org_model.get_all_organizations(lat=lat, lng=lng, distance_km=distance_km)


@router.get("/{org_id}", response_model=Organization)
async def get_organization_by_id(org_id: str) -> Organization:
    organization = await org_model.get_organization_by_id(org_id)

    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    return organization


@router.post("/new", response_model=Organization)
async def create_organization(
    org: Annotated[CreateOrganizationRequest, Body(...)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Organization:
    if current_user.user_type != UserType.ORGANIZATION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only users with organization role can create a organization",
        )

    if current_user.entity_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already been associated with a organization",
        )

    location = await geocoding_service.location_to_coordinates(org.address)

    return await org_model.create_organization(org, current_user.id, location)


@router.put("/{org_id}", response_model=Organization)
async def update_organization(
    org_id: str,
    org: Annotated[UpdateOrganizationRequest, Body(...)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Organization:
    if current_user.user_type != UserType.ADMIN:
        if current_user.entity_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are not associated with any organization",
            )

        if not await user_model.owns_entity(current_user.id, org_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update this organization",
            )

    location = await geocoding_service.location_to_coordinates(org.address) if org.address else None

    return await org_model.update_organization(org_id, org, location)


@router.delete("/{org_id}", response_model=None)
async def delete_organization(
    org_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    if current_user.entity_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not associated with any organization",
        )

    if not await user_model.owns_entity(current_user.id, org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this organization",
        )

    return await org_model.delete_organization(org_id)
