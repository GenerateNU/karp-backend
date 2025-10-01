from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException, status

from app.api.endpoints.user import get_current_user
from app.models.admin import admin_model
from app.models.event import event_model
from app.models.item import item_model
from app.models.organization import org_model
from app.models.vendor import vendor_model
from app.schemas.admin import (
    AdminResponse,
    ApproveEventRequest,
    ApproveItemRequest,
    ApproveOrganizationRequest,
    ApproveVendorRequest,
    CreateAdminRequest,
    OrgApplicationID,
    VendorApplicationID,
)
from app.schemas.user import User, UserType

router = APIRouter()


@router.post("/create", response_model=AdminResponse)
async def create_admin(
    admin_data: Annotated[CreateAdminRequest, Body(...)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AdminResponse:
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can create new admin users"
        )

    # Check if admin already exists
    try:
        existing_admin = await admin_model.get_admin_by_email(admin_data.email)
        if existing_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin with this email already exists",
            )
    except ValueError:
        pass

    return await admin_model.create_admin(admin_data, current_user.id)


@router.get("/all", response_model=list[AdminResponse])
async def get_all_admins(
    current_user: Annotated[User, Depends(get_current_user)]
) -> list[AdminResponse]:
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can view admin list"
        )

    return await admin_model.get_all_admins()


@router.post("/approve/organization", response_model=None)
async def approve_organization(
    approval_data: Annotated[ApproveOrganizationRequest, Body(...)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can approve organizations"
        )

    # Update organization status
    from app.schemas.organization import Status, UpdateOrganizationRequest

    update_data = UpdateOrganizationRequest(status=Status(approval_data.status))
    await org_model.update_organization(approval_data.organization_id, update_data)

    # Add to admin's application list
    org_application = OrgApplicationID(
        id=str(ObjectId()),
        organization_id=approval_data.organization_id,
        status=approval_data.status,
    )
    await admin_model.add_org_application(current_user.id, org_application)


@router.post("/approve/vendor", response_model=None)
async def approve_vendor(
    approval_data: Annotated[ApproveVendorRequest, Body(...)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can approve vendors"
        )

    # Update vendor status
    from app.schemas.vendor import UpdateVendorRequest, VendorStatus

    update_data = UpdateVendorRequest(status=VendorStatus(approval_data.status))
    await vendor_model.update_vendor(approval_data.vendor_id, update_data)

    # Add to admin's application list
    vendor_application = VendorApplicationID(
        id=str(ObjectId()), vendor_id=approval_data.vendor_id, status=approval_data.status
    )
    await admin_model.add_vendor_application(current_user.id, vendor_application)


@router.post("/approve/item", response_model=None)
async def approve_item(
    approval_data: Annotated[ApproveItemRequest, Body(...)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can approve items"
        )

    # Update item status
    from app.schemas.item import UpdateItemRequest

    update_data = UpdateItemRequest(status=approval_data.status)
    await item_model.update_item(approval_data.item_id, update_data)


@router.post("/approve/event", response_model=None)
async def approve_event(
    approval_data: Annotated[ApproveEventRequest, Body(...)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can approve events"
        )

    # Update event status
    from app.schemas.event import Status as EventStatus
    from app.schemas.event import UpdateEventStatusRequest

    update_data = UpdateEventStatusRequest(status=EventStatus(approval_data.status))
    await event_model.update_event_status(approval_data.event_id, update_data)
