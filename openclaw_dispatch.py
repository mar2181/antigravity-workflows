#!/usr/bin/env python3
"""
openclaw_dispatch.py — Bridge between Claude Code and OpenClaw local Docker worker.

Claude Code uses this to send tasks to OpenClaw and read results back.

Usage:
  python openclaw_dispatch.py --test                    # end-to-end test
  python openclaw_dispatch.py --health                  # check container health
  python openclaw_dispatch.py --stats                   # processing statistics
  python openclaw_dispatch.py --submit ad_copy_draft sugar_shack '{"angle":"summer beach day"}'
  python openclaw_dispatch.py --result task_20260325_143022_abc123
  python openclaw_dispatch.py --pending                 # list pending tasks
  python openclaw_dispatch.py --clear-completed         # clean up old results

As a module (imported by Claude Code):
  from openclaw_dispatch import dispatch_task, check_result, wait_for_result
  task_id = dispatch_task("ad_copy_draft", "sugar_shack", {"angle": "summer"})
  result = wait_for_result(task_id, timeout=120)
"""

import sys
import json
import time
import argparse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

INBOX = Path("C:/Users/mario/openclaw-workspace/inbox")
OUTBOX = Path("C:/Users/mario/openclaw-workspace/outbox")
PROCESSING = Path("C:/Users/mario/openclaw-workspace/processing")
FAILED = Path("C:/Users/mario/openclaw-workspace/failed")
GATEWAY = "http://127.0.0.1:8080"


# ─── Core Functions (used by Claude Code as imports) ─────────────────────────

def dispatch_task(task_type: str, client_key: str, parameters: dict,
                  model: str = "", priority: str = "normal") -> str:
    """Send a task to OpenClaw. Returns task_id."""
    task_id = f"task_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{int(time.time()*1000) % 100000}"

    task = {
        "task_id": task_id,
        "task_type": task_type,
        "client_key": client_key,
        "priority": priority,
        "parameters": {
            "title": f"{task_type} for {client_key}",
            **parameters,
        },
        "model_preference": model,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "created_by": "claude_code",
    }

    task_path = INBOX / f"{task_id}.json"
    task_path.write_text(json.dumps(task, indent=2, ensure_ascii=False), encoding="utf-8")
    return task_id


def check_result(task_id: str) -> dict | None:
    """Check if a task has completed. Returns result dict or None."""
    result_path = OUTBOX / f"result_{task_id}.json"
    if result_path.exists():
        return json.loads(result_path.read_text(encoding="utf-8"))
    return None


def wait_for_result(task_id: str, timeout: int = 300, poll_interval: int = 5) -> dict | None:
    """Block until result is ready or timeout. Returns result dict or None."""
    start = time.time()
    while time.time() - start < timeout:
        result = check_result(task_id)
        if result:
            return result
        time.sleep(poll_interval)
    return None


def check_health() -> dict:
    """Check OpenClaw gateway health."""
    try:
        resp = urllib.request.urlopen(f"{GATEWAY}/health", timeout=5)
        return json.loads(resp.read())
    except Exception as e:
        return {"status": "unreachable", "error": str(e)}


def get_stats() -> dict:
    """Get processing statistics from gateway."""
    try:
        resp = urllib.request.urlopen(f"{GATEWAY}/stats", timeout=5)
        return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


# ─── CLI ─────────────────────────────────────────────────────────────────────

