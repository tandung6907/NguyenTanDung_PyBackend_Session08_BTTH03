from datetime import date
from enum import Enum
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

app = FastAPI(title="Coworking Desk & Booking Management API")


class DeskStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    MAINTENANCE = "MAINTENANCE"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


class DeskCreate(BaseModel):
    desk_number: str = Field(..., min_length=1)
    zone: str = Field(..., min_length=1)
    price_per_day: float = Field(..., gt=0)
    status: DeskStatus


class DeskUpdate(BaseModel):
    desk_number: str = Field(..., min_length=1)
    zone: str = Field(..., min_length=1)
    price_per_day: float = Field(..., gt=0)
    status: DeskStatus


class Desk(DeskCreate):
    id: int


class BookingCreate(BaseModel):
    desk_id: int
    customer_name: str = Field(..., min_length=1)
    booking_date: date
    payment_status: PaymentStatus


class Booking(BookingCreate):
    id: int


desks: list[Desk] = [
    Desk(id=1, desk_number="DSK-A-01", zone="Zone A - Quiet Space", price_per_day=150000.0, status=DeskStatus.AVAILABLE),
    Desk(id=2, desk_number="DSK-B-02", zone="Zone B - Creative", price_per_day=200000.0, status=DeskStatus.AVAILABLE),
    Desk(id=3, desk_number="DSK-C-03", zone="Zone C - Panoramic", price_per_day=250000.0, status=DeskStatus.MAINTENANCE),
]

bookings: list[Booking] = [
    Booking(
        id=1,
        desk_id=1,
        customer_name="Nguyen Van A",
        booking_date=date(2026, 7, 1),
        payment_status=PaymentStatus.PAID,
    )
]


def generate_next_id(records: list) -> int:
    return max((r.id for r in records), default=0) + 1


def find_desk(desk_id: int) -> Optional[Desk]:
    return next((d for d in desks if d.id == desk_id), None)


def get_desk_or_404(desk_id: int) -> Desk:
    desk = find_desk(desk_id)
    if desk is None:
        raise HTTPException(status_code=404, detail="Desk not found")
    return desk


def is_desk_number_duplicate(desk_number: str, exclude_id: Optional[int] = None) -> bool:
    return any(
        d.desk_number.lower() == desk_number.lower() and d.id != exclude_id
        for d in desks
    )


@app.post("/desks", response_model=Desk, status_code=201)
def create_desk(payload: DeskCreate):
    if is_desk_number_duplicate(payload.desk_number):
        raise HTTPException(status_code=400, detail="Desk number already exists")

    desk = Desk(id=generate_next_id(desks), **payload.model_dump())
    desks.append(desk)
    return desk


@app.get("/desks", response_model=list[Desk])
def list_desks(
    zone_keyword: Optional[str] = Query(default=None),
    max_price: Optional[float] = Query(default=None, gt=0),
    status: Optional[DeskStatus] = Query(default=None),
):
    result = desks

    if zone_keyword:
        zone_keyword_lower = zone_keyword.lower()
        result = [d for d in result if zone_keyword_lower in d.zone.lower()]

    if max_price is not None:
        result = [d for d in result if d.price_per_day <= max_price]

    if status:
        result = [d for d in result if d.status == status]

    return result


@app.get("/desks/{desk_id}", response_model=Desk)
def get_desk(desk_id: int):
    return get_desk_or_404(desk_id)


@app.put("/desks/{desk_id}", response_model=Desk)
def update_desk(desk_id: int, payload: DeskUpdate):
    desk = get_desk_or_404(desk_id)

    if is_desk_number_duplicate(payload.desk_number, exclude_id=desk_id):
        raise HTTPException(status_code=400, detail="Desk number already exists")

    desk.desk_number = payload.desk_number
    desk.zone = payload.zone
    desk.price_per_day = payload.price_per_day
    desk.status = payload.status
    return desk


@app.delete("/desks/{desk_id}", status_code=204)
def delete_desk(desk_id: int):
    desk = get_desk_or_404(desk_id)
    desks.remove(desk)
    return None


@app.post("/bookings", response_model=Booking, status_code=201)
def create_booking(payload: BookingCreate):
    desk = find_desk(payload.desk_id)
    if desk is None:
        raise HTTPException(status_code=404, detail="Desk not found")

    if desk.status != DeskStatus.AVAILABLE:
        raise HTTPException(status_code=400, detail="Desk is not available for booking")

    is_overbooked = any(
        b.desk_id == payload.desk_id and b.booking_date == payload.booking_date
        for b in bookings
    )
    if is_overbooked:
        raise HTTPException(status_code=400, detail="This desk is already booked for the selected date")

    booking = Booking(id=generate_next_id(bookings), **payload.model_dump())
    bookings.append(booking)
    return booking


@app.get("/bookings", response_model=list[Booking])
def list_bookings():
    return bookings