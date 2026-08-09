import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

INTERNAL_API_KEY = os.environ["INTERNAL_API_KEY"]
BACKUP_SERVICE_URL = os.getenv("BACKUP_SERVICE_URL", "http://backup-service:8000")
AUTO_BACKUP_ENABLED = os.getenv("AUTO_BACKUP_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
AUTO_BACKUP_TIME = os.getenv("AUTO_BACKUP_TIME", "02:00")
TZ = os.getenv("TZ", "America/Guayaquil")
STATUS_FILE = Path(os.getenv("BACKUP_SCHEDULER_STATUS_FILE", "/backup-state/scheduler.json"))
POLL_SECONDS = max(int(os.getenv("BACKUP_SCHEDULER_POLL_SECONDS", "30")), 10)


def parse_time(value):
    try:
        hour, minute = [int(part) for part in value.split(":", 1)]
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
        return hour, minute
    except Exception as exc:
        raise RuntimeError("AUTO_BACKUP_TIME debe tener formato HH:MM") from exc


def write_status(**updates):
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    try:
        if STATUS_FILE.exists():
            data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    data.update(updates)
    data["updated_at"] = datetime.now(ZoneInfo(TZ)).isoformat()
    temp = STATUS_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(STATUS_FILE)


def next_run(now, hour, minute):
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def trigger_backup():
    response = requests.post(
        f"{BACKUP_SERVICE_URL}/api/backups/google-drive",
        headers={"X-Internal-Key": INTERNAL_API_KEY, "X-User-Role": "admin"},
        json={"actor_name": "Respaldo automático diario"},
        timeout=600,
    )
    if response.status_code != 200:
        try:
            message = response.json().get("error")
        except Exception:
            message = response.text[:500]
        raise RuntimeError(message or f"HTTP {response.status_code}")
    return response.json()


def main():
    hour, minute = parse_time(AUTO_BACKUP_TIME)
    tz = ZoneInfo(TZ)
    last_run_date = None
    write_status(enabled=AUTO_BACKUP_ENABLED, configured_time=AUTO_BACKUP_TIME, timezone=TZ)
    while True:
        now = datetime.now(tz)
        if not AUTO_BACKUP_ENABLED:
            write_status(enabled=False, configured_time=AUTO_BACKUP_TIME, timezone=TZ, next_run=None)
            time.sleep(POLL_SECONDS)
            continue
        nr = next_run(now, hour, minute)
        write_status(enabled=True, configured_time=AUTO_BACKUP_TIME, timezone=TZ, next_run=nr.isoformat())
        if (now.hour, now.minute) >= (hour, minute) and last_run_date != now.date().isoformat():
            write_status(last_attempt=now.isoformat(), state="running")
            try:
                result = trigger_backup()
                last_run_date = now.date().isoformat()
                write_status(last_success=datetime.now(tz).isoformat(), last_run_date=last_run_date, state="success", result=result)
            except Exception as exc:
                write_status(last_failure=datetime.now(tz).isoformat(), state="error", error=str(exc)[:1000])
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
