"""Shared helpers for the বাংলার খবর news autopilot (stdlib only)."""
import json, os, time, urllib.request, urllib.parse, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "state")
INBOX = os.path.join(ROOT, "inbox")
DONE = os.path.join(ROOT, "done")
LOGS = os.path.join(ROOT, "logs")


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def config():
    c = load_json(os.path.join(ROOT, "config.json"), {})
    if os.environ.get("FORCE_DRAFT") == "1":  # test runs: everything stays a draft, nobody is messaged
        c["force_draft"] = True
    return c


def secrets():
    s = load_json(os.path.join(ROOT, "secrets.json"))
    if not s and os.environ.get("BOT_SECRETS"):  # GitHub Actions: one JSON secret
        raw = os.environ["BOT_SECRETS"].strip().lstrip("\ufeff").strip()
        if "{" in raw:
            raw = raw[raw.index("{"):raw.rindex("}") + 1]
        try:
            s = json.loads(raw)
        except ValueError:  # safe hint only, never the value itself
            raise SystemExit(f"BOT_SECRETS is not JSON: length={len(raw)}, has_brace={'{' in raw}, "
                             f"has_token_key={'telegram_bot_token' in raw}")
    if not s:
        raise SystemExit("secrets.json নেই — সেটআপ বাকি।")
    return s


def log(msg):
    os.makedirs(LOGS, exist_ok=True)
    line = f"{datetime.datetime.utcnow().isoformat(timespec='seconds')}Z {msg}"
    print(line)
    with open(os.path.join(LOGS, "run.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def http(url, data=None, headers=None, method=None, timeout=60, raw=False):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
    return body if raw else json.loads(body.decode("utf-8"))


def tg(method, **params):
    tok = secrets()["telegram_bot_token"]
    data = urllib.parse.urlencode({k: (json.dumps(v) if isinstance(v, (dict, list)) else v)
                                   for k, v in params.items() if v is not None}).encode()
    res = http(f"https://api.telegram.org/bot{tok}/{method}", data=data)
    if not res.get("ok"):
        raise RuntimeError(f"Telegram {method}: {res}")
    return res["result"]


def tg_download(file_id, dest):
    tok = secrets()["telegram_bot_token"]
    info = tg("getFile", file_id=file_id)
    blob = http(f"https://api.telegram.org/file/bot{tok}/{info['file_path']}", raw=True, timeout=120)
    with open(dest, "wb") as f:
        f.write(blob)
    return dest


BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
BN_MONTHS = ["জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন", "জুলাই",
             "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর"]


def bn_date(dt):
    return f"{str(dt.day).translate(BN_DIGITS)} {BN_MONTHS[dt.month-1]} {str(dt.year).translate(BN_DIGITS)}"


def local_now():
    off = config().get("timezone_offset_hours", 6)
    return datetime.datetime.utcnow() + datetime.timedelta(hours=off)
