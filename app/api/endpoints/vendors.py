from typing import Annotated

from fastapi import APIRouter, Body

from app.models.vendor import vendor_model
from app.schemas.vendor import CreateVendorRequest, Vendor

router = APIRouter()


@router.post("/new", response_model=Vendor)
async def create_vendor(vendor: Annotated[CreateVendorRequest, Body(...)]):
    return await vendor_model.create_vendor(vendor)


@router.get("/all", response_model=list[Vendor])
async def get_vendors():
    return await vendor_model.get_all_vendors()


@router.delete("/clear", response_model=None)
async def clear_vendors():
    return await vendor_model.delete_all_vendors()
