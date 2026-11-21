"""One run (GitHub Actions, every 5 min): Telegram -> articles (code only) -> WordPress. No AI.
Stories code can't finish are parked as WordPress drafts for Claude (claude_tasks.py)."""
import os, sys, glob, time, shutil, html, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import fetch_telegram, auto_build, wp_publish

N = lambda s: unicodedata.normalize("NFC", html.unescape(s or "")).strip()


def recent_titles():
    import datetime
    after = (datetime.datetime.utcnow() - datetime.timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        return {N(p["title"]["rendered"]) for p in wp_publish.wp("/posts", params={
            "after": after, "per_page": 100, "_fields": "title", "status": "publish"})}
    except Exception as e:
        log(f"dup check failed: {e}"); return set()


def main():
    if os.environ.get("FORCE_DRAFT") == "1":  # connection test only: never touches Telegram updates
        import re as _re
        for k in ("TELEGRAM_BOT_TOKEN", "WP_USER", "WP_APP_PASSWORD", "OWNER_CHAT_ID"):
            v = os.environ.get(k, "")
            print(f"{k}: set={bool(v.strip())} length={len(v.strip())} spaces={v.strip().count(' ')}")
        tokv = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        print("TELEGRAM_BOT_TOKEN looks like a bot token:", bool(_re.fullmatch(r"\d{6,12}:[A-Za-z0-9_-]{30,}", tokv)))
        try:
            print("TELEGRAM OK @" + tg("getMe")["username"])
        except Exception as e:
            print("TELEGRAM FAIL", type(e).__name__, str(e)[:80].replace(tokv, "***") if tokv else str(e)[:80])
        try:
            me = wp_publish.wp("/users/me", params={"context": "edit", "_fields": "slug,roles"})
            print("WORDPRESS OK roles=", me.get("roles"))
        except Exception as e:
            print("WORDPRESS FAIL", str(e)[:160])
            import base64, urllib.request, urllib.error
            u = config()["site_url"].rstrip("/") + "/wp-json/wp/v2/users/me"
            for label, pw in (("wrong-password probe", "xxxx"), ("real", os.environ.get("WP_APP_PASSWORD", ""))):
                tok = base64.b64encode(f"{os.environ.get('WP_USER','').strip()}:{pw.strip()}".encode()).decode()
                for hdr in ("Authorization", "X-Authorization"):
                    req = urllib.request.Request(u + "?_fields=slug", headers={hdr: "Basic " + tok, "User-Agent": "Mozilla/5.0 (BanglarKhabor Desk)"})
                    try:
                        print(label, hdr, "->", urllib.request.urlopen(req, timeout=30).read()[:80])
                    except urllib.error.HTTPError as h:
                        print(label, hdr, "->", h.code, h.read()[:120], "server=", h.headers.get("server"))
        return
    if not config().get("runner_enabled"):
        print("runner_enabled is false in config.json (switch-over not done yet)"); return
    st_path = os.path.join(STATE, "telegram.json")
    st = load_json(st_path, None)
    if st is None or not st.get("owner_chat_id"):
        st = st or {"offset": 0, "pending": [], "groups": {}, "owner_chat_id": None, "reporters": {}}
        st["owner_chat_id"] = secrets().get("owner_chat_id") or os.environ.get("OWNER_CHAT_ID")
        save_json(st_path, st)
    fetch_telegram.main()
    items = sorted(glob.glob(os.path.join(INBOX, "*", "item.json")))
    titles = recent_titles() if items else set()
    for f in items:
        d = os.path.dirname(f)
        item = load_json(f)
        if item.get("status") not in ("new", "error"):
            continue
        item["attempts"] = item.get("attempts", 0) + 1
        save_json(f, item)
        if item["status"] == "new":
            arts = auto_build.main(d)
            for a in arts:
                if a.get("decision") == "publish" and N(a["title"]) in titles:
                    a["decision"] = "skip"; log(f"duplicate skipped {item['id']}: {a['title']}")
            save_json(os.path.join(d, "articles.json"), arts)
        wp_publish.main(d)
        item = load_json(f) if os.path.exists(f) else None
        if item and item.get("status") == "error" and item["attempts"] >= 12:
            item["status"] = "failed"; save_json(f, item)
            log(f"gave up {item['id']} after 12 tries")
    # keep the cache small: done/ keeps only json for 3 days, log keeps 3000 lines
    for dd in glob.glob(os.path.join(DONE, "*")):
        for x in glob.glob(os.path.join(dd, "*.jpg")) + glob.glob(os.path.join(dd, "*.png")):
            os.remove(x)
        if time.time() - os.path.getmtime(dd) > 3 * 86400:
            shutil.rmtree(dd, ignore_errors=True)
    lp = os.path.join(LOGS, "run.log")
    if os.path.exists(lp):
        lines = open(lp, encoding="utf-8").read().splitlines()[-3000:]
        open(lp, "w", encoding="utf-8").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