def cmd_test():
    """End-to-end test: dispatch a task, wait for result, verify."""
    print("OpenClaw End-to-End Test")
    print("=" * 40)

    # Check health first
    print("\n1. Checking gateway health...")
    health = check_health()
    if health.get("status") == "unreachable":
        print(f"   FAIL: Gateway unreachable — {health.get('error')}")
        print("   Is the Docker container running? Try: docker ps | grep openclaw")
        return False

    ollama_ok = health.get("ollama", {}).get("connected", False)
    print(f"   Gateway: OK")
    print(f"   Ollama: {'connected' if ollama_ok else 'NOT connected'}")

    if not ollama_ok:
        print("   FAIL: Ollama not connected. Is ollama serve running?")
        return False

    models = health.get("ollama", {}).get("models", [])
    print(f"   Models: {models}")

    # Dispatch test task
    print("\n2. Dispatching test task...")
    task_id = dispatch_task(
        task_type="ad_copy_draft",
        client_key="sugar_shack",
        parameters={
            "angle": "test — summer beach day families",
            "max_words": 100,
            "instruction": "Write a short 50-word test ad for a candy store on the beach.",
        },
    )
    print(f"   Task ID: {task_id}")

    # Wait for result
    print("\n3. Waiting for result (timeout 120s)...")
    result = wait_for_result(task_id, timeout=120, poll_interval=3)

    if not result:
        print("   FAIL: Timeout — no result after 120 seconds")
        return False

    status = result.get("status")
    if status == "failed":
        print(f"   FAIL: Task failed — {result.get('error')}")
        return False

    content = result.get("result", {}).get("content", "")
    model_used = result.get("result", {}).get("metadata", {}).get("model_used", "?")
    duration = result.get("result", {}).get("metadata", {}).get("duration_seconds", "?")
    pushed = result.get("pushed_to_supabase", False)

    print(f"   Status: {status}")
    print(f"   Model: {model_used}")
    print(f"   Duration: {duration}s")
    print(f"   Supabase: {'pushed' if pushed else 'NOT pushed'}")
    print(f"   Content preview: {content[:150]}...")

    print("\n" + "=" * 40)
    print("ALL TESTS PASSED" if status == "completed" else "TESTS FAILED")
    return status == "completed"


def cmd_health():
    """Print health status."""
    health = check_health()
    print(json.dumps(health, indent=2))


def cmd_stats():
    """Print processing stats."""
    stats = get_stats()
    print(json.dumps(stats, indent=2))


def cmd_submit(task_type: str, client_key: str, params_json: str):
    """Submit a task from CLI."""
    params = json.loads(params_json)
    task_id = dispatch_task(task_type, client_key, params)
    print(f"Task queued: {task_id}")


def cmd_result(task_id: str):
    """Print result for a task."""
    result = check_result(task_id)
    if result:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"No result found for {task_id}")


def cmd_pending():
    """List pending and processing tasks."""
    pending = sorted(INBOX.glob("task_*.json"))
    processing = sorted(PROCESSING.glob("*.json"))

    if not pending and not processing:
        print("No pending or processing tasks.")
        return

    if pending:
        print(f"PENDING ({len(pending)}):")
        for p in pending:
            data = json.loads(p.read_text(encoding="utf-8"))
            print(f"  {data.get('task_id')} | {data.get('task_type')} | {data.get('client_key')}")

    if processing:
        print(f"\nPROCESSING ({len(processing)}):")
        for p in processing:
            data = json.loads(p.read_text(encoding="utf-8"))
            print(f"  {data.get('task_id')} | {data.get('task_type')} | {data.get('client_key')}")


def cmd_clear_completed(days_old: int = 7):
    """Remove result files older than N days."""
    import os
    cutoff = time.time() - (days_old * 86400)
    removed = 0
    for p in OUTBOX.glob("result_*.json"):
        if os.path.getmtime(str(p)) < cutoff:
            p.unlink()
            removed += 1
    print(f"Removed {removed} result files older than {days_old} days.")


def main():
    parser = argparse.ArgumentParser(description="OpenClaw Dispatch — Claude Code <-> OpenClaw bridge")
    parser.add_argument("--test", action="store_true", help="Run end-to-end test")
    parser.add_argument("--health", action="store_true", help="Check gateway health")
    parser.add_argument("--stats", action="store_true", help="Get processing stats")
    parser.add_argument("--submit", nargs=3, metavar=("TYPE", "CLIENT", "PARAMS_JSON"),
                        help="Submit a task")
    parser.add_argument("--result", metavar="TASK_ID", help="Get result for a task")
    parser.add_argument("--pending", action="store_true", help="List pending tasks")
    parser.add_argument("--clear-completed", nargs="?", const=7, type=int, metavar="DAYS",
                        help="Remove old results (default: 7 days)")

    args = parser.parse_args()

    if args.test:
        success = cmd_test()
        sys.exit(0 if success else 1)
    elif args.health:
        cmd_health()
    elif args.stats:
        cmd_stats()
    elif args.submit:
        cmd_submit(*args.submit)
    elif args.result:
        cmd_result(args.result)
    elif args.pending:
        cmd_pending()
    elif args.clear_completed is not None:
        cmd_clear_completed(args.clear_completed)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
