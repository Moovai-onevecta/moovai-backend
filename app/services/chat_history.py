from __future__ import annotations

from datetime import UTC, datetime

from app.models.chat_history import ChatHistory, StoredChatAction, StoredChatMessage
from app.services.base import FirestoreService


class ChatHistoryService(FirestoreService[ChatHistory]):
    """Firestore-backed chat + suggested-action history, one document per
    itinerary, keyed by itinerary_id — not a generated id (see id_field
    docstring on FirestoreService), mirroring UsersService's uid-keyed
    pattern.
    """

    collection_name = "chat_histories"

    def get_for_itinerary(self, itinerary_id: str) -> ChatHistory | None:
        return self.get_model(itinerary_id, ChatHistory)

    def _get_or_create(self, itinerary_id: str, owner_uid: str) -> ChatHistory:
        existing = self.get_for_itinerary(itinerary_id)
        if existing is not None:
            return existing

        now = datetime.now(UTC)
        return ChatHistory(
            itinerary_id=itinerary_id,
            owner_uid=owner_uid,
            created_at=now,
            updated_at=now,
        )

    def append_messages(
        self, itinerary_id: str, owner_uid: str, messages: list[StoredChatMessage]
    ) -> ChatHistory:
        history = self._get_or_create(itinerary_id, owner_uid)
        updated = history.model_copy(
            update={
                "messages": [*history.messages, *messages],
                "updated_at": datetime.now(UTC),
            }
        )
        self.save_model(itinerary_id, updated)
        return updated

    def append_actions(
        self, itinerary_id: str, owner_uid: str, actions: list[StoredChatAction]
    ) -> ChatHistory:
        history = self._get_or_create(itinerary_id, owner_uid)
        updated = history.model_copy(
            update={
                "actions": [*history.actions, *actions],
                "updated_at": datetime.now(UTC),
            }
        )
        self.save_model(itinerary_id, updated)
        return updated

    def resolve_action(
        self, itinerary_id: str, action_id: str, accepted: bool
    ) -> ChatHistory | None:
        history = self.get_for_itinerary(itinerary_id)
        if history is None:
            return None

        now = datetime.now(UTC)
        resolved_actions = [
            action.model_copy(
                update={
                    "status": "approved" if accepted else "skipped",
                    "resolved_at": now,
                }
            )
            if action.action_id == action_id
            else action
            for action in history.actions
        ]
        updated = history.model_copy(
            update={"actions": resolved_actions, "updated_at": now}
        )
        self.save_model(itinerary_id, updated)
        return updated
