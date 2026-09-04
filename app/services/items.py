from google.cloud.firestore import Client as FirestoreClient

from app.models.item import Item, ItemCreate

COLLECTION = "items"


class ItemsService:
    def __init__(self, db: FirestoreClient) -> None:
        self._db = db

    def create(self, owner_uid: str, payload: ItemCreate) -> Item:
        doc_ref = self._db.collection(COLLECTION).document()
        data = payload.model_dump()
        data["owner_uid"] = owner_uid
        doc_ref.set(data)
        return Item(id=doc_ref.id, owner_uid=owner_uid, **payload.model_dump())

    def list_for_owner(self, owner_uid: str) -> list[Item]:
        query = self._db.collection(COLLECTION).where("owner_uid", "==", owner_uid)
        return [Item(id=doc.id, **(doc.to_dict() or {})) for doc in query.stream()]

    def get(self, item_id: str) -> Item | None:
        doc = self._db.collection(COLLECTION).document(item_id).get()
        if not doc.exists:
            return None
        return Item(id=doc.id, **(doc.to_dict() or {}))
