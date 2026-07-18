# Users command safety matrix

## Policy

Every Users-owned write route must be registered in
`backend/app/users/command_safety.py` with three controls:

- **Audit**: a registered append-only audit event or an equally durable security log.
- **Replay**: an idempotency key, optimistic version, one-time token, natural
  idempotency, guarded state transition, or explicit reauthentication policy.
- **Concurrency**: a transaction, conditional update/delete, unique constraint,
  optimistic version, or atomic token rotation.

The policy is risk-based. Requiring a generic `Idempotency-Key` on password
verification, login, logout, or token refresh would not improve their safety.
Those commands instead use rate limits, reauthentication, one-time tokens,
conditional state transitions, and refresh-token replay detection.

## Coverage summary

| Domain | Commands | Primary replay control | Primary concurrency control |
| --- | ---: | --- | --- |
| Authentication | 7 | rate limits, one-time tokens, rotation | transactions and conditional state |
| Account/security/profile/preferences/sessions | 8 | versions, reauthentication, natural idempotency | conditional updates and transactions |
| Privacy lifecycle | 7 | policy versions and guarded transitions | transactions and conditional state |
| Learning state | 6 | versions, idempotency keys, unique targets | transactions and unique constraints |
| Workflow assets, including Agent save | 5 | idempotency key and versions | transactions and conditional updates |
| **Total** | **33** | | |

The canonical row-level matrix lives in `COMMAND_SAFETY` so it cannot drift
independently from enforcement. `scripts/check-users-command-safety.py` derives
the actual FastAPI command surface and fails on missing, stale, incomplete, or
unknown audit registrations.

## Authentication audit events

The authentication lifecycle now emits:

- `users.auth.registered`
- `users.auth.login_succeeded` (in addition to the success/failure login log)
- `users.auth.password_reset_started`
- `users.auth.password_reset_verified`
- `users.auth.password_reset_completed`
- `users.auth.session_refreshed`
- `users.auth.session_logged_out`

Audit metadata is allowlisted. Passwords, answers, reset tokens, refresh tokens,
cookies, authorization headers, and raw request bodies are never recorded.

Account contact changes emit `users.account.updated` with field names only.
Email and phone values are excluded from audit metadata, and changing either
contact requires current-password reauthentication.

## Verification

Run:

```powershell
.\scripts\verify-users.ps1
```

The suite compiles the registry, checks all current routes, validates audit event
references, runs service regressions, and includes the result in the security
baseline as `USR-SEC-027`.
