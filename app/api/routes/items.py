from fastapi import APIRouter, Depends, HTTPException, status

from app.deps.auth import CurrentUser, get_current_user
from app.deps.services import get_items_service
from app.models.item import Item, ItemCreate
from app.services.items import ItemsService

router = APIRouter(prefix="/items", tags=["items"])


@router.post("", response_model=Item, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: ItemCreate,
    user: CurrentUser = Depends(get_current_user),
    items: ItemsService = Depends(get_items_service),
) -> Item:
    return items.create(owner_uid=user.uid, payload=payload)


@router.get("", response_model=list[Item])
def list_items(
    user: CurrentUser = Depends(get_current_user),
    items: ItemsService = Depends(get_items_service),
) -> list[Item]:
    return items.list_for_owner(owner_uid=user.uid)


@router.get("/{item_id}", response_model=Item)
def get_item(
    item_id: str,
    user: CurrentUser = Depends(get_current_user),
    items: ItemsService = Depends(get_items_service),
) -> Item:
    item = items.get(item_id)
    if item is None or item.owner_uid != user.uid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item
