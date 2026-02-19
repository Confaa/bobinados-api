from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from models.motor_model import Motor, Winding, WindingPass, WindingWire, General, Chassis, EmptyTest, EmptyTest
from schemas.motor_schema import MotorRequest

class MotorRepository:
    @staticmethod
    def get_all(db: Session, offset: int = 0, limit: int = 100):
        statement = (
            select(Motor)
            .options(
                selectinload(Motor.general),
                selectinload(Motor.chassis),
                selectinload(Motor.empty_test),
                selectinload(Motor.winding),
            )
            .order_by(Motor.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return db.exec(statement).all()

    @staticmethod
    def add(db: Session, motor: Motor):
        db.add(motor)
        return motor

    @staticmethod
    def get_by_id(db: Session, motor_id: int):
        statement = (
            select(Motor)
            .where(Motor.id == motor_id)
            .options(
                selectinload(Motor.general),
                selectinload(Motor.chassis),
                selectinload(Motor.empty_test),
                selectinload(Motor.winding).selectinload(Winding.passes),
                selectinload(Motor.winding).selectinload(Winding.wires),
            )
        )
        return db.exec(statement).first()

    @staticmethod
    def update(db: Session, motor_id: int, data: MotorRequest):
        # 1. Traemos el motor (Esto inicia implícitamente la transacción)
        motor = MotorRepository.get_by_id(db, motor_id)
        if not motor:
            return None
        
        # 2. Modificamos los datos sobre el objeto traído
        # Datos Base
        motor.power = data.power
        motor.phases = str(data.phases) # Asegurar string si viene int
        motor.rpm = data.rpm
        motor.voltage = data.voltage
        motor.nominal_current = data.nominal_current
        
        # General
        if data.general and motor.general:
            motor.general.owner = data.general.owner
            motor.general.brand = data.general.brand
            motor.general.serial_number = data.general.serial_number
            motor.general.description = data.general.description
            if data.general.date:
                motor.general.date = data.general.date

        # Chassis
        if data.chassis and motor.chassis:
            c_data = data.chassis.model_dump(exclude_none=True)
            for k, v in c_data.items():
                setattr(motor.chassis, k, v)

        # Bobinado (Complejo: Limpiar y rellenar listas)
        if data.winding and motor.winding:
            w = motor.winding
            w.connection = data.winding.connection
            w.material = data.winding.material
            w.double_layer = data.winding.double_layer
            w.coil_weight = data.winding.coil_weight
            
            # Actualizar Pasos
            w.passes.clear() # Borra los viejos de la DB al commitear
            for p in data.winding.passes:
                w.passes.append(WindingPass(pass_length=p.pass_length, pass_turn=p.pass_turn))
            
            # Actualizar Alambres
            w.wires.clear()
            for wire in data.winding.wires:
                w.wires.append(WindingWire(wire_diameter=wire.wire_diameter, wire_quantity=wire.wire_quantity))

        # Test Vacío
        if data.empty_test:
            if motor.empty_test:
                motor.empty_test.empty_current = data.empty_test.empty_current
                motor.empty_test.applied_tension = data.empty_test.applied_tension
            else:
                motor.empty_test = EmptyTest(**data.empty_test.model_dump())

        # 3. Guardamos cambios
        db.add(motor)
        db.commit() # Confirmamos la transacción
        db.refresh(motor) # Recargamos datos frescos
        return motor
    
    @staticmethod
    def delete(db: Session, motor_id: int) -> bool:
        # 1. Buscamos el motor
        motor = db.get(Motor, motor_id)
        
        # 2. Si no existe, retornamos False
        if not motor:
            return False
        
        # 3. Borramos y confirmamos (las relaciones se borran por CASCADE configurado en el modelo)
        db.delete(motor)
        db.commit()
        return True