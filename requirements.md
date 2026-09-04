# Backend Requirements

Functional requirements for the MoovAI backend. This is a living document — update it as
scope is confirmed; treat anything below marked **TBD** as an open question, not a decision.

## 1. Purpose

MoovAI lets travelers plan itineraries (destinations + flights), invite friends to
collaborate on a trip, and book services — tour guides and transport — from local
providers. Service providers get their own login to manage the cities they cover and
respond to incoming requests. Payments for booked services run through WeWire.

The backend is a typed Python API sitting between the client app(s) and Firebase, and it
brokers AI features through a hosted LLM API. It does not host or run any models itself —
all AI inference is delegated to a third-party API (currently Anthropic).

## 2. Core infrastructure

- **Platform**: Firebase (Firestore + Firebase Authentication) as the system of record.
- **API layer**: FastAPI, async, typed end-to-end with Pydantic v2 models.
- **Type safety**: `mypy --strict` must pass with no errors; no untyped function bodies.
- **Deployment target**: containerized, expected to run on Cloud Run or similar, using
  Application Default Credentials in production (service-account key file only for local
  dev). **TBD**: confirm actual hosting target.

## 3. Authentication and account types

- Clients authenticate with Firebase Auth (email/password, OAuth providers, etc. — handled
  client-side).
- The backend never handles passwords or credentials directly.
- Every protected endpoint requires `Authorization: Bearer <Firebase ID token>`.
- The backend verifies the ID token via `firebase_admin.auth.verify_id_token` and derives
  the caller's identity (`uid`, `email`, custom claims) from it.
- Two distinct account types share the same Firebase Auth pool but have different
  capabilities, enforced via a custom claim / role field set on the user's profile doc:
  - **Traveler** — creates and joins itineraries, books services.
  - **Service provider** — manages a profile (cities served, service type), views and
    responds to incoming booking requests. Sub-types: **tour guide**, **transport
    provider**. **TBD**: can one account be both a traveler and a provider, or are these
    mutually exclusive signups?
- **TBD**: is there an admin/staff role (e.g. to vet/approve service providers before they
  go live)?

## 4. Itineraries

- A traveler creates an **itinerary**: a named trip with a date range.
- An itinerary contains:
  - **Destinations** — ordered list of cities/places, each with arrival/departure dates.
  - **Flights** — flight segments (carrier, flight number, departure/arrival airports and
    times) attached to the itinerary. **TBD**: manually entered by the user, or looked up
    via a flight-data API? If looked up, that's another external API integration alongside
    WeWire and the AI provider.
- **Collaboration / invites**:
  - The itinerary owner can invite friends by email (or in-app username/uid lookup —
    **TBD**) to join the itinerary.
  - Invited friends who accept become **collaborators** and can view (and, **TBD**, edit)
    the shared itinerary — destinations, flights, and bookings.
  - **TBD**: permission model for collaborators — read-only vs. can add/edit destinations,
    flights, and bookings themselves.
  - **TBD**: invite delivery mechanism (email link, push notification, in-app only) and
    whether an invitee needs an existing MoovAI account first.

## 5. Service provider marketplace

- Service providers (tour guides, transport providers) register the **cities they offer
  services in** as part of their profile.
- Travelers request a service (e.g. "tour guide in Lisbon for these dates") tied to a
  destination on their itinerary; the request should be **visible only to providers who
  cover that city**.
- Providers log in to a view scoped to their own coverage area, showing incoming requests
  for their cities, and can accept/decline/respond to a request.
- **TBD**: request lifecycle and states — e.g. `pending` → `offered` (provider proposes
  terms/price) → `accepted` → `confirmed` (post-payment) → `completed` / `cancelled`. Needs
  to be nailed down before modeling this in Firestore.
- **TBD**: does a traveler request a specific provider, or broadcast to all providers in a
  city and pick from responses (marketplace-style)?
- **TBD**: provider vetting/verification before they can appear to travelers.

