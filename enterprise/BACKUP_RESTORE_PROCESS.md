# Backup and Restore Process

Stand: 2026-05-02
Owner: Engineering
Status: v1

## 1. Purpose
- Define a repeatable backup and restore process for AgentLens runtime data.
- Cover frequency, retention, restore steps, and verification.

## 2. Scope
- In scope:
  - SQLite operational database (all core tables, including requests, evaluations, traces, demo requests, audit log)
- Out of scope:
  - Application source code (already covered by Git)
  - Secret values (managed by deployment platform secrets)

## 3. Source of Truth
- Database location is derived from `DATABASE_URL`.
- Current default in code is `sqlite+aiosqlite:///./observability.db`.
- Production example in comments: `sqlite+aiosqlite:////data/llm_observe.db`.

## 4. Backup Policy v1
- Frequency:
  - Daily full backup (once every 24h)
  - Additional on-demand backup before schema changes or major releases
- Retention:
  - Daily backups: 30 days
  - Weekly snapshot: 12 weeks
  - Monthly snapshot: 12 months
- Storage:
  - Keep backups outside the active runtime path
  - Encrypt at rest in backup storage

## 5. Backup Procedure (SQLite)

### 5.1 Preferred method (SQLite online backup)
Use `sqlite3` when available:

```powershell
sqlite3 observability.db ".timeout 5000" ".backup backup/observability_$(Get-Date -Format yyyyMMdd_HHmmss).db"
```

### 5.2 Fallback method (file copy during maintenance window)
If `sqlite3` is not available, stop writes briefly and copy file:

```powershell
Copy-Item -LiteralPath .\observability.db -Destination .\backup\observability_$(Get-Date -Format yyyyMMdd_HHmmss).db
```

### 5.3 Integrity check after backup
```powershell
sqlite3 .\backup\<backup_file>.db "PRAGMA integrity_check;"
```
Expected result: `ok`

## 6. Restore Procedure

### 6.1 Pre-restore checklist
- Identify target backup file.
- Confirm incident/ticket approval for restore.
- Stop application writes (or put app in maintenance mode).
- Preserve current DB as pre-restore snapshot.

### 6.2 Restore steps
1. Create safety snapshot of current file:
```powershell
Copy-Item -LiteralPath .\observability.db -Destination .\backup\pre_restore_$(Get-Date -Format yyyyMMdd_HHmmss).db
```
2. Replace database with selected backup:
```powershell
Copy-Item -LiteralPath .\backup\<selected_backup>.db -Destination .\observability.db -Force
```
3. Start application and run smoke tests:
  - `GET /requests/stats`
  - `GET /compliance/stats`
  - `GET /traces`

### 6.3 Post-restore validation
- Confirm expected record counts and newest timestamps.
- Confirm dashboard pages load.
- Confirm ingest endpoint accepts new events.

## 7. Recovery Targets (initial v1)
- RPO target: <= 24 hours (daily backup cadence)
- RTO target: <= 60 minutes for standard restore

## 8. Logging and Evidence
- For every backup and restore, record:
  - Timestamp (UTC)
  - Operator
  - Source DB path
  - Backup filename
  - Integrity check result
  - Restore duration (if restore executed)

## 9. Restore Drill Cadence
- Run restore drill at least once per month.
- Execute in non-production first.
- Capture measured restore time and issues.

## 10. Railway Notes (production)
- Ensure persistent volume is used for SQLite path from `DATABASE_URL`.
- Backup automation can run as scheduled task that:
  - Executes SQLite backup
  - Uploads encrypted backup to external storage
  - Retains according to policy in section 4

## 11. Action Items to Operationalize v1
- Add scheduled backup job in deployment environment.
- Add backup status check in weekly ops review.
- Add monthly restore drill entry to incident/reliability calendar.
