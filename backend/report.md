# Root cause analysis report

**Incident ID:** INC-9084
**Service:** notifications-service
**Severity:** critical
**MTTI:** 0.5s

## Root cause
Disk full on `disk_usage_percent` — disk full pattern
detected, corroborated by a `no space left error` on pod `notifications-service-e19`.

## Evidence
- **Prometheus:** `disk_usage_percent` moved from 59%
  to 100% (+71%) over a 14-minute window
  (confidence 80%).
- **ELK logs:** `ERROR write failed: No space left on device (/var/log/notifications)` on pod `notifications-service-e19` at T-2s
  (matched after scanning 25 lines).
- **Correlation:** the metric anomaly and the log event align in time and service, supporting
  a single shared root cause rather than two unrelated failures.

## Recommended actions
1. Clear or rotate oversized log files immediately
2. Add log rotation with size caps
3. Alert on disk usage above 85%

## Confidence
86%
