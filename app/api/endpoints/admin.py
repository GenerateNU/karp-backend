from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status

from app.api.endpoints.user import get_current_admin
from app.models.admin import admin_model
from app.models.event import event_model
from app.models.item import item_model
from app.models.organization import org_model
from app.models.vendor import vendor_model
from app.schemas.admin import (
    AdminResponse,
    CreateAdminRequest,
    UpdateEventRequest,
    UpdateItemRequest,
    UpdateOrganizationRequest,
    UpdateVendorRequest,
)
from app.schemas.event import Status as EventStatus
from app.schemas.event import UpdateEventStatusRequest
from app.schemas.organization import Status
from app.schemas.user import User
from app.schemas.vendor import VendorStatus

router = APIRouter()


@router.post("/create", response_model=AdminResponse)
async def create_admin(
    admin_data: Annotated[CreateAdminRequest, Body(...)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> AdminResponse:

    # Check if admin already exists
    try:
        print(admin_data.email)
        existing_admin = await admin_model.get_admin_by_email(admin_data.email)
        print("existing_admin", existing_admin)
        if existing_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin with this email already exists",
            )
    except ValueError:
        pass

    admin = await admin_model.create_admin(current_user.id)
    admin_dict = admin.model_dump()
    admin_dict["user_type"] = "ADMIN"
    return AdminResponse(**admin_dict)


@router.get("/all", response_model=list[AdminResponse])
async def get_all_admins(
    current_user: Annotated[User, Depends(get_current_admin)],
) -> list[AdminResponse]:

    admins = await admin_model.get_all_admins()
    return [AdminResponse(**admin.model_dump()) for admin in admins]


@router.post("/change-status/organization", response_model=None)
async def change_org_status(
    approval_data: Annotated[UpdateOrganizationRequest, Body(...)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> None:

    # Update organization status

    update_data = UpdateOrganizationRequest(status=Status(approval_data.status))
    await org_model.update_organization(approval_data.organization_id, update_data)


@router.post("/change-status/vendor", response_model=None)
async def change_vendor_status(
    approval_data: Annotated[UpdateVendorRequest, Body(...)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> None:

    update_data = UpdateVendorRequest(status=VendorStatus(approval_data.status))
    await vendor_model.update_vendor(approval_data.vendor_id, update_data)


@router.post("/change-status/item", response_model=None)
async def change_item_status(
    approval_data: Annotated[UpdateItemRequest, Body(...)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> None:

    update_data = UpdateItemRequest(status=approval_data.status)
    await item_model.update_item(update_data, approval_data.item_id)


@router.post("/change-status/event", response_model=None)
async def change_event_status(
    approval_data: Annotated[UpdateEventRequest, Body(...)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> None:

    update_data = UpdateEventStatusRequest(status=EventStatus(approval_data.status))
    await event_model.update_event(approval_data.event_id, update_data)
