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
        me = tg("getMe")["username"]
        n = len(wp_publish.wp("/posts", params={"per_page": 1, "_fields": "id"}))
        print(f"TEST OK telegram=@{me} wordpress_posts_visible={n}"); return
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
