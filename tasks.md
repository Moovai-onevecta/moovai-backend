Here's a 30-task build plan, grouped into phases so foundational work isn't blocked by the open product questions in §10. Where a task touches a TBD, I've flagged it — build the scaffolding now, swap in the real decision later without much rework.

**Phase 1 — Foundation & infra (1–6)**
1. Lock deployment target (Cloud Run vs. alternative) and finish the Dockerfile + container config.
2. Implement `core/firebase.py` — Firebase Admin SDK init, ADC in prod, service-account key fallback for local dev.
3. Implement `core/config.py` with `pydantic-settings`; fill out `.env.example` (Firebase project, Anthropic key placeholders).
4. Stand up CI: `mypy --strict`, `ruff`, `pytest` on every push.
5. Build `deps/auth.py` — verify `Authorization: Bearer <Firebase ID token>` via `verify_id_token`, expose `uid`/`email`/claims to routes.
6. Define the role/claim scheme for traveler vs. provider on the user profile doc (build as non-exclusive by default; flag for revisit once §3's exclusivity question is answered).

**Phase 2 — Data models & service layer (7–10)**
7. Pydantic models for `User`/`Profile` (traveler + provider fields, role).
8. Pydantic models for `Itinerary`, `Destination`, `Flight`.
9. Build the `app/services/` CRUD abstraction pattern (one place for Firestore access, per §7).
10. Firestore helper layer for `camelCase`↔`snake_case` translation and `None`-safe `to_dict()` handling.

**Phase 3 — Itineraries & collaboration (11–15)**
11. Itinerary CRUD endpoints (create/read/update/delete, owner-scoped).
12. Destinations sub-resource endpoints.
13. Flights sub-resource — manual entry only for MVP (flight-data API integration deferred per §4 TBD).
14. Invite flow — invite by email, accept endpoint (default to read-only collaborator access until the permission model in §4 is decided).
15. Access-control dependency enforcing owner-or-accepted-collaborator on itinerary reads/writes.

**Phase 4 — Service provider marketplace (16–20)**
16. Provider profile model + registration endpoints (cities served, service type).
17. Provider visibility stub — ship as auto-live, with a hook point for vetting/approval once §3's admin-role question is settled.
18. `ServiceRequest` model with a minimal lifecycle (`pending`/`accepted`/`declined`) that can be extended once §5's full state machine is confirmed.
19. Request-creation endpoint, queryable/filterable by city.
20. Provider-facing endpoints to list and respond to incoming requests scoped to their coverage cities.

**Phase 5 — Payments (21–23, mostly schema-only until WeWire access lands)**
21. `Payment`/`Booking` Pydantic models and Firestore collection linking `service_request` → transaction, no live calls yet.
22. `WeWireClient` interface with a mocked implementation, so the payment step in the booking flow can be tested end-to-end before real credentials arrive.
23. Webhook route stub for payment confirmation/refund callbacks (signature verification logic pending WeWire docs).

**Phase 6 — AI integration (24–26)**
24. `app/services/ai.py` — server-side calls to Anthropic's Messages API using `ChatRequest`/`ChatResponse` models.
25. `app/api/routes` AI endpoint, authenticated like any other protected route.
26. Add per-user rate limiting/usage caps; decide and implement (or explicitly skip) chat-history persistence to Firestore.

**Phase 7 — Testing, security, polish (27–30)**
27. Unit tests for each service module (auth, itineraries, service requests, AI).
28. API-level tests with `TestClient` covering the full route set, including permission edge cases.
29. Draft Firestore security rules mirroring the backend's access logic, for defense-in-depth.
30. Finalize README, API docs, and `.env.example` with every required variable (Firebase, Anthropic, WeWire once known).

A few notes on sequencing: Phases 1–4 and 6 can proceed in parallel with the open questions in §10 — I've defaulted each blocked decision to the simplest reasonable MVP behavior so you're not stalled. Payments (Phase 5) is the one area where I'd genuinely hold off on real implementation until WeWire's docs are in hand, since the auth model and payout structure change the data model, not just the endpoint logic.

Want me to turn any of these phases into detailed sub-tickets (endpoints, request/response schemas, Firestore collection shapes) next?