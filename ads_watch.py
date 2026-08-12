"""Meta ads watchdog — Juan José Elizondo (and any account added to ACCOUNTS).

WHY THIS EXISTS
    Mario: "I'm not gonna be wanting to keep track of it on my own... I cannot
    spend my day looking at this."

    A $10/day campaign nobody watches is worse than no campaign: it spends every
    single day and reports nothing. This is the thing that watches it.

    Modelled line-for-line on balance_watch.py (same folder) — stdlib only, no
    deps, threshold -> Telegram. Do not turn this into a dashboard.

THE ONE RULE THAT MATTERS MOST (R1)
    Meta will happily report "6 leads" while zero of them reached Juan's inbox.
    This stack has shipped exactly that failure twice:
      - 2026-08-04: Dalia said "Enviado a Juan Jose" while HTML5 validation
        silently blocked every submit.
      - api/contact.js:57-61 STILL returns HTTP 200 {ok:true, emailed:false}
        when SMTP credentials are missing.
    So R1 counts what Meta claims against what actually landed in Mario's inbox
    (he is CC'd on every lead) and screams when they disagree.

AUTHORITY
    The ONLY mutating call this script may ever make is POST /{ad_id}
    status=PAUSED. It can never raise a budget, change targeting, resume an ad,
    or create anything. Pausing is reversible; spending is not -- that asymmetry
    is the entire argument for letting it act at all.

    Pausing requires --arm. Default is dry-run.
    ...and EVERY alert states which mode it ran in, so "it silently stopped
    pausing" is impossible to miss.

RUN
    python ads_watch.py --discover     # list ad accounts the token can see
    python ads_watch.py                # evaluate, alert, DRY-RUN (no pausing)
    python ads_watch.py --arm          # evaluate, alert, and actually pause
    python ads_watch.py --quiet        # suppress the "all healthy" Telegram

SCHEDULED
    Windows Task Scheduler task "Antigravity-AdsWatch", every 4 hours.
    ~6 API calls per run against a 300/hour/account ceiling = 1/200th of budget.
"""
import argparse
import datetime as dt
import email.utils
import hashlib
import hmac
import imaplib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Emoji in status output dies on this box's cp1252 console (documented trap,
# hit 4x in this codebase). Never let a print kill the watchdog.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

EXEC_DIR = Path(__file__).resolve().parent
MEMORY = Path(r"C:\Users\mario\.claude\projects\C--Users-mario\memory")
VAULT = MEMORY / "api_keys_vault.md"
CREDS = EXEC_DIR / "fb_api_credentials.json"
STATE_FILE = EXEC_DIR / "ads_watch_state.json"
GRAVITY_ENV = Path("C:/Users/mario/.gemini/antigravity/scratch/gravity-claw/.env")

GRAPH = "https://graph.facebook.com/v21.0"

# ---------------------------------------------------------------------------
# CONFIG — the only part anyone should need to edit.
#
# ad_account_id is filled in after `--discover`. Until then the script says so
# loudly rather than reporting a healthy account it never looked at.
# ---------------------------------------------------------------------------
ACCOUNTS = [
    {
        "key": "juan_commercial",
        "label": "Juan — Naves (industrial, MX)",
        "ad_account_id": "",            # e.g. "act_123456789" — from --discover
        "daily_budget": 7.00,           # USD/day we intend to spend
        "target_cpl": 25.00,            # healthy cost per lead
        "lead_subject": "Nueva consulta",   # api/contact.js:64
        "lead_mailbox": "marioelizondo81@gmail.com",  # he is CC'd on every lead
    },
    {
        "key": "juan_residential",
        "label": "Juan — Residencial (HOUSING)",
        "ad_account_id": "",
        "daily_budget": 3.00,
        "target_cpl": None,             # weeks 1-2 buy pixel data, not leads
        "lead_subject": None,           # residential leads go to Supabase, not this inbox
        "lead_mailbox": None,
    },
]

# Rule thresholds. Changing these changes what the watchdog will PAUSE, so they
# live here in the open rather than buried in the rule bodies.
R2_MIN_IMPRESSIONS = 1000     # enough delivery to judge a creative
R2_MAX_CTR = 0.5              # percent
R3_CPL_MULTIPLE = 3.0         # pause at 3x target CPL...
R3_MIN_SPEND = 50.00          # ...but only once it has spent enough to be real
R4_SPEND_MULTIPLE = 1.5       # daily spend over 1.5x intended = someone changed something
ALERT_COOLDOWN_HOURS = 24     # re-fire a persisting problem daily, never go silent forever

