# app/schemas.py
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr

from paycharm.app.utils.enums import OrderStatus


class OrderItemCreate(BaseModel):
    name: str
    quantity: int
    unit_price: float


class OrderItemRead(BaseModel):
    id: int
    name: str
    quantity: int
    unit_price: float
    line_amount: float

    class Config:
        orm_mode = True


class OrderCreate(BaseModel):
    items: List[OrderItemCreate]
    delivery_address: Optional[str]
    contact_email: Optional[EmailStr]
    contact_phone: Optional[str]
    total_amount: float
    status: OrderStatus
    source_message: str


class OrderRead(BaseModel):
    id: int
    created_at: datetime
    updated_at: datetime
    status: OrderStatus
    delivery_address: Optional[str]
    contact_email: Optional[EmailStr]
    contact_phone: Optional[str]
    total_amount: float

    class Config:
        orm_mode = True
