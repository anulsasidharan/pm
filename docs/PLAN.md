# Project Plan: Project Management MVP

## Scope and Constraints

- MVP includes hardcoded login credentials: `user` / `password`
- One board per user for MVP, but schema should remain future-ready for multiple users
- Backend: FastAPI (Python)
- Frontend: Next.js (existing frontend demo is source of UI behavior)
- Runtime: local Docker container
- AI provider: OpenRouter with model `openai/gpt-oss-120b`
- Database: SQLite (created automatically if missing)

## Part 1 Execution Status

Current status: Complete (approved on 2026-03-09)

Progress update: Parts 1-10 complete (Part 5 approved on 2026-03-11, Part 6 completed on 2026-03-11, Part 7 completed on 2026-03-11, Part 8 completed on 2026-03-12, Part 9 completed on 2026-03-12, Part 10 completed on 2026-03-12)

Approved decisions:

- App port in Docker/local runtime: `8000`
- SQLite storage location: bind mount `./data/app.db`
- Session mechanism for MVP auth: signed HTTP-only cookie
- Session timeout: `24 hours`
- Conversation history window sent to AI: last `20` messages
- API style: REST under `/api/*`
- Test stack:
- Backend unit/integration: `pytest` + FastAPI test client
- Frontend unit: `vitest` + React Testing Library
- Frontend integration/e2e: `playwright`

## Quality Gates (Applies to All Parts)

- Unit test coverage target is **~80% when sensible**, prioritizing valuable tests over coverage-only tests
- Integration tests must cover all major user flows end-to-end and API/UI interactions
- No phase is marked complete until tests pass and phase success criteria are met
- Keep implementation simple and focused on MVP requirements only

## Part 1: Planning and Alignment

### Checklist

- [x] Confirm plan scope and sequence with user
- [x] Confirm final choices where unspecified (ports, cookie/session details, history window)
- [x] Confirm acceptance of quality gates and testing thresholds
- [x] Confirm frontend AGENTS documentation exists and is accurate

### Tests

- [x] Plan reviewed for completeness against AGENTS requirements
- [x] Each later part has implementation, tests, and success criteria sections

### Success Criteria

- [x] User explicitly approves this plan before implementation starts
- [x] No unresolved blockers for Parts 2-10

## Part 2: Scaffolding (Docker + FastAPI + Scripts)

### Checklist

- [x] Create backend FastAPI app scaffold in `backend/`
- [x] Add route `/api/health` returning healthy status
- [x] Add temporary root route serving hello-world HTML
- [x] Add Dockerfile and runtime command for FastAPI app
- [x] Add docker-compose configuration for local run
- [x] Add start/stop scripts for Windows, macOS, Linux in `scripts/`
- [x] Ensure `.env` is wired for runtime config

### Tests

- [x] Backend unit tests for health endpoint and app startup
- [x] Integration test that container starts and serves `/` + `/api/health`
- [x] Script smoke tests for start and stop on each OS script path

### Success Criteria

- [x] `docker compose up` brings app up successfully
- [x] `GET /` returns expected hello page
- [x] `GET /api/health` returns success JSON

## Part 3: Serve Existing Frontend

### Checklist

- [x] Integrate existing Next.js frontend build output into backend serving flow
- [x] Replace hello-world root with built frontend app at `/`
- [x] Ensure static assets are correctly served in Docker
- [x] Keep API namespace under `/api/*`

### Tests

- [x] Frontend unit tests for board render and core component logic
- [x] Integration test verifies `/` loads Kanban board in container
- [x] Integration test verifies frontend + API coexist without route collisions

### Success Criteria

- [x] Kanban board demo appears at `/`
- [x] API endpoints still reachable and unaffected
- [x] Unit coverage remains >= 80%

## Part 4: Fake Sign-In / Sign-Out Flow

### Checklist

- [x] Add login page/view gate before Kanban access
- [x] Validate hardcoded credentials (`user` / `password`)
- [x] Add sign-out control that clears authenticated session
- [x] Ensure unauthenticated access to `/` redirects or shows login view

### Tests

- [x] Frontend unit tests for login form validation and state transitions
- [x] Backend/session unit tests for auth guard behavior (if server session used)
- [x] Integration tests: login success, login failure, logout, blocked unauthenticated access

### Success Criteria

- [x] Only authenticated users can view Kanban board
- [x] Logout returns user to login experience
- [x] Unit coverage remains >= 80%

## Part 5: Database Modeling and Sign-Off

### Checklist

- [x] Define SQLite schema for users and board state storage
- [x] Store board as JSON payload per user (MVP requirement)
- [x] Define migration/init strategy for auto-create when DB missing
- [x] Document schema and rationale in `docs/`
- [x] Request and capture user sign-off before API persistence work