# Meta account_status values worth naming in an alert.
ACCOUNT_STATUS = {
    1: "ACTIVE", 2: "DISABLED", 3: "UNSETTLED", 7: "PENDING_RISK_REVIEW",
    8: "PENDING_SETTLEMENT", 9: "IN_GRACE_PERIOD", 100: "PENDING_CLOSURE",
    101: "CLOSED", 201: "ANY_ACTIVE", 202: "ANY_CLOSED",
}
# effective_status values that mean "this ad is not running and nobody told you".
BAD_AD_STATUS = {"DISAPPROVED", "PENDING_BILLING_INFO", "WITH_ISSUES"}

# Meta reports leads under several action_type names depending on how the
# conversion was configured. Prefer the most specific website-pixel one.
LEAD_ACTION_TYPES = (
    "offsite_conversion.fb_pixel_lead",
    "onsite_conversion.lead_grouped",
    "lead",
)


# ---------------------------------------------------------------------------
# Plumbing (all of it copied in spirit from balance_watch.py)
# ---------------------------------------------------------------------------
def notify_mario(text: str) -> bool:
    """Telegram. Same env file and same shape as balance_watch.py."""
    try:
        env = {}
        for line in GRAVITY_ENV.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
        token, chat_id = env.get("TELEGRAM_BOT_TOKEN", ""), env.get("TELEGRAM_USER_ID", "")
        if not token or not chat_id:
            return False
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": text[:4096]}).encode()
        resp = urllib.request.urlopen(
            urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data),
            timeout=15,
        )
        return json.loads(resp.read()).get("ok", False)
    except Exception as e:
        print(f"[notify_mario FAILED] {type(e).__name__}: {e}")
        return False


def vault_key(pattern: str) -> str:
    """Pull a secret out of the memory vault by regex — never hardcode one here."""
    try:
        m = re.search(pattern, VAULT.read_text(encoding="utf-8", errors="replace"))
        return m.group(1) if (m and m.groups()) else (m.group(0) if m else "")
    except Exception:
        return ""


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state: dict) -> None:
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[state write FAILED] {e}")


def meta_get(path: str, params: dict) -> dict:
    """GET the Graph API with appsecret_proof. Raises on failure — callers must
    treat an exception as an ALARM, never as 'nothing to report'."""
    creds = json.loads(CREDS.read_text(encoding="utf-8"))
    tok, secret = creds["mario_user_token"], creds["app_secret"]
    proof = hmac.new(secret.encode(), tok.encode(), hashlib.sha256).hexdigest()
    q = dict(params)
    q["access_token"] = tok
    q["appsecret_proof"] = proof
    url = f"{GRAPH}{path}?{urllib.parse.urlencode(q)}"
    try:
        with urllib.request.urlopen(url, timeout=45) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"HTTP {e.code} on {path} :: {body}") from None


def meta_pause_ad(ad_id: str) -> bool:
    """The ONE mutating call this script is allowed to make. Nothing else."""
    creds = json.loads(CREDS.read_text(encoding="utf-8"))
    tok, secret = creds["mario_user_token"], creds["app_secret"]
    proof = hmac.new(secret.encode(), tok.encode(), hashlib.sha256).hexdigest()
    data = urllib.parse.urlencode(
        {"status": "PAUSED", "access_token": tok, "appsecret_proof": proof}
    ).encode()
    req = urllib.request.Request(f"{GRAPH}/{ad_id}", data=data, method="POST")
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r).get("success", True) is not False


