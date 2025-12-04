from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from app.api.endpoints.user import get_current_admin, get_current_user
from app.models.user import user_model
from app.models.vendor import CreateVendorRequest, Vendor, vendor_model
from app.schemas.user import User, UserType
from app.schemas.vendor import UpdateVendorRequest, VendorStatus
from app.services.geocoding import geocoding_service

router = APIRouter()


@router.get("/me", response_model=Vendor)
async def get_self(
    current_user: Annotated[User, Depends(get_current_user)],
) -> Vendor:
    return await vendor_model.get_vendor_by_id(current_user.entity_id)


@router.post("/new", response_model=Vendor)
async def create_vendor(
    vendor: Annotated[CreateVendorRequest, Body(...)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.user_type != UserType.VENDOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only users with vendor role can create a vendor",
        )

    if current_user.entity_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already been associated with a vendor",
        )

    if not vendor.address or not vendor.address.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Address is required to create a vendor",
        )

    try:
        location = await geocoding_service.location_to_coordinates(vendor.address)
    except HTTPException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid address: {e.detail}. "
                "Please provide a valid address that can be geocoded."
            ),
        ) from e

    return await vendor_model.create_vendor(vendor, current_user.id, location)


@router.get("/all", response_model=list[Vendor])
async def get_vendors(
    status: Annotated[VendorStatus | None, None] = None,
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lng: Annotated[float | None, Query(ge=-180, le=180)] = None,
    distance_km: Annotated[float | None, Query(gt=0, le=200)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
):
    return await vendor_model.get_all_vendors(
        status=status, lat=lat, lng=lng, distance_km=distance_km, page=page, limit=limit
    )


@router.get("/approve/{vendor_id}", response_model=None)
async def approve_vendor(vendor_id: str, current_user: Annotated[User, Depends(get_current_admin)]):
    return await vendor_model.approve_vendor(vendor_id)


@router.get("/{vendor_id}", response_model=Vendor)
async def get_vendor_by_id(vendor_id: str) -> Vendor:
    return await vendor_model.get_vendor_by_id(vendor_id)


@router.delete("/clear", response_model=None)
async def clear_vendors():
    return await vendor_model.delete_all_vendors()


@router.put("/{vendor_id}", response_model=Vendor)
async def update_vendor(
    vendor_id: str,
    vendor: Annotated[UpdateVendorRequest, Body(...)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Vendor:
    if current_user.user_type != UserType.ADMIN:
        if current_user.entity_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are not associated with any vendor",
            )
        if not await user_model.owns_entity(current_user.id, vendor_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update this vendor",
            )

    location = None
    if vendor.address:
        location = await geocoding_service.location_to_coordinates(vendor.address)

    return await vendor_model.update_vendor(vendor_id, vendor, location)
