from fastapi import APIRouter, Depends, HTTPException, status

from app.deps.auth import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("/{service_request_id}/pay", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def pay_for_booking(
    service_request_id: str,
    _user: AuthenticatedUser = Depends(get_current_user),
) -> None:
    """Charge an accepted service request through WeWire.

    Reserves the shape of the payments surface. Not implemented: WeWire's auth model,
    checkout flow, and payout semantics are all open (see requirements.md §6) — nothing
    here should be built out until that's answered.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Payments are not yet implemented — pending WeWire integration "
            "(requirements.md §6)"
        ),
    )
