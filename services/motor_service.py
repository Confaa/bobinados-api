from sqlmodel import Session
from models.motor_model import Chassis, EmptyTest, General, Motor, Winding, WindingPass, WindingWire
from repositories.motor_repository import MotorRepository
from schemas.motor_schema import MotorRequest


class MotorService:
    @staticmethod
    def get_all(db: Session, offset: int = 0, limit: int = 100) -> list[Motor]:
        return MotorRepository.get_all(db, offset, limit)

    @staticmethod
    def add(db: Session, data: MotorRequest):
        # Lógica de creación transaccional
        with db.begin():
            # Ajuste de marca si viene en general
            brand_val = data.general.brand if data.general else "Sin Marca"
            
            motor = Motor(
                power=data.power,
                phases=str(data.phases),
                rpm=data.rpm,
                voltage=data.voltage,
                nominal_current=data.nominal_current,
                brand=brand_val # Importante si tu modelo Motor tiene brand
            )
            MotorRepository.add(db, motor)
            db.flush()

            if data.general:
                # Excluimos brand del dict general si ya lo usamos en Motor
                gen_data = data.general.model_dump(exclude_none=True)
                if "brand" in gen_data and hasattr(Motor, "brand"): 
                    pass # O lo quitamos con del gen_data['brand'] si la tabla General no lo tiene
                db.add(General(motor_id=motor.id, **gen_data))
            
            if data.chassis:
                db.add(Chassis(motor_id=motor.id, **data.chassis.model_dump(exclude_none=True)))
            
            if data.empty_test:
                db.add(EmptyTest(motor_id=motor.id, **data.empty_test.model_dump(exclude_none=True)))
                
            if data.winding:
                db.add(Winding(
                    motor_id=motor.id,
                    connection=data.winding.connection,
                    material=data.winding.material,
                    double_layer=data.winding.double_layer,
                    coil_weight=data.winding.coil_weight,
                ))
                if data.winding.passes:
                    db.add_all([
                        WindingPass(winding_motor_id=motor.id, pass_length=p.pass_length, pass_turn=p.pass_turn)
                        for p in data.winding.passes
                    ])
                if data.winding.wires:
                    db.add_all([
                        WindingWire(winding_motor_id=motor.id, wire_diameter=w.wire_diameter, wire_quantity=w.wire_quantity)
                        for w in data.winding.wires
                    ])

        # Retornar objeto completo con relaciones
        return MotorRepository.get_by_id(db, motor.id)

    @staticmethod
    def update(db: Session, motor_id: int, data: MotorRequest):
        return MotorRepository.update(db, motor_id, data)
    
    @staticmethod
    def delete(db: Session, motor_id: int) -> bool:
        return MotorRepository.delete(db, motor_id)