# ---------------------------------------------------------------------------
# R1's ground truth: what actually landed in the inbox
# ---------------------------------------------------------------------------
def delivered_lead_count(mailbox: str, subject: str, since: dt.date) -> int | None:
    """Count real lead emails via IMAP.

    Returns None when it genuinely could not check. ⛔ None is NOT zero — the
    caller must report 'reconciliation unavailable', never 'reconciled OK'. A
    watchdog that reports success when its own instrument is broken is the exact
    bug this whole file exists to catch.
    """
    pwd = vault_key(r"Gmail App Password[^\n]*marioelizondo81[\s\S]{0,400}?\*\*App password:\*\*\s*`([^`]+)`")
    if not pwd:
        return None
    pwd = pwd.replace(" ", "")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", timeout=30)
        try:
            mail.login(mailbox, pwd)
            # Search ALL mail, not just INBOX — a filter could have moved it.
            mail.select('"[Gmail]/All Mail"', readonly=True)
            since_str = since.strftime("%d-%b-%Y")
            status, data = mail.search(None, "SINCE", since_str, "SUBJECT", f'"{subject}"')
            if status != "OK":
                return None
            return len(data[0].split())
        finally:
            try:
                mail.logout()
            except Exception:
                pass
    except Exception as e:
        print(f"[IMAP reconciliation unavailable] {type(e).__name__}: {e}")
        return None


# ---------------------------------------------------------------------------
# Insights helpers
# ---------------------------------------------------------------------------
def _lead_count(row: dict) -> int:
    for at in LEAD_ACTION_TYPES:
        for a in row.get("actions", []) or []:
            if a.get("action_type") == at:
                try:
                    return int(float(a.get("value", 0)))
                except (TypeError, ValueError):
                    return 0
    return 0


def _cpl(row: dict) -> float | None:
    for at in LEAD_ACTION_TYPES:
        for a in row.get("cost_per_action_type", []) or []:
            if a.get("action_type") == at:
                try:
                    return float(a.get("value"))
                except (TypeError, ValueError):
                    return None
    return None


