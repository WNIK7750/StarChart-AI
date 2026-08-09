# HTTPS production deployment runbook

## Current release state

Status: **PREPARED / NO-GO**

The production overlay may be validated and installed in a dormant state while
the ICP filing is pending. Do not publish production DNS, request the public
certificate, or enable the public application before the filing result is
available.

Production invariants:

- Canonical origin: `https://starchart-ai.xyz`
- `https://www.starchart-ai.xyz` redirects to the canonical origin.
- Production is served at `/`, never under `/StarChart-AI`.
- Application listener: `127.0.0.1:8003`
- Service: `starchart-ai-production`
- Database: `/srv/starchart-ai-production/data/ai_nav.sqlite3`
- Uploads: `/srv/starchart-ai-production/uploads`
- Environment: `/etc/starchart-ai/production.env`
- Canonical template: `deploy/production/env.example`
- The site has no default model and no shared Provider API Key.
- User model API Keys never enter SQLite or the environment file; production
  remains NO-GO for user models until an independent credential-store adapter is available.
- The HTTP test service and its data remain independent.

## Before the ICP result

1. Validate the checkout:

   ```powershell
   .\scripts\verify-repository-layout.ps1
   .\scripts\verify-production-deployment.ps1
   ```

2. Build a release archive using the normal release workflow. Confirm that no
   parent directory, local environment file, key, database, upload, or unrelated
   dirty file is selected.
3. On the server, run the read-only staging preflight:

   ```bash
   sudo deploy/production/scripts/preflight.sh before-staging
   ```

4. Install only the dormant production identity, directories, environment
   template, and systemd unit:

   ```bash
   sudo deploy/production/scripts/install-staging.sh
   ```

5. Create `/etc/starchart-ai/production.env` from the canonical deployment
   template and fill only site-level values interactively. Never paste its
   contents into logs or task output. Generate a unique production secret and
   confirm the explicit allowlist for user-configured model hosts. Do not put a
   user API Key, default model, shared Provider Key, or site cost budget in this file.
6. Validate the production configuration before starting the service. Start it
   only on loopback port `8003`; do not install the public Nginx site yet.
7. Use a fresh production database. Do not copy HTTP-test users or conversations
   into production without a separately reviewed migration.
8. Keep `AI_NAV_AGENT_CREDENTIAL_STORE=unconfigured` until a Linux production
   Secret Manager adapter has been implemented, tested and independently signed
   off. In this state model configuration fails closed while public Learning and
   Tools remain available.

## Inputs required after the ICP result

- ICP filing number and the exact footer wording required by the filing result
- Public support/privacy contact address
- Confirmation that password recovery has a real sender, or a decision to keep
  recovery visibly disabled
- Confirmation of the model-provider domains allowed for user configuration
- A reviewed Linux production credential-store adapter with backup, rotation,
  deletion, least-privilege and audit procedures

## DNS and certificate cutover

Perform this section only after the ICP result is available.

1. Create DNS records with a temporarily low TTL:

   - `A` record for `@` to `47.100.94.1`
   - `CNAME` record for `www` to `starchart-ai.xyz` (an equivalent `A` record is
     also acceptable)

2. Confirm both names resolve publicly to the intended server.
3. Run the pre-certificate checks and install the ACME-only virtual host:

   ```bash
   sudo deploy/production/scripts/preflight.sh before-acme
   sudo deploy/production/scripts/install-acme.sh
   ```

   This host exposes only `/.well-known/acme-challenge/`; every other request
   returns `503`, so the production application is still not public.

4. Request a certificate for both names:

   ```bash
   sudo certbot certonly --webroot \
     -w /var/www/letsencrypt \
     -d starchart-ai.xyz \
     -d www.starchart-ai.xyz
   sudo certbot renew --dry-run
   ```

5. Confirm the loopback production service and certificates, then install HTTPS:

   ```bash
   sudo deploy/production/scripts/preflight.sh before-https
   sudo deploy/production/scripts/backup.sh
   sudo deploy/production/scripts/install-https.sh
   sudo deploy/production/scripts/smoke-test.sh
   ```

6. Complete browser checks for registration, login, password recovery status,
   learning nodes, assistant streaming, conversation persistence, upload limits,
   logout, and mobile layout.

## Go-live gates

Do not declare production ready until all gates pass:

- ICP number is displayed and links to the required filing system.
- Public security filing is completed within the applicable post-launch window.
- Privacy terms, public contact, and data-retention behavior are visible.
- Password recovery is operational or explicitly unavailable to users.
- User-model provider terms and the host allowlist are confirmed.
- The independent credential store passes save, read, rotate, delete, isolation,
  backup and restore tests without storing API Keys in SQLite or logs.
- Capacity, monitoring, alerting, backup, isolated restore rehearsal, and
  rollback rehearsal pass.
- Certificate renewal dry-run succeeds.
- HTTP redirects to HTTPS; `www` redirects to the root domain.
- No secret, database, upload, parent directory, or unrelated worktree file is
  included in the release.

## Backup and restore rehearsal

Create a verified backup:

```bash
sudo deploy/production/scripts/backup.sh
```

Restore only into the isolated rehearsal database:

```bash
sudo deploy/production/scripts/restore-rehearsal.sh \
  /var/backups/starchart-ai-production/ai_nav-UTC_TIMESTAMP.sqlite3
```

The rehearsal script refuses to overwrite an existing target and never replaces
the live database.

## Rollback

1. Disable user-model access first if credential storage or provider behavior is involved.
2. Stop `starchart-ai-production`.
3. Restore the previous release pointer and the Nginx file saved under
   `/var/backups/starchart-ai-production/`.
4. Run `nginx -t` before reloading Nginx.
5. Restore the production database only from a verified backup when data
   corruption is confirmed. Do not use destructive schema downgrades.
6. Re-run health and security checks before reopening traffic.
