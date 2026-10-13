from fastapi import APIRouter, Depends

from app.deps import get_store, get_user
from app.schemas import VehicleIn, VehicleOut, VehiclePatchIn
from app.serializers import vehicle_out
from app.services import vehicle_service
from app.store import Store, User

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("", response_model=list[VehicleOut])
def list_vehicles(user: User = Depends(get_user), store: Store = Depends(get_store)):
    return [vehicle_out(v) for v in vehicle_service.list_vehicles(store, user)]


@router.post("", response_model=VehicleOut, status_code=201)
def create_vehicle(
    body: VehicleIn, user: User = Depends(get_user), store: Store = Depends(get_store)
):
    return vehicle_out(vehicle_service.create_vehicle(store, user, body.model_dump()))


@router.patch("/{vehicle_id}", response_model=VehicleOut)
def update_vehicle(
    vehicle_id: str,
    body: VehiclePatchIn,
    user: User = Depends(get_user),
    store: Store = Depends(get_store),
):
    return vehicle_out(
        vehicle_service.update_vehicle(
            store, user, vehicle_id, body.model_dump(exclude_unset=True)
        )
    )


@router.delete("/{vehicle_id}")
def delete_vehicle(
    vehicle_id: str, user: User = Depends(get_user), store: Store = Depends(get_store)
):
    vehicle_service.delete_vehicle(store, user, vehicle_id)
    return {}