def _f(row: dict, key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# The rules
# ---------------------------------------------------------------------------
def evaluate_account(acct: dict, state: dict, armed: bool) -> tuple[list, list, dict]:
    """Returns (alerts, pause_actions, snapshot). Every failure path appends an
    ALARM — none of them may return quietly."""
    alerts: list[str] = []
    pauses: list[dict] = []
    aid = acct["ad_account_id"]
    label = acct["label"]

    snapshot = {"label": label, "checked_at": dt.datetime.now().isoformat(timespec="seconds")}

    # --- R5a: is the account itself alive? -------------------------------
    try:
        info = meta_get(
            f"/{aid}",
            {"fields": "name,account_status,disable_reason,currency,amount_spent,spend_cap,balance"},
        )
        st = info.get("account_status")
        snapshot["account_status"] = ACCOUNT_STATUS.get(st, str(st))
        snapshot["currency"] = info.get("currency")
        if st != 1:
            alerts.append(
                f"🚨 R5 [{label}] ACCOUNT NOT ACTIVE — status "
                f"{ACCOUNT_STATUS.get(st, st)}"
                + (f", reason {info['disable_reason']}" if info.get("disable_reason") else "")
                + ". Nothing is delivering."
            )
    except Exception as e:
        alerts.append(f"🚨 [{label}] Could not read the ad account: {e}")
        snapshot["error"] = str(e)[:300]
        return alerts, pauses, snapshot  # no point continuing blind

    # --- Yesterday's per-ad insights -------------------------------------
    try:
        ins = meta_get(
            f"/{aid}/insights",
            {
                "level": "ad",
                "date_preset": "yesterday",
                "fields": "ad_id,ad_name,campaign_name,spend,impressions,clicks,ctr,cpc,cpm,"
                          "actions,cost_per_action_type",
                "limit": 200,
            },
        ).get("data", [])
    except Exception as e:
        alerts.append(f"🚨 [{label}] Insights call FAILED — the watchdog is blind: {e}")
        snapshot["error"] = str(e)[:300]
        return alerts, pauses, snapshot

    # --- Which ads are live, and are any disapproved? (R5b) --------------
    try:
        ads = meta_get(
            f"/{aid}/ads",
            {"fields": "id,name,effective_status", "limit": 200},
        ).get("data", [])
    except Exception as e:
        ads = []
        alerts.append(f"⚠️ [{label}] Could not read ad statuses (R5/R6 degraded): {e}")

    status_by_id = {a["id"]: a.get("effective_status", "?") for a in ads}
    # ⛔ Keep names in their own map. Reading a name out of status_by_id returns
    # "ACTIVE" for every ad, so the R6 alert names no one and is useless.
    name_by_id = {a["id"]: a.get("name") or a["id"] for a in ads}
    for a in ads:
        if a.get("effective_status") in BAD_AD_STATUS:
            alerts.append(
                f"🚨 R5 [{label}] Ad \"{a.get('name')}\" is {a['effective_status']} — "
                f"not delivering, and Meta did not tell you."
            )

    active_ids = {i for i, s in status_by_id.items() if s == "ACTIVE"}
    reported_ids = {r.get("ad_id") for r in ins}

    # --- R6: active but zero delivery ------------------------------------
    for ad_id in sorted(active_ids - reported_ids):
        alerts.append(
            f"🚨 R6 [{label}] Ad \"{name_by_id.get(ad_id, ad_id)}\" is ACTIVE but had "
            f"ZERO impressions yesterday. Zero delivery reads exactly like a quiet day."
        )

    # --- Per-ad rules R2 / R3 --------------------------------------------
    total_spend = 0.0
    total_leads = 0
    for row in ins:
        ad_id = row.get("ad_id")
        name = row.get("ad_name", ad_id)
        spend = _f(row, "spend")
        impr = _f(row, "impressions")
        ctr = _f(row, "ctr")
        leads = _lead_count(row)
        cpl = _cpl(row)
        total_spend += spend
        total_leads += leads

        # Never act on an ad that is already paused — idempotence.
        if status_by_id.get(ad_id) != "ACTIVE":
            continue

        if impr >= R2_MIN_IMPRESSIONS and leads == 0 and ctr < R2_MAX_CTR:
            pauses.append({
                "ad_id": ad_id, "name": name, "rule": "R2",
                "why": f"{int(impr):,} impressions, 0 leads, CTR {ctr:.2f}% "
                       f"(< {R2_MAX_CTR}%). The creative is dead.",
            })
        elif (
            acct.get("target_cpl")
            and cpl is not None
            and spend >= R3_MIN_SPEND
            and cpl > acct["target_cpl"] * R3_CPL_MULTIPLE
        ):
            pauses.append({
                "ad_id": ad_id, "name": name, "rule": "R3",
                "why": f"CPL ${cpl:.2f} is over {R3_CPL_MULTIPLE:g}x the ${acct['target_cpl']:.0f} "
                       f"target after ${spend:.2f} spent.",
            })

    snapshot["spend_yesterday"] = round(total_spend, 2)
    snapshot["leads_reported"] = total_leads
    snapshot["ads_active"] = len(active_ids)

    # --- R4: spend anomaly (alarm only — a human changed something) -------
    budget = acct.get("daily_budget") or 0
    if budget and total_spend > budget * R4_SPEND_MULTIPLE:
        alerts.append(
            f"🚨 R4 [{label}] Spent ${total_spend:.2f} yesterday against a ${budget:.2f}/day "
            f"budget ({total_spend / budget:.1f}x). The watchdog did not change this — "
            f"someone or something else did."
        )

    # --- R1: RECONCILIATION — the most important rule in the file ---------
    if acct.get("lead_subject") and acct.get("lead_mailbox"):
        yesterday = dt.date.today() - dt.timedelta(days=1)
        delivered = delivered_lead_count(acct["lead_mailbox"], acct["lead_subject"], yesterday)
        snapshot["leads_delivered"] = delivered
        if delivered is None:
            alerts.append(
                f"⚠️ R1 [{label}] RECONCILIATION UNAVAILABLE — could not read the inbox, so "
                f"'{total_leads} leads' from Meta is UNVERIFIED. This is not a pass."
            )
        elif delivered != total_leads:
            alerts.append(
                f"🚨 R1 [{label}] LEAD MISMATCH — Meta reports {total_leads} lead(s) yesterday, "
                f"but only {delivered} actually reached the inbox. You may be paying for leads "
                f"that never arrive. Check api/contact.js and the SMTP app password."
            )
    else:
        snapshot["leads_delivered"] = None

    return alerts, pauses, snapshot


# ---------------------------------------------------------------------------
def cmd_discover() -> int:
    """List every ad account the token can see. This is the gate for everything."""
    try:
        r = meta_get("/me/adaccounts", {
            "fields": "id,name,account_status,currency,amount_spent,spend_cap,business_name",
            "limit": 50,
        })
    except Exception as e:
        print(f"FAILED: {e}")
        print()
        print("If this says '(#200) Missing Permissions', the token still lacks")
        print("ads_read / ads_management. See Phase 0.1 of the plan — the fix is a")
        print("re-auth of app 3528802383934007, NOT a new app.")
        return 1
    accts = r.get("data", [])
    print(f"AD ACCOUNTS VISIBLE: {len(accts)}")
    for a in accts:
        print(f"  {a.get('id'):<22} {a.get('name')}")
        print(f"     status={ACCOUNT_STATUS.get(a.get('account_status'), a.get('account_status'))} "
              f"spent={a.get('amount_spent')} {a.get('currency')} biz={a.get('business_name')}")
    if not accts:
        print("  (none — the token authenticated but sees no ad accounts)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Meta ads watchdog")
    ap.add_argument("--discover", action="store_true", help="list visible ad accounts and exit")
    ap.add_argument("--arm", action="store_true",
                    help="ACTUALLY pause ads that trip R2/R3 (default: dry-run)")
    ap.add_argument("--quiet", action="store_true", help="no Telegram when everything is healthy")
    args = ap.parse_args()

    if args.discover:
        return cmd_discover()

    mode = "ARMED" if args.arm else "DRY-RUN"
    state = load_state()
    now = dt.datetime.now()

    configured = [a for a in ACCOUNTS if a.get("ad_account_id")]
    if not configured:
        # ⛔ Never let "nothing configured" look like "everything is fine".
        msg = ("⚠️ ADS WATCH could not run: no ad_account_id is set in ACCOUNTS.\n"
               "Run `python ads_watch.py --discover` once the token has ads_read.")
        print(msg)
        notify_mario(msg)
        return 2

    all_alerts: list[str] = []
    all_pauses: list[dict] = []
    snapshots = {}

    for acct in configured:
        alerts, pauses, snap = evaluate_account(acct, state, args.arm)
        all_alerts.extend(alerts)
        all_pauses.extend(pauses)
        snapshots[acct["key"]] = snap

    # --- act on pauses ----------------------------------------------------
    pause_lines = []
    for p in all_pauses:
        if args.arm:
            try:
                ok = meta_pause_ad(p["ad_id"])
                pause_lines.append(
                    f"⏸️ PAUSED [{p['rule']}] \"{p['name']}\" — {p['why']}"
                    + ("" if ok else "  (Meta did not confirm!)")
                )
            except Exception as e:
                pause_lines.append(f"🚨 FAILED to pause \"{p['name']}\" ({p['rule']}): {e}")
        else:
            pause_lines.append(f"🔎 WOULD PAUSE [{p['rule']}] \"{p['name']}\" — {p['why']}")

    # --- dedup: same problem shouldn't shout every 4h, but must not go quiet
    seen = state.get("alert_seen", {})
    fresh = []
    for a in all_alerts:
        key = hashlib.sha256(a.encode("utf-8")).hexdigest()[:16]
        last = seen.get(key)
        if last:
            try:
                age_h = (now - dt.datetime.fromisoformat(last)).total_seconds() / 3600
                if age_h < ALERT_COOLDOWN_HOURS:
                    continue
            except Exception:
                pass
        seen[key] = now.isoformat(timespec="seconds")
        fresh.append(a)

    state["alert_seen"] = seen
    state["last_run"] = now.isoformat(timespec="seconds")
    state["last_mode"] = mode
    state["snapshots"] = snapshots
    save_state(state)

    # --- report -----------------------------------------------------------
    summary = " | ".join(
        f"{s['label']}: ${s.get('spend_yesterday', 0):.2f}, "
        f"{s.get('leads_reported', 0)} leads"
        + (f" ({s['leads_delivered']} delivered)" if s.get("leads_delivered") is not None else "")
        for s in snapshots.values()
    )
    print(f"[{mode}] {summary}")
    for line in fresh + pause_lines:
        print("  " + line)

    body = fresh + pause_lines
    if body:
        notify_mario(f"📊 ADS WATCH [{mode}]\n" + "\n".join(body) + f"\n\n({summary})")
    elif not args.quiet:
        notify_mario(f"📊 ADS WATCH [{mode}] — all healthy.\n{summary}")
    else:
        print("healthy — no alert sent (--quiet)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
