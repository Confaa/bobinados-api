from datetime import date as Date
from typing import Optional

from sqlalchemy import Column, ForeignKey
from sqlmodel import SQLModel, Field, Relationship


class Motor(SQLModel, table=True):
    __tablename__ = "motor"

    id: int | None = Field(default=None, primary_key=True)
    power: str | None = None
    phases: str | None = None
    rpm: int | None = None
    voltage: str | None = None
    nominal_current: float | None = None

    winding: Optional["Winding"] = Relationship(
        back_populates="motor", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    empty_test: Optional["EmptyTest"] = Relationship(
        back_populates="motor", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    chassis: Optional["Chassis"] = Relationship(
        back_populates="motor", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    general: Optional["General"] = Relationship(
        back_populates="motor", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class Winding(SQLModel, table=True):
    __tablename__ = "winding"

    motor_id: int = Field(
        sa_column=Column(
            ForeignKey("motor.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    connection: str
    material: str
    double_layer: bool
    coil_weight: float | None = None

    # Relaciones 1:muchos
    passes: Optional[list["WindingPass"]] = Relationship(
        back_populates="winding",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    wires: Optional[list["WindingWire"]] = Relationship(
        back_populates="winding",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    motor: Motor = Relationship(back_populates="winding")


class WindingPass(SQLModel, table=True):
    __tablename__ = "winding_pass"

    id: int | None = Field(default=None, primary_key=True)
    winding_motor_id: int = Field(
        sa_column=Column(
            ForeignKey("winding.motor_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    pass_length: int
    pass_turn: int

    winding: Winding = Relationship(back_populates="passes")


class WindingWire(SQLModel, table=True):
    __tablename__ = "winding_wire"

    id: int | None = Field(default=None, primary_key=True)
    winding_motor_id: int = Field(
        sa_column=Column(
            ForeignKey("winding.motor_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    wire_diameter: float
    wire_quantity: int

    winding: Winding = Relationship(back_populates="wires")


class General(SQLModel, table=True):
    __tablename__ = "general"

    motor_id: int = Field(
        sa_column=Column(
            ForeignKey("motor.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    owner: str | None = None
    date: Date = Field(default_factory=Date.today)
    brand: str | None = Field(default=None, index=True)
    serial_number: str | None = Field(default=None, index=True)
    description: str | None = None

    motor: Motor = Relationship(back_populates="general")


class Chassis(SQLModel, table=True):
    __tablename__ = "chassis"

    motor_id: int = Field(
        sa_column=Column(
            ForeignKey("motor.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    body: str | None = None
    slots: int | None = None
    plate_internal_diameter: float | None = None
    plate_external_diameter: float | None = None
    plate_length: float | None = None
    rear_bearing: str | None = None
    front_bearing: str | None = None

    motor: Motor = Relationship(back_populates="chassis")


class EmptyTest(SQLModel, table=True):
    __tablename__ = "empty_test"

    motor_id: int = Field(
        sa_column=Column(
            ForeignKey("motor.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    empty_current: float | None = None
    applied_tension: float | None = None

    motor: Motor = Relationship(back_populates="empty_test")
