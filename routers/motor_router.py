from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlmodel import Session

from core.database import get_session
from schemas.motor_schema import MotorRequest, MotorResponse
from services.motor_service import MotorService


router = APIRouter(prefix="/motors")


@router.get(
    "",
    response_model=list[MotorResponse],
    status_code=status.HTTP_200_OK,
    summary="List Motors",
)
def get_motors(
    db: Session = Depends(get_session),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
):
    return MotorService.get_all(db, offset, limit)


@router.post(
    "",
    response_model=MotorResponse, # Cambiado a Response para devolver ID creado
    status_code=status.HTTP_201_CREATED,
    summary="Add Motor",
)
def add_motor(
    data: MotorRequest,
    db: Session = Depends(get_session),
):
    return MotorService.add(db, data)


@router.put(
    "/{motor_id}",
    response_model=MotorResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Motor",
)
def update_motor(
    motor_id: int,
    data: MotorRequest,
    db: Session = Depends(get_session),
):
    updated_motor = MotorService.update(db, motor_id, data)
    if not updated_motor:
        raise HTTPException(status_code=404, detail="Motor not found")
    return updated_motor

@router.delete(
    "/{motor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Motor",
)
def delete_motor(
    motor_id: int,
    db: Session = Depends(get_session),
):
    deleted = MotorService.delete(db, motor_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Motor with ID {motor_id} not found"
        )
    
    return None