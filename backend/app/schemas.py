from typing import Any

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class RegisterCustomerRequest(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=6)
    phone_country_code: str | None = "+91"
    phone_number: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


class RoomRequest(BaseModel):
    room_number: int
    room_type_id: int
    floor: int = 1
    status: str = "AVAILABLE"


class RoomTypeRequest(BaseModel):
    type_name: str
    capacity: int = 1
    price_per_night: float
    description: str | None = None


class BookingRequest(BaseModel):
    room_id: int
    check_in_date: str
    check_out_date: str


class StatusRequest(BaseModel):
    status: str


class PaymentRequest(BaseModel):
    booking_id: int
    method_id: int
    amount: float


class ServiceRequest(BaseModel):
    booking_id: int
    service_id: int
    quantity: int = Field(default=1, ge=1)


class DepartmentRequest(BaseModel):
    department_name: str
    head_manager_id: int | None = None

