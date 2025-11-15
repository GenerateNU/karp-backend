from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status

from app.api.endpoints.user import get_current_admin, get_current_user
from app.models.vendor import CreateVendorRequest, Vendor, vendor_model
from app.schemas.user import User, UserType

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

    return await vendor_model.create_vendor(vendor, current_user.id)


@router.get("/all", response_model=list[Vendor])
async def get_vendors():
    return await vendor_model.get_all_vendors()


@router.get("/approve/{vendor_id}", response_model=None)
async def approve_vendor(vendor_id: str, current_user: Annotated[User, Depends(get_current_admin)]):
    return await vendor_model.approve_vendor(vendor_id)


@router.get("/{vendor_id}", response_model=Vendor)
async def get_vendor_by_id(vendor_id: str) -> Vendor:
    return await vendor_model.get_vendor_by_id(vendor_id)


@router.delete("/clear", response_model=None)
async def clear_vendors():
    return await vendor_model.delete_all_vendors()