## 6. Payments (WeWire)

- Booked services (tour guide, transport) are paid for through **WeWire**, a third-party
  payment API. The backend never stores raw card/bank details — WeWire handles that, same
  pattern as AI: the backend calls WeWire's hosted API, it doesn't process payments itself.
- **TBD** (blocking — need WeWire's docs/API keys before this can be implemented):
  - Auth model for WeWire's API (API key, OAuth, webhook signing secret for callbacks).
  - Payment flow: does WeWire host a checkout page/widget, or does it expose a
    charge-a-payment-method API the backend calls directly?
  - Who is paid — does WeWire support marketplace-style split payouts to individual
    providers, or does MoovAI need to hold funds and payout providers separately?
  - Refunds/cancellations, and how they map to the booking-request lifecycle above.
  - Currency handling if travelers and providers are in different countries.

## 7. Data model (Firestore)

- Firestore is the primary datastore; no relational database is planned.
- Data access goes through a service layer (`app/services/`), not directly from route
  handlers, so query logic and Firestore-specific quirks (e.g. `snake_case` vs. `camelCase`
  field naming, `None` handling on `to_dict()`) stay in one place.
- Anticipated top-level collections (**TBD**, pending answers above): `users` (traveler +
  provider profiles, role, provider cities/service type), `itineraries` (with
  `destinations` and `flights` as subcollections or embedded arrays — **TBD** which, based
  on expected size and query patterns), `itinerary_invites` (or an `invites` subcollection
  per itinerary), `service_requests` (queryable by city and provider), `payments`/`bookings`
  linking a `service_request` to a WeWire transaction.
- Ownership/access rule generalizes beyond single-owner: an itinerary is readable/writable
  by its owner *and* its accepted collaborators, not just `owner_uid`.
- **TBD**: Firestore security rules — even though the backend enforces access control, if
  any client ever talks to Firestore directly, rules need to mirror this logic.

## 8. AI integration

- AI features are implemented by calling a hosted LLM API (Anthropic's Messages API) over
  HTTPS from the backend — never client-side, so the API key stays server-only.
- Requests/responses are validated with typed Pydantic models (`ChatRequest`/`ChatResponse`).
- AI endpoints require authentication like any other protected route.
- **TBD**:
  - Should AI conversations be persisted to Firestore (chat history per user)?
  - Streaming responses (SSE/WebSocket) vs. request/response only?
  - Rate limiting / usage caps per user to control API cost?
  - Multiple providers/models, or Anthropic only?

## 9. Non-functional requirements

- **Type safety**: all new code must be fully typed; CI (once set up) should run `mypy`,
  `ruff`, and `pytest` on every change.
- **Config**: all secrets/config via environment variables (`pydantic-settings`), never
  hardcoded. `.env` is git-ignored; `.env.example` documents required variables. This will
  grow to include WeWire credentials and, if adopted, a flight-data API key.
- **CORS**: restricted to configured allowed origins (`CORS_ORIGINS` env var).
- **Testing**: unit tests for services and routes; `TestClient` for API-level tests.

## 10. Open product questions (need input before building further)

Roughly in the order they'd block implementation:

1. WeWire's API docs/credentials, and the payment-flow/payout questions in §6 — payments
   can't be built at all until this is answered.
2. Service request lifecycle and whether requests are targeted-provider or broadcast (§5).
3. Collaborator permission model for shared itineraries (§4).
4. Flights: manual entry vs. flight-data API lookup (§4).
5. Traveler vs. provider account exclusivity, and whether an admin/vetting role exists (§3).
6. Any file/media upload needs (e.g. provider photos, ID verification) — would imply
   Firebase Storage.
7. Any background/scheduled jobs (e.g. reminders before a trip, expiring stale requests) —
   would imply Cloud Functions or Cloud Tasks alongside this API.
8. Specific AI use cases beyond a generic chat endpoint — e.g. itinerary suggestions,
   auto-drafting a trip from a prompt, matching travelers to providers.
