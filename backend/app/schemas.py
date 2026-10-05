import re
from datetime import date
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    model_validator,
)


class AppBaseModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


# ---------- allowed values ----------
RoomStatus = Literal["AVAILABLE", "OCCUPIED", "MAINTENANCE", "RESERVED"]
BookingStatus = Literal[
    "PENDING", "APPROVED", "REJECTED", "CHECKIN_PENDING", "CHECKED_IN",
    "CHECKOUT_PENDING", "CHECKED_OUT", "CANCELLED",
]
MaintenanceStatus = Literal["PENDING", "IN_PROGRESS", "COMPLETED"]


# ---------- reusable field rules (limits match the DB columns) ----------
def _normalize_email(value: str) -> str:
    if len(value) > 100:
        raise ValueError("Email must be at most 100 characters")
    return value.lower()


def _check_strength(value: str) -> str:
    if not re.search(r"[A-Za-z]", value):
        raise ValueError("Password must contain at least one letter")
    if not re.search(r"\d", value):
        raise ValueError("Password must contain at least one digit")
    return value


Email = Annotated[EmailStr, AfterValidator(_normalize_email)]
StrongPassword = Annotated[str, StringConstraints(min_length=8, max_length=72), AfterValidator(_check_strength)]
AnyPassword = Annotated[str, StringConstraints(min_length=1, max_length=128)]
NameStr = Annotated[str, StringConstraints(min_length=1, max_length=100)]
PhoneCountryCode = Annotated[str, StringConstraints(pattern=r"^\+\d{1,4}$", min_length=2, max_length=5)]
PhoneNumber = Annotated[str, StringConstraints(pattern=r"^\d{6,15}$", min_length=6, max_length=15)]
Money = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]
SalaryMoney = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]
RoomTypeName = Annotated[str, StringConstraints(min_length=1, max_length=50)]
JobText = Annotated[str, StringConstraints(max_length=100)]
Id = Annotated[int, Field(gt=0)]


# ---------- auth ----------
class LoginRequest(AppBaseModel):
    email: Email
    password: AnyPassword


class RegisterCustomerRequest(AppBaseModel):
    name: NameStr
    email: Email
    password: StrongPassword
    phone_country_code: PhoneCountryCode | None = "+91"
    phone_number: PhoneNumber | None = None


class ChangePasswordRequest(AppBaseModel):
    current_password: AnyPassword
    new_password: StrongPassword

    @model_validator(mode="after")
    def passwords_must_differ(self):
        if self.current_password == self.new_password:
            raise ValueError("New password must be different from current password")
        return self


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


class ProfileUpdateRequest(AppBaseModel):
    name: NameStr | None = None
    phone_country_code: PhoneCountryCode | None = None
    phone_number: PhoneNumber | None = None
    address: Annotated[str, StringConstraints(max_length=255)] | None = None
    id_proof: Annotated[str, StringConstraints(max_length=100)] | None = None
    nationality: Annotated[str, StringConstraints(max_length=50)] | None = None


# ---------- rooms ----------
class RoomRequest(AppBaseModel):
    room_number: int = Field(gt=0)
    room_type_id: Id
    floor: int = Field(default=1, ge=0)
    status: RoomStatus = "AVAILABLE"


class RoomTypeRequest(AppBaseModel):
    type_name: RoomTypeName
    capacity: int = Field(default=1, ge=1, le=20)
    price_per_night: Money
    description: Annotated[str, StringConstraints(max_length=255)] | None = None


class RoomStatusRequest(AppBaseModel):
    status: RoomStatus


# ---------- bookings ----------
class BookingRequest(AppBaseModel):
    room_id: Id
    check_in_date: date
    check_out_date: date
    customer_id: Id | None = None  # only used by staff booking on behalf of a walk-in guest

    @model_validator(mode="after")
    def validate_dates(self):
        if self.check_in_date < date.today():
            raise ValueError("Check-in date cannot be in the past")
        if self.check_out_date <= self.check_in_date:
            raise ValueError("Check-out date must be after check-in date")
        if (self.check_out_date - self.check_in_date).days > 30:
            raise ValueError("Stay cannot exceed 30 nights")
        return self


class BookingStatusRequest(AppBaseModel):
    status: BookingStatus
    rejection_reason: Annotated[str, StringConstraints(max_length=255)] | None = None
    override_balance: bool = False

    @model_validator(mode="after")
    def reason_only_when_rejecting(self):
        if self.rejection_reason and self.status != "REJECTED":
            raise ValueError("A reason can only be given when rejecting a booking")
        return self


# ---------- billing & services ----------
class PaymentRequest(AppBaseModel):
    booking_id: Id
    method_id: Id
    amount: Money


class ServiceRequest(AppBaseModel):
    booking_id: Id
    service_id: Id
    quantity: int = Field(default=1, ge=1, le=100)


class ServiceCreateRequest(AppBaseModel):
    service_name: Annotated[str, StringConstraints(min_length=1, max_length=100)]
    price: Money


class ServiceUpdateRequest(AppBaseModel):
    service_name: Annotated[str, StringConstraints(min_length=1, max_length=100)] | None = None
    price: Money | None = None


# ---------- people ----------
class DepartmentRequest(AppBaseModel):
    department_name: NameStr
    head_manager_id: Id | None = None


class ActiveRequest(AppBaseModel):
    active: bool


class ResetPasswordRequest(AppBaseModel):
    temporary_password: StrongPassword


class StaffCreateRequest(AppBaseModel):
    name: NameStr
    email: Email
    phone_country_code: PhoneCountryCode | None = "+91"
    phone_number: PhoneNumber | None = None
    department_id: Id
    manager_id: Id | None = None  # honoured for admins only; managers always use their own id
    job_description: JobText | None = None
    salary: SalaryMoney
    temporary_password: StrongPassword


class StaffUpdateRequest(AppBaseModel):
    name: NameStr | None = None
    phone_country_code: PhoneCountryCode | None = None
    phone_number: PhoneNumber | None = None
    department_id: Id | None = None
    manager_id: Id | None = None
    job_description: JobText | None = None
    salary: SalaryMoney | None = None


class ManagerCreateRequest(AppBaseModel):
    name: NameStr
    email: Email
    phone_country_code: PhoneCountryCode | None = "+91"
    phone_number: PhoneNumber | None = None
    department_id: Id
    reports_to_manager_id: Id | None = None
    job_description: JobText | None = None
    salary: SalaryMoney
    temporary_password: StrongPassword


class ManagerUpdateRequest(AppBaseModel):
    name: NameStr | None = None
    phone_country_code: PhoneCountryCode | None = None
    phone_number: PhoneNumber | None = None
    department_id: Id | None = None
    reports_to_manager_id: Id | None = None
    job_description: JobText | None = None
    salary: SalaryMoney | None = None


class CustomerCreateRequest(AppBaseModel):
    name: NameStr
    email: Email
    phone_country_code: PhoneCountryCode | None = "+91"
    phone_number: PhoneNumber | None = None
    temporary_password: StrongPassword


# ---------- maintenance ----------
class MaintenanceCreateRequest(AppBaseModel):
    room_id: Id
    description: Annotated[str, StringConstraints(min_length=1, max_length=255)]
    staff_id: Id | None = None


class MaintenanceUpdateRequest(AppBaseModel):
    status: MaintenanceStatus | None = None
    staff_id: Id | None = None
    description: Annotated[str, StringConstraints(min_length=1, max_length=255)] | None = None