### Tests

- [x] Unit tests for DB initialization and schema creation
- [x] Unit tests for basic read/write board JSON operations

### Success Criteria

- [x] Schema document approved by user
- [x] DB can initialize from empty state automatically

## Part 6: Backend API for Kanban Persistence

### Checklist

- [x] Implement API routes to fetch board for authenticated user
- [x] Implement API routes to update board for authenticated user
- [x] Add input validation and error handling for malformed board data
- [x] Ensure DB auto-creation on first run

### Tests

- [x] Backend unit tests for service layer and validation
- [x] API tests for happy path and validation failures
- [x] Integration tests for auth + persistence behavior

### Success Criteria

- [x] Board changes persist across app restarts
- [x] Invalid payloads return clear 4xx errors
- [x] Unit coverage remains meaningful for changed behavior (target ~80% when sensible)

## Part 7: Frontend + Backend Integration

### Checklist

- [x] Replace frontend in-memory state with backend-backed state fetch/save
- [x] Add loading and error handling for board read/write operations
- [x] Ensure drag/drop and edits trigger persistence updates
- [x] Keep UX responsive and avoid data loss on rapid edits

### Tests

- [x] Frontend unit tests for API client and state update logic
- [x] Integration tests for create/edit/move card flows with backend persistence
- [x] Integration tests for refresh/reload retaining latest board state

### Success Criteria

- [x] UI operations persist reliably to backend
- [x] Reload reflects latest saved board state
- [x] Unit coverage remains meaningful for changed behavior (target ~80% when sensible)

## Part 8: AI Connectivity (OpenRouter)

### Checklist

- [x] Add backend AI client using `OPENROUTER_API_KEY` from `.env`
- [x] Configure model `openai/gpt-oss-120b`
- [x] Add backend endpoint to run connectivity check prompt
- [x] Implement retry/timeouts with simple MVP-safe behavior

### Tests

- [x] Unit tests for AI client request construction and error mapping
- [x] Integration smoke test for AI endpoint with prompt `2+2`
- [x] Integration test for missing/invalid API key behavior

### Success Criteria

- [x] AI endpoint returns valid response for connectivity prompt
- [x] Errors are actionable and do not crash the app
- [x] Unit coverage remains meaningful for changed behavior (target ~80% when sensible)

## Part 9: Structured AI Board Operations

### Checklist

- [x] Define structured response schema:
- [x] Include assistant reply text
- [x] Include optional board update payload
- [x] Include structured operation type metadata
- [x] Send board JSON + user message + conversation history to model
- [x] Validate model response against schema before applying updates
- [x] Apply board updates atomically when present

### Tests

- [x] Unit tests for schema validation and parse failures
- [x] Unit tests for board mutation application logic
- [x] Integration tests for chat-only and chat+board-update responses
- [x] Integration tests for malformed model output fallback behavior

### Success Criteria

- [x] AI can respond without board changes
- [x] AI can return valid board updates that persist
- [x] Invalid model outputs are handled safely
- [x] Unit coverage remains meaningful for changed behavior (target ~80% when sensible)

## Part 10: AI Sidebar UX in Frontend

### Checklist

- [x] Build sidebar chat UI integrated into Kanban view
- [x] Show message history and request state (loading/error)
- [x] Call backend AI endpoint with current board context
- [x] Apply returned board updates to UI state and persist them
- [x] Refresh or reconcile board state after AI mutation

### Tests

- [x] Frontend unit tests for chat state reducer/store and render logic
- [x] Integration tests for user message -> AI response rendering
- [x] Integration tests for AI-triggered board update reflected in Kanban UI
- [x] Integration tests for error and retry behavior

### Success Criteria

- [x] Sidebar enables reliable chat with AI assistant
- [x] AI-updated board state appears automatically in UI
- [x] Unit coverage remains meaningful for changed behavior (target ~80% when sensible)

## Test Strategy Detail

### Unit Tests

- Backend: `pytest` with coverage for route handlers, services, DB, and AI client wrappers
- Frontend: `vitest` + React Testing Library for component/state logic
- Coverage target: aim for ~80% when sensible; do not add low-value tests only to hit a number

### Integration Tests

- API integration tests using FastAPI test client and real SQLite test DB
- Frontend integration tests using Playwright (or equivalent) against running app
- Container-level smoke tests for startup, root page, auth flow, Kanban operations, AI flow

## Definition of Done (Per Phase)

- [ ] Implementation complete for phase scope
- [ ] Unit tests passing with meaningful coverage for changed behavior (target ~80% when sensible)
- [ ] Integration tests for phase flow passing
- [ ] Documentation updated where relevant
- [ ] User review checkpoint completed for major milestones