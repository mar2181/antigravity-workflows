#!/usr/bin/env python3
"""
telegram_bot.py — Antigravity Telegram Command Bot (Level 2 — Claude-Powered)

Slash commands  → instant script execution, no API cost
Free-text       → routed through Claude API (claude-sonnet-4-6) with full
                  CLAUDE.md + MEMORY.md context + conversation history

Usage:
    cd "C:/Users/mario/.gemini/antigravity/tools/execution"
    python telegram_bot.py

Commands (instant, no API):
    /report   — Run daily intelligence report
    /brief    — Run morning brief (text-only)
    /status   — Facebook session health check
    /queue    — Show autoresearch queue
    /reviews  — Show pending GBP reviews
    /reset    — Clear conversation history
    /help     — List commands

Mission Control audit commands:
    /mc_audit          — Run dashboard audit now (sends findings to Telegram)
    /mc_apply 1 3 6    — Apply specific numbered fixes
    /mc_apply all      — Apply all low-risk fixes

Skills self-healing commands:
    /skill_scan        — Show top 20 weakest skills (no API, instant)
    /skill_scan N      — Show top N weakest
    /skill_heal        — Run overnight batch improvement (top 50, background)
    /skill_heal N      — Run on top N weakest skills only

Free-text examples:
    "what should I post for Sugar Shack this weekend?"
    "summarize the competitor intel for Island Arcade"
    "write a bilingual ad for Juan" (follows up on prior answer)
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Paths ─────────────────────────────────────────────────────────────────
EXECUTION_DIR  = Path(__file__).parent
SCRATCH_DIR    = EXECUTION_DIR.parent.parent / "scratch"
ENV_PATH       = SCRATCH_DIR / "gravity-claw" / ".env"
CONFIG_PATH    = SCRATCH_DIR / "jack_automations_vault" / "skill_improver_config.json"
VAULT_DIR      = SCRATCH_DIR / "jack_automations_vault"
CLAUDE_MD_PATH = Path("C:/Users/mario/.claude/CLAUDE.md")
MEMORY_MD_PATH = Path("C:/Users/mario/.claude/projects/C--Users-mario/memory/MEMORY.md")
QUEUE_PATH     = EXECUTION_DIR / "autoresearch_queue.json"
INTEL_SCRIPT   = SCRATCH_DIR / "SCR_daily_intelligence.py"
BRIEF_SCRIPT   = EXECUTION_DIR / "morning_brief.py"
HEALTH_SCRIPT  = EXECUTION_DIR / "fb_health_check.py"

MAX_HISTORY_TURNS = 20  # keep last 20 user+assistant pairs = 40 messages


# ── Credentials ───────────────────────────────────────────────────────────
def _load_env(path: Path) -> dict:
    env: dict = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return env

def _load_anthropic_key() -> str:
    # Try skill_improver_config.json first (confirmed present)
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        key = cfg.get("anthropic_api_key", "")
        if key:
            return key
    except Exception:
        pass
    # Fallback: env var
    return os.environ.get("ANTHROPIC_API_KEY", "")

_env     = _load_env(ENV_PATH)
TOKEN    = _env.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
OWNER_ID = str(_env.get("TELEGRAM_USER_ID") or os.environ.get("TELEGRAM_USER_ID", ""))
ANTHROPIC_KEY  = _load_anthropic_key()
OPENROUTER_KEY = _env.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY", "")
TELEGRAM_MODEL = _env.get("TELEGRAM_MODEL", "anthropic/claude-sonnet-4-6")

if not TOKEN or not OWNER_ID:
    sys.exit("ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_USER_ID not found in .env")
if not OPENROUTER_KEY and not ANTHROPIC_KEY:
    print("WARNING: No LLM API key found — free-text messages will not work.")


# ── Claude context (loaded once at startup) ───────────────────────────────
def _load_claude_context() -> str:
    parts = []
    try:
        parts.append(CLAUDE_MD_PATH.read_text(encoding="utf-8", errors="replace"))
    except FileNotFoundError:
        parts.append("[CLAUDE.md not found]")
    try:
        lines = MEMORY_MD_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
        parts.append("\n\n--- MEMORY (first 200 lines) ---\n" + "\n".join(lines[:200]))
    except FileNotFoundError:
        pass
    return "\n\n".join(parts)

SYSTEM_PROMPT = _load_claude_context()


# ── Telegram API helpers ───────────────────────────────────────────────────
BASE = f"https://api.telegram.org/bot{TOKEN}"

def _tg(method: str, payload: dict) -> dict:
    data = urllib.parse.urlencode(payload).encode()
    req  = urllib.request.Request(f"{BASE}/{method}", data=data)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": e.read().decode()}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def send(chat_id: str, text: str) -> None:
    """Send a message, splitting at 4096-char chunks if needed."""
    text = text or "(empty response)"
    for i in range(0, max(len(text), 1), 4096):
        _tg("sendMessage", {"chat_id": chat_id, "text": text[i:i + 4096]})

def get_updates(offset: int) -> list:
    result = _tg("getUpdates", {"offset": offset, "timeout": 3, "limit": 10})
    return result.get("result", []) if result.get("ok") else []

def answer_callback(callback_query_id: str) -> None:
    _tg("answerCallbackQuery", {"callback_query_id": callback_query_id})


# ── LLM API (OpenRouter primary, Anthropic fallback) ──────────────────────
def _call_llm(history: list) -> str:
    """Send conversation history to LLM, return reply text.
    Uses OpenRouter if key available, falls back to Anthropic direct."""
    if OPENROUTER_KEY:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
        payload  = json.dumps({
            "model":      TELEGRAM_MODEL,
            "max_tokens": 1024,
            "messages":   messages,
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=payload,
            headers={
                "Content-Type":  "application/json",
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "HTTP-Referer":  "https://antigravity.local",
                "X-Title":       "Antigravity Bot",
            },
        )
        try:
            resp   = urllib.request.urlopen(req, timeout=60)
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            err = e.read().decode()
            return f"OpenRouter error {e.code}: {err[:300]}"
        except Exception as e:
            return f"OpenRouter error: {e}"

    if ANTHROPIC_KEY:
        payload = json.dumps({
            "model":      "claude-sonnet-4-6",
            "max_tokens": 1024,
            "system":     SYSTEM_PROMPT,
            "messages":   history,
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type":      "application/json",
                "x-api-key":         ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
            },
        )
        try:
            resp   = urllib.request.urlopen(req, timeout=60)
            result = json.loads(resp.read())
            return result["content"][0]["text"]
        except urllib.error.HTTPError as e:
            err = e.read().decode()
            return f"Anthropic error {e.code}: {err[:300]}"
        except Exception as e:
            return f"Anthropic error: {e}"

    return "⚠️ No LLM API key configured. Add OPENROUTER_API_KEY to gravity-claw/.env"


# ── Command handlers ───────────────────────────────────────────────────────
def cmd_help(chat_id: str, _hist: list) -> None:
    send(chat_id, (
        "🤖 Antigravity Bot v3\n\n"
        "WORKFLOW COMMANDS (run pipelines from phone):\n"
        "/ad <client> <angle>   — Generate ad copy\n"
        "/blog <client> <kw>    — Generate blog post\n"
        "/post <client> <msg>   — Quick FB text post\n"
        "/claude <prompt>       — Claude Code (full context, remembers session)\n"
        "/claude_reset          — Start fresh Claude Code session\n"
        "/3d <url or prompt>    — Convert image to 3D model\n"
        "/rag <query>           — Search knowledge base\n\n"
        "INSTANT COMMANDS (no API cost):\n"
        "/report         — Daily intelligence report\n"
        "/brief          — Morning brief summary\n"
        "/status         — Facebook session health\n"
        "/queue          — Autoresearch queue\n"
        "/reviews        — Pending GBP reviews to answer\n"
        "/review_history — Last 20 reviews + status\n"
        "/reset          — Clear conversation history\n"
        "/help           — This message\n\n"
        "MISSION CONTROL AUDIT:\n"
        "/mc_audit          — Run dashboard audit now\n"
        "/mc_apply 1 3 6    — Apply numbered fixes\n"
        "/mc_apply all      — Apply all low-risk fixes\n\n"
        "SKILLS SELF-HEALING (841 skills vault):\n"
        "/skill_scan        — Show top 20 weakest skills (instant)\n"
        "/skill_scan 50     — Show top N weakest\n"
        "/skill_heal        — Run overnight improvement (top 50, background)\n"
        "/skill_heal 10     — Run on top N weakest only\n\n"
        "REVIEW BUTTONS:\n"
        "Tap ✅ Post / ✏️ Edit / ❌ Skip on review alerts.\n\n"
        "FREE-TEXT (Claude-powered):\n"
        "Ask anything — ad copy, competitor intel,\n"
        "campaign strategy, client questions.\n"
        "Follows up on previous messages in session."
    ))

def cmd_report(chat_id: str, _hist: list) -> None:
    send(chat_id, "⏳ Running intelligence report...")
    result = subprocess.run(
        [sys.executable, str(INTEL_SCRIPT)],
        capture_output=True, text=True, cwd=str(SCRATCH_DIR), timeout=120
    )
    output = result.stdout.strip() or result.stderr.strip() or "Done (no output)."
    send(chat_id, f"📊 Intelligence Report\n\n{output}")

def cmd_brief(chat_id: str, _hist: list) -> None:
    send(chat_id, "⏳ Running morning brief...")
    result = subprocess.run(
        [sys.executable, str(BRIEF_SCRIPT), "--text-only"],
        capture_output=True, text=True, cwd=str(EXECUTION_DIR), timeout=120
    )
    output = result.stdout.strip() or result.stderr.strip() or "Done."
    send(chat_id, f"☀️ Morning Brief\n\n{output}")

def cmd_status(chat_id: str, _hist: list) -> None:
    send(chat_id, "⏳ Checking Facebook sessions...")
    result = subprocess.run(
        [sys.executable, str(HEALTH_SCRIPT)],
        capture_output=True, text=True, cwd=str(EXECUTION_DIR), timeout=60
    )
    output = result.stdout.strip() or result.stderr.strip() or "Done."
    send(chat_id, f"🔍 FB Session Status\n\n{output}")

def cmd_queue(chat_id: str, _hist: list) -> None:
    if not QUEUE_PATH.exists():
        send(chat_id, "📭 No items in autoresearch queue.")
        return
    try:
        items = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
        if not items:
            send(chat_id, "📭 Queue is empty.")
            return
        lines = ["📋 Autoresearch Queue:"]
        for item in items:
            lines.append(f"  • {item['business']} ({item['date']}) — {item.get('source','?')}")
        lines.append("\nRun: python ad_copy_optimizer.py <business>")
        send(chat_id, "\n".join(lines))
    except Exception as e:
        send(chat_id, f"Error reading queue: {e}")

def cmd_reviews(chat_id: str, _hist: list) -> None:
    """Show all pending (unreplied, unskipped) GBP reviews."""
    state_file = EXECUTION_DIR / "gbp_review_state.json"
    if not state_file.exists():
        send(chat_id, "📭 No review state found. Is the watcher running?")
        return
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
        reviews = state.get("reviews", {})
        pending = [(rid, r) for rid, r in reviews.items()
                   if not r.get("replied") and not r.get("skipped")]
        if not pending:
            send(chat_id, "✅ No pending reviews! All caught up.")
            return
        lines = [f"📋 {len(pending)} Pending Review(s):\n"]
        for rid, r in pending[-10:]:  # last 10
            stars = "⭐" * r.get("stars", 5)
            lines.append(
                f"{stars} {r.get('business_name','?')}\n"
                f"👤 {r.get('reviewer','?')}: {r.get('text','')[:80]}...\n"
                f"ID: {rid[:16]}\n"
            )
        send(chat_id, "\n".join(lines))
    except Exception as e:
        send(chat_id, f"Error reading reviews: {e}")


def cmd_review_history(chat_id: str, _hist: list) -> None:
    """Show last 20 reviews with reply status."""
    state_file = EXECUTION_DIR / "gbp_review_state.json"
    if not state_file.exists():
        send(chat_id, "📭 No review history yet.")
        return
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
        reviews = list(state.get("reviews", {}).items())[-20:]
        if not reviews:
            send(chat_id, "📭 No reviews recorded yet.")
            return
        lines = [f"📜 Last {len(reviews)} Review(s):\n"]
        for rid, r in reversed(reviews):
            stars  = "⭐" * r.get("stars", 5)
            status = "✅ Replied" if r.get("replied") else ("⬜ Skipped" if r.get("skipped") else "🟡 Pending")
            lines.append(f"{stars} {r.get('business_name','?')} — {r.get('reviewer','?')} — {status}")
        send(chat_id, "\n".join(lines))
    except Exception as e:
        send(chat_id, f"Error: {e}")


VALID_CLIENTS = {
    "sugar_shack", "island_arcade", "island_candy", "juan",
    "spi_fun_rentals", "custom_designs_tx", "optimum_clinic", "optimum_foundation",
}

# Track Claude Code session for --continue support
_claude_session_active = False


def cmd_ad(chat_id: str, text: str) -> None:
    """Generate ad copy: /ad <client> <angle>"""
    parts = text.split(None, 2)  # /ad client angle...
    if len(parts) < 3:
        send(chat_id, "Usage: /ad <client> <angle>\n"
             f"Clients: {', '.join(sorted(VALID_CLIENTS))}\n"
             "Example: /ad sugar_shack road trip families")
        return
    client, angle = parts[1].lower(), parts[2]
    if client not in VALID_CLIENTS:
        send(chat_id, f"❌ Unknown client: {client}\nValid: {', '.join(sorted(VALID_CLIENTS))}")
        return
    send(chat_id, f"✍️ Generating ad copy for {client} — angle: {angle}...")
    try:
        result = subprocess.run(
            [sys.executable, str(EXECUTION_DIR / "ad_copy_optimizer.py"), client, "--angle", angle],
            capture_output=True, text=True, cwd=str(EXECUTION_DIR), timeout=120,
        )
        output = result.stdout.strip() or result.stderr.strip() or "Done (no output)."
        send(chat_id, f"📝 Ad Copy — {client}\n\n{output}")
    except subprocess.TimeoutExpired:
        send(chat_id, "⏰ Ad generation timed out (2 min limit). Try a simpler angle.")
    except Exception as e:
        send(chat_id, f"❌ Error: {e}")


def cmd_blog(chat_id: str, text: str) -> None:
    """Generate blog post: /blog <client> <keyword>"""
    parts = text.split(None, 2)  # /blog client keyword...
    if len(parts) < 3:
        send(chat_id, "Usage: /blog <client> <keyword>\n"
             "Example: /blog custom_designs_tx security camera installation mcallen tx")
        return
    client, keyword = parts[1].lower(), parts[2]
    if client not in VALID_CLIENTS:
        send(chat_id, f"❌ Unknown client: {client}\nValid: {', '.join(sorted(VALID_CLIENTS))}")
        return
    send(chat_id, f"📝 Generating blog for {client} — keyword: {keyword}\n"
         "This takes a few minutes. You'll get a Telegram notification when done.")
    subprocess.Popen(
        [sys.executable, str(EXECUTION_DIR / "blog_writer.py"),
         "--client", client, "--keyword", keyword],
        cwd=str(EXECUTION_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def cmd_post(chat_id: str, text: str) -> None:
    """Quick FB text post: /post <client> <message>"""
    parts = text.split(None, 2)  # /post client message...
    if len(parts) < 3:
        send(chat_id, "Usage: /post <client> <message>\n"
             "Example: /post sugar_shack Happy Sunday from South Padre!")
        return
    client, message = parts[1].lower(), parts[2]
    if client not in VALID_CLIENTS:
        send(chat_id, f"❌ Unknown client: {client}\nValid: {', '.join(sorted(VALID_CLIENTS))}")
        return
    send(chat_id, f"📤 Posting to {client} Facebook page...")
    try:
        result = subprocess.run(
            [sys.executable, str(EXECUTION_DIR / "facebook_marketer.py"),
             "--action", "text", "--page", client, "--message", message],
            capture_output=True, text=True, cwd=str(EXECUTION_DIR), timeout=120,
        )
        output = result.stdout.strip() or result.stderr.strip() or "Done."
        if result.returncode == 0:
            send(chat_id, f"✅ Posted to {client}!\n\n{output[:500]}")
        else:
            send(chat_id, f"⚠️ Post may have failed:\n{output[:500]}")
    except subprocess.TimeoutExpired:
        send(chat_id, "⏰ Posting timed out. Check FB session with /status")
    except Exception as e:
        send(chat_id, f"❌ Error: {e}")


def cmd_claude(chat_id: str, text: str) -> None:
    """Run Claude Code headless with full context + conversation continuity."""
    global _claude_session_active
    parts = text.split(None, 1)  # /claude prompt...
    if len(parts) < 2:
        send(chat_id, "Usage: /claude <prompt>\n"
             "Example: /claude list all files in the sugar_shack folder\n"
             "Use /claude_reset to start a fresh session")
        return
    prompt = parts[1]
    # Build command — use --continue if we have an active session
    cmd = ["claude", "-p", "--model", "sonnet"]
    if _claude_session_active:
        cmd.append("--continue")
    cmd.append(prompt)
    mode_label = "continuing session" if _claude_session_active else "new session"
    send(chat_id, f"🧠 Running Claude Code ({mode_label})... up to 5 min")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True, text=True,
            cwd=str(EXECUTION_DIR), timeout=300,
        )
        output = result.stdout.strip() or result.stderr.strip() or "Done (no output)."
        if result.returncode == 0:
            _claude_session_active = True  # session exists now, can --continue next time
        header = "🤖 Claude Code Result:\n\n"
        send(chat_id, header + output[:4000])
    except subprocess.TimeoutExpired:
        send(chat_id, "⏰ Claude Code timed out (5 min limit). Try a simpler prompt.")
    except FileNotFoundError:
        send(chat_id, "❌ Claude CLI not found. Is it installed?")
    except Exception as e:
        send(chat_id, f"❌ Error: {e}")


def cmd_claude_reset(chat_id: str, text: str) -> None:
    """Reset Claude Code session — next /claude starts fresh."""
    global _claude_session_active
    _claude_session_active = False
    send(chat_id, "🔄 Claude Code session reset. Next /claude starts a fresh conversation.")


def cmd_rag(chat_id: str, text: str) -> None:
    """Search knowledge base: /rag <query>"""
    parts = text.split(None, 1)
    if len(parts) < 2:
        send(chat_id, "Usage: /rag <search query>\n\n"
             "Examples:\n"
             "  /rag what ad angles work for sugar shack\n"
             "  /rag competitor weaknesses island arcade\n"
             "  /rag optimum clinic blog ideas")
        return
    query = parts[1].strip()
    send(chat_id, f"🔍 Searching knowledge base...")
    try:
        result = subprocess.run(
            [sys.executable, str(EXECUTION_DIR / "rag_pipeline.py"),
             "search", query, "--top", "3", "--context"],
            capture_output=True, text=True, cwd=str(EXECUTION_DIR), timeout=30,
        )
        output = result.stdout.strip() or result.stderr.strip() or "No results."
        send(chat_id, f"📚 RAG Results:\n\n{output[:3500]}")
    except subprocess.TimeoutExpired:
        send(chat_id, "⏰ Search timed out.")
    except Exception as e:
        send(chat_id, f"❌ Error: {e}")


def cmd_3d(chat_id: str, text: str) -> None:
    """Convert image/prompt to 3D: /3d <url-or-prompt>"""
    parts = text.split(None, 1)
    if len(parts) < 2:
        send(chat_id, "Usage: /3d <image-url or text prompt>\n\n"
             "Examples:\n"
             "  /3d https://example.com/photo.jpg\n"
             "  /3d modern security camera on a wall bracket\n\n"
             "Cost: $0.30-$0.45 per model")
        return
    source = parts[1].strip()
    is_url = source.startswith("http://") or source.startswith("https://")
    mode = "--url" if is_url else "--prompt"
    send(chat_id, f"🔮 Converting to 3D model... ({'from URL' if is_url else 'generating image first'})\n"
         "This takes 1-3 minutes.")
    try:
        result = subprocess.run(
            [sys.executable, str(EXECUTION_DIR / "image_to_3d.py"),
             mode, source, "--texture", "standard", "--notify"],
            capture_output=True, text=True, cwd=str(EXECUTION_DIR), timeout=300,
        )
        output = result.stdout.strip() or result.stderr.strip() or "Done."
        if result.returncode == 0:
            send(chat_id, f"✅ 3D model ready!\n\n{output[-500:]}")
        else:
            send(chat_id, f"⚠️ 3D conversion issue:\n{output[-500:]}")
    except subprocess.TimeoutExpired:
        send(chat_id, "⏰ 3D conversion timed out (5 min limit).")
    except Exception as e:
        send(chat_id, f"❌ Error: {e}")


COMMANDS = {
    "/help":           cmd_help,
    "/report":         cmd_report,
    "/brief":          cmd_brief,
    "/status":         cmd_status,
    "/queue":          cmd_queue,
    "/reviews":        cmd_reviews,
    "/review_history": cmd_review_history,
}


# ── Dispatch ──────────────────────────────────────────────────────────────
def dispatch(chat_id: str, text: str, history: list) -> list:
    """Handle one message. Returns updated history list."""
    text = text.strip()
    first_word = text.split()[0].lower() if text else ""

    if first_word == "/reset":
        send(chat_id, "🔄 Conversation history cleared.")
        return []

    # Workflow commands (need full text for args)
    if first_word in ("/ad", "/blog", "/post", "/claude", "/claude_reset", "/3d", "/rag"):
        handler = {"/ad": cmd_ad, "/blog": cmd_blog, "/post": cmd_post, "/claude": cmd_claude, "/claude_reset": cmd_claude_reset, "/3d": cmd_3d, "/rag": cmd_rag}
        handler[first_word](chat_id, text)
        return history

    # Mission Control audit commands (handle before COMMANDS dict — need args)
    if first_word == "/mc_audit":
        send(chat_id, "🔄 Running Mission Control audit... (~90 seconds)")
        result = subprocess.run(
            [sys.executable, str(EXECUTION_DIR / "mission_control_auditor.py")],
            capture_output=True, text=True, cwd=str(EXECUTION_DIR), timeout=300,
        )
        if result.returncode != 0 and not result.stdout:
            send(chat_id, f"❌ Audit failed:\n{(result.stderr or 'No output')[:400]}")
        return history

    if first_word == "/mc_apply":
        parts = text.split()[1:]
        if not parts:
            send(chat_id, "Usage: /mc_apply 1 3 6\n       /mc_apply all")
            return history
        send(chat_id, "⚙️ Applying fixes and verifying build... (up to 5 minutes)")
        result = subprocess.run(
            [sys.executable, str(EXECUTION_DIR / "mission_control_auditor.py"), "--apply"] + parts,
            capture_output=True, text=True, cwd=str(EXECUTION_DIR), timeout=360,
        )
        output = result.stdout.strip() or result.stderr.strip() or "Done (no output)."
        send(chat_id, output)
        return history

    # Skills self-healing commands
    if first_word == "/skill_scan":
        parts = text.split()[1:]
        top_n = parts[0] if parts and parts[0].isdigit() else "20"
        send(chat_id, f"🔍 Scanning skills vault for weaknesses (top {top_n})...")
        result = subprocess.run(
            [sys.executable, str(VAULT_DIR / "skill_scanner.py"), "--top", top_n],
            capture_output=True, text=True, cwd=str(VAULT_DIR), timeout=60,
        )
        output = result.stdout.strip() or result.stderr.strip() or "No output."
        send(chat_id, f"📊 Skill Scan Results\n\n{output}")
        return history

    if first_word == "/skill_heal":
        parts = text.split()[1:]
        limit = parts[0] if parts and parts[0].isdigit() else "50"
        send(chat_id,
             f"🧠 Starting Skills self-healing run (top {limit} weakest)...\n"
             f"Running in background — you'll get a Telegram when done.\n"
             f"(~{int(limit) * 2} min estimated)")
        # Fire-and-forget: don't block the bot poll loop
        subprocess.Popen(
            [sys.executable, str(VAULT_DIR / "skill_batch_runner.py"), "--limit", limit],
            cwd=str(VAULT_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return history

    handler = COMMANDS.get(first_word)
    if handler:
        # Instant command — no API, no history update
        handler(chat_id, history)
        return history

    # Free-text → LLM
    send(chat_id, "🧠 Thinking...")
    history = history + [{"role": "user", "content": text}]
    reply    = _call_llm(history)
    is_error = reply.startswith(("OpenRouter error", "Anthropic error", "⚠️"))
    if not is_error:
        history = history + [{"role": "assistant", "content": reply}]

    # Cap at MAX_HISTORY_TURNS pairs
    if len(history) > MAX_HISTORY_TURNS * 2:
        history = history[-(MAX_HISTORY_TURNS * 2):]

    send(chat_id, reply)
    return history


# ── Poll loop ─────────────────────────────────────────────────────────────
def main() -> None:
    print(f"Starting Antigravity Telegram bot (owner: {OWNER_ID})...")
    provider = f"OpenRouter ✓ ({TELEGRAM_MODEL})" if OPENROUTER_KEY else \
               ("Anthropic ✓ (claude-sonnet-4-6)" if ANTHROPIC_KEY else "✗ no key — free-text disabled")
    print(f"LLM: {provider}")
    print(f"System prompt: {len(SYSTEM_PROMPT)} chars loaded from CLAUDE.md + MEMORY.md")
    send(OWNER_ID,
         "🟢 Antigravity bot online (v3.1 — Full Claude Code)\n\n"
         "UPGRADED: /claude now has full context + session memory\n"
         "NEW: /claude_reset, /3d, /rag\n"
         "Free-text now powered by Claude Sonnet.\n"
         "Type /help for all commands.")
    print("Listening (Ctrl+C to stop)...")

    offset      = 0
    history: list = []

    # Pending edit state: review_id waiting for custom reply text
    # {chat_id: {"review_id": ..., "business_key": ..., "expires": unix_timestamp}}
    pending_edit: dict = {}

    while True:
        try:
            updates = get_updates(offset)
            for update in updates:
                offset = update["update_id"] + 1

                # ── Inline button callback ─────────────────────────────
                cb = update.get("callback_query")
                if cb:
                    answer_callback(cb["id"])
                    chat_id  = str(cb["from"]["id"])
                    cb_data  = cb.get("data", "")
                    if chat_id != OWNER_ID:
                        continue
                    if cb_data.startswith("gbp_"):
                        try:
                            import importlib.util, sys as _sys
                            watcher_path = str(EXECUTION_DIR / "gbp_review_watcher.py")
                            spec = importlib.util.spec_from_file_location("gbp_review_watcher", watcher_path)
                            watcher = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(watcher)
                            state = watcher.load_state()
                            watcher._load_locations_from_state(state)
                            # Track edit pending
                            if cb_data.startswith("gbp_edit|"):
                                parts = cb_data.split("|")
                                pending_edit[chat_id] = {
                                    "review_id":   parts[1],
                                    "business_key": parts[2],
                                    "expires":     time.time() + 600,  # 10-minute window
                                }
                            watcher.handle_callback(cb_data, state)
                        except Exception as e:
                            send(OWNER_ID, f"⚠️ Review action error: {e}")
                    continue

                # ── Regular message ────────────────────────────────────
                msg = update.get("message") or update.get("edited_message")
                if not msg:
                    continue
                chat_id = str(msg["chat"]["id"])
                text    = msg.get("text", "")
                if chat_id != OWNER_ID:
                    print(f"Ignored message from unknown chat_id: {chat_id}")
                    continue
                print(f"[{time.strftime('%H:%M:%S')}] {text!r}")

                # ── Check if waiting for edited review reply ───────────
                if chat_id in pending_edit:
                    if time.time() > pending_edit[chat_id].get("expires", 0):
                        pending_edit.pop(chat_id)  # expired — discard silently
                if chat_id in pending_edit and text and not text.startswith("/"):
                    edit_info = pending_edit.pop(chat_id)
                    try:
                        import importlib.util
                        watcher_path = str(EXECUTION_DIR / "gbp_review_watcher.py")
                        spec = importlib.util.spec_from_file_location("gbp_review_watcher", watcher_path)
                        watcher = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(watcher)
                        state = watcher.load_state()
                        watcher._load_locations_from_state(state)
                        # Override draft with user's custom text, then post
                        review_id    = edit_info["review_id"]
                        business_key = edit_info["business_key"]
                        rv = state.get("reviews", {}).get(review_id, {})
                        rv["draft"] = text  # use their edited text
                        watcher.handle_callback(f"gbp_post|{review_id}|{business_key}", state)
                    except Exception as e:
                        send(chat_id, f"⚠️ Could not post edited reply: {e}")
                    continue

                history = dispatch(chat_id, text, history)
        except KeyboardInterrupt:
            send(OWNER_ID, "🔴 Antigravity bot going offline.")
            print("\nBot stopped.")
            break
        except Exception as e:
            print(f"Poll error: {e}")
        time.sleep(1)


if __name__ == "__main__":
    main()
