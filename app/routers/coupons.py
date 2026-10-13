from fastapi import APIRouter

router = APIRouter(prefix="/coupons", tags=["Coupons"])


@router.post("/validate")
def validate_coupon():
    return True
