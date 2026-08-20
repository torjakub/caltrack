# Sync protocol

*Status: draft — implemented in milestone M4. This document describes the design; update it if the implementation diverges.*

The mobile app is offline-first: it keeps its own local database and can create, edit, and delete records with no connectivity. Syncing reconciles that local state with the server whenever the server is reachable.

## Design goals

- Work correctly for the common case (one person, a couple of devices, rarely editing the same record on two devices before syncing) without building a full CRDT/auto-merge system.
- Never silently discard a conflicting edit. When both sides changed the same record since the last sync, surface it to the user — mine vs. theirs — rather than guessing.
- Keep the server the durable source of truth once synced; the mobile app's local database is authoritative only until it talks to the server again.

## Mechanism

Every syncable table (`user_profile`, `user_targets`, `foods`, `food_nutrients`, `food_micronutrients`, `recipes`/`recipe_items`, `log_entries`) has:
- a client-generated UUID primary key (so records can be created offline before the server has ever seen them),
- an `updated_at` timestamp,
- a soft-delete `deleted_at` tombstone (deletes sync like any other change).

Each device tracks a single `since` checkpoint — the server timestamp of its last successful sync.

On `POST /api/v1/sync`, for each incoming record:

1. **No existing server row** → apply as an insert.
2. **Existing row, `server_row.updated_at <= since`** → apply as an update/delete. The device's last known state was current when it made this change.
3. **Existing row, `server_row.updated_at > since`** → **conflict**. The server row changed after this device last synced, so some other device changed it — don't apply, return both versions instead.

The whole batch applies in one transaction; a failed sync leaves the device's `since` unchanged, so a retry safely resends the same (idempotent) batch.

## Conflict resolution

Conflicts come back as `{entity_type, id, mine, theirs}` pairs — whole-record, not field-level. The client shows a git-diff-style comparison and the user picks **keep mine**, **keep theirs**, or **edit manually**. The resolution is submitted via `POST /api/v1/sync/resolve` and applied as a new write (fresh `updated_at`), then the client re-syncs to reconcile its checkpoint.

## Known limitations (accepted trade-offs for v1)

- No three-way merge / common-ancestor snapshot — conflicts show only the two current versions, not a shared base. Sufficient at solo/household scale; would need a version-history table to improve.
- Conflict detection is whole-record: editing different fields of the same record from two devices still flags a conflict, even though a field-level merge could have avoided it. Chosen deliberately to keep the protocol simple and auditable.
- Push ordering matters: a log entry referencing a food created offline must be pushed in (or after) the same batch as that food, so server-side foreign keys resolve. The sync engine pushes in a fixed order: profile/targets → foods/nutrients → recipes → log entries.
