from __future__ import annotations

from datetime import date as Date
from sqlmodel import SQLModel


# -------------------------
# REQUEST (POST/PUT BODY)
# -------------------------
class WindingPassRequest(SQLModel):
    pass_length: int
    pass_turn: int


class WindingWireRequest(SQLModel):
    wire_diameter: float
    wire_quantity: int


class WindingRequest(SQLModel):
    connection: str 
    material: str
    double_layer: bool
    coil_weight: float| None = None

    passes: list[WindingPassRequest] = []
    wires: list[WindingWireRequest] = []


class GeneralRequest(SQLModel):
    owner: str| None = None
    date: Date
    brand: str| None = None
    description: str| None = None
    serial_number: str| None = None


class ChassisRequest(SQLModel):
    body: str| None = None
    slots: int| None = None
    plate_internal_diameter: float| None = None
    plate_external_diameter: float| None = None
    plate_length: float| None = None
    rear_bearing: str| None = None
    front_bearing: str| None = None


class EmptyTestRequest(SQLModel):
    empty_current: float| None = None
    applied_tension: float| None = None


class MotorRequest(SQLModel):
    power: str| None = None
    phases: int| None = None
    rpm: int| None = None
    voltage: str| None = None
    nominal_current: float| None = None

    winding: WindingRequest | None = None
    empty_test: EmptyTestRequest | None = None
    chassis: ChassisRequest | None = None
    general: GeneralRequest | None = None


# -------------------------
# RESPONSE (GET/POST OUTPUT)
# -------------------------
class WindingPassResponse(SQLModel):
    id: int
    winding_motor_id: int
    pass_length: int| None = None
    pass_turn: int| None = None


class WindingWireResponse(SQLModel):
    id: int
    winding_motor_id: int
    wire_diameter: float| None = None
    wire_quantity: int| None = None


class WindingResponse(SQLModel):
    motor_id: int
    connection: str
    material: str
    double_layer: bool
    coil_weight: float| None = None

    passes: list[WindingPassResponse] = []
    wires: list[WindingWireResponse] = []


class GeneralResponse(SQLModel):
    motor_id: int
    owner: str| None = None
    brand: str| None = None
    date: Date
    description: str| None = None
    serial_number: str| None = None


class ChassisResponse(SQLModel):
    motor_id: int
    body: str| None = None
    slots: int| None = None
    plate_internal_diameter: float| None = None
    plate_external_diameter: float| None = None
    plate_length: float| None = None
    rear_bearing: str| None = None
    front_bearing: str| None = None


class EmptyTestResponse(SQLModel):
    motor_id: int
    empty_current: float| None = None
    applied_tension: float| None = None


class MotorResponse(SQLModel):
    id: int
    power: str| None = None
    phases: str| None = None
    rpm: int| None = None
    voltage: str| None = None
    nominal_current: float| None = None

    winding: WindingResponse | None = None
    empty_test: EmptyTestResponse | None = None
    chassis: ChassisResponse | None = None
    general: GeneralResponse | None = None
