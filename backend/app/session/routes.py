from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from app.session.service import LeaveRejected

router = APIRouter(prefix="/api")


class JoinRequest(BaseModel):
    seat_token: str | None = None


class LeaveRequest(BaseModel):
    seat_token: str


@router.post("/join")
async def join(body: JoinRequest, request: Request) -> dict:
    seat = await request.app.state.seats.join(body.seat_token)
    return {"seat_token": seat.seat_token, "phase": seat.phase}


@router.post("/leave", status_code=204)
async def leave(body: LeaveRequest, request: Request) -> Response:
    try:
        await request.app.state.seats.leave(body.seat_token)
    except LeaveRejected:
        raise HTTPException(status_code=409, detail="The run has already started")
    return Response(status_code=204)
