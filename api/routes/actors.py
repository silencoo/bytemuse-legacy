from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.routes import get_current_user
from app.api.services import iactor
from app.api.services.iactor import Subscribe
from app.common.reponse import ResponseEntity
from app.database.session import get_session

router = APIRouter()


@router.get("/actors")
def list_actors(session: Session = Depends(get_session),
                current_user: str = Depends(get_current_user)) -> ResponseEntity:
    return iactor.list(session)


@router.get("/actors/rank")
def rank(session: Session = Depends(get_session),
         current_user: str = Depends(get_current_user)) -> ResponseEntity:
    return iactor.rank(session)


@router.post("/actors/sub")
async def subscribe(sub_form: Subscribe, session: Session = Depends(get_session),
                    current_user: str = Depends(get_current_user)) -> ResponseEntity:
    return iactor.subscribe(sub_form, session)


@router.delete("/actors/cancel")
async def cancel(actor_name: str, session: Session = Depends(get_session),
                 current_user: str = Depends(get_current_user)) -> ResponseEntity:
    return iactor.cancel(actor_name, session)
