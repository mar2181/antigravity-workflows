"""Check 5 — Supabase env key NAMES present. Never reads or logs values."""

from pathlib import Path

from . import Finding

CHECK_ID = "supabase_env"
ENV_PATH = Path("C:/Users/mario/.gemini/antigravity/scratch/gravity-claw/.env")
REQUIRED_KEYS = ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")
PROPOSED_FIX = (
    "See Terminal A instructions to repopulate Supabase env "
    f"keys in {ENV_PATH} (do NOT paste values into the repo)"
)


def _extract_key_names(text: str) -> set:
    keys = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key = stripped.split("=", 1)[0].strip()
        if key.lower().startswith("export "):
            key = key[len("export ") :].strip()
        if key:
            keys.add(key)
    return keys


def run() -> Finding:
    if not ENV_PATH.exists():
        return Finding.now(
            id=f"{CHECK_ID}_env_missing",
            severity="error",
            problem=f"Supabase env file missing: {ENV_PATH}",
            root_cause_guess="gravity-claw .env was deleted or never created on this machine",
            proposed_fix=PROPOSED_FIX,
        )

    try:
        text = ENV_PATH.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return Finding.now(
            id=f"{CHECK_ID}_unreadable",
            severity="error",
            problem=f"Cannot read {ENV_PATH}: {exc}",
            root_cause_guess="Permissions or lock issue on the .env file",
            proposed_fix=f"Confirm read access to {ENV_PATH}",
        )

    present = _extract_key_names(text)
    missing = [k for k in REQUIRED_KEYS if k not in present]

    if missing:
        return Finding.now(
            id=f"{CHECK_ID}_missing_keys",
            severity="error",
            problem=f"Missing Supabase env key name(s): {', '.join(missing)}",
            root_cause_guess=f"Key name(s) not present in {ENV_PATH} (values not inspected)",
            proposed_fix=PROPOSED_FIX,
        )

    return Finding.now(
        id=f"{CHECK_ID}_ok",
        severity="info",
        problem="Supabase env key names present (values not inspected)",
        root_cause_guess="",
        proposed_fix="",
    )
