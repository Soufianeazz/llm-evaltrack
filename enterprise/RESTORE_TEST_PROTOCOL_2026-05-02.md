# Restore Test Protocol

Stand: 2026-05-02
Owner: Engineering
Environment: Local non-production drill
Status: Completed

## 1. Objective
- Execute one restore drill with time measurement and verification evidence.

## 2. Source and Artifacts
- Source DB: `observability.db`
- Backup artifact: `enterprise/drills/observability_backup_20260502_101944.db`
- Restore artifact: `enterprise/drills/observability_restore_test_20260502_101944.db`

## 3. Timing Results
- Backup copy duration: `10.10 ms`
- Restore copy duration: `1.82 ms`

## 4. Integrity and Consistency Checks
- SHA256 source:
  - `9322A1DD13FFADDDF99DA1A54D59EFD8B8E9E21CE0293BE5557ADE22F7FB5166`
- SHA256 backup:
  - `9322A1DD13FFADDDF99DA1A54D59EFD8B8E9E21CE0293BE5557ADE22F7FB5166`
- SHA256 restore:
  - `9322A1DD13FFADDDF99DA1A54D59EFD8B8E9E21CE0293BE5557ADE22F7FB5166`
- Hash match across all three files: `True`

`PRAGMA integrity_check`:
- source: `ok`
- backup: `ok`
- restore: `ok`

## 5. Record Count Verification
- `requests`: 15
- `evaluations`: 15
- `traces`: 2
- `spans`: 8
- `audit_log`: 0
- `retention_policy`: 0
- `api_keys`: 1
- `demo_requests`: 18

All checked counts were identical across source, backup, and restore artifacts.

## 6. Outcome
- Restore drill passed.
- Backup and restore procedure is reproducible for local SQLite operational data.
- No data divergence detected in this drill.

## 7. Follow-up
- Repeat drill monthly and include production-like environment in next run.
- Track measured RTO trend in weekly reliability review.
