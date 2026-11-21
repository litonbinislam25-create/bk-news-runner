"""Claude's only jobs (owner 2026-11-21), run at 10:00 and 18:00 Dhaka:
  python3 bin/claude_tasks.py list            -> queued drafts + new posts to proof-read; prints NOTHING if none
  python3 bin/claude_tasks.py finish <id> a.json   -> publish a queued draft (a.json = one article dict, RUN.md)
  python3 bin/claude_tasks.py drop <id> skip|reject "<reason>"
  python3 bin/claude_tasks.py fix <id> fixes.json  -> [[old, new], ...] small language fixes in the body
  python3 bin/claude_tasks.py reviewed        -> mark proof-reading done up to now
"""
import os, sys, re, json, html, datetime, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import wp_publish
from wp_publish import wp, QUEUE_MARK

LAST = os.path.join(STATE, "last_review.txt")


def queued():
    out = []
    for p in wp("/posts", params={"status": "draft", "per_page": 50, "context": "edit", "_fields": "id,title,content"}):
        raw = p["content"]["raw"]
        if raw.startswith(QUEUE_MARK):
            out.append((p, json.loads(raw[len(QUEUE_MARK):raw.index(" -->")])))
    return out


def plain(h):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h))).strip()


def cmd_list():
    any_ = False
    for p, m in queued():
        any_ = True
        print(f"## QUEUED {p['id']} | {m['reason']} | প্রতিনিধি: {m['item']['reporter'].get('telegram_name')}")
        print("\n".join(m["lines"]))
        for l in m["links"]:
            print("LINK", l)
        for x in m["media"]:
            print("PHOTO", x["url"])
        if m.get("draft_art"):
            print("CODE-DRAFT title:", m["draft_art"]["title"], "| cats:", m["draft_art"]["categories"],
                  "| byline:", m["draft_art"]["reporter_name"])
    since = (open(LAST).read().strip() if os.path.exists(LAST) else
             (datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%SZ"))
    posts = wp("/posts", params={"after": since, "per_page": 30, "status": "publish", "context": "edit",
                                 "_fields": "id,title,content,meta"})
    for p in posts:
        txt = plain(p["content"]["raw"].split("আরও পড়ুন")[0].split("🩸")[0])
        any_ = True
        print(f"## REVIEW {p['id']} | {html.unescape(p['title']['raw'])}\n{txt}")
    if not any_:
        print("NOTHING")


def load_q(pid):
    for p, m in queued():
        if p["id"] == int(pid):
            return p, m
    raise SystemExit(f"{pid} queued draft নয়")


def cmd_finish(pid, path):
    p, m = load_q(pid)
    art = load_json(path)
    art["_post_id"] = int(pid)
    art.setdefault("decision", "publish")
    art.setdefault("reply_to_message_id", m.get("msg"))
    d = tempfile.mkdtemp()
    files = {x["file"]: x["url"] for x in m["media"]}
    fp = art.get("featured_photo")
    if fp and not str(fp).startswith("http"):
        art["featured_photo"] = files.get(fp)  # URL -> publish_one downloads it
    bp = []
    for fn in art.get("body_photos", []):
        url = files.get(fn, fn)
        if not str(url).startswith("http"):
            continue
        local = os.path.join(d, os.path.basename(url.split("?")[0]))
        open(local, "wb").write(http(url, headers={"User-Agent": "Mozilla/5.0"}, raw=True, timeout=60))
        bp.append(os.path.basename(local))
    art["body_photos"] = bp
    item = dict(m["item"]); item.setdefault("messages", [])
    r = wp_publish.publish_one(d, item, art, config())
    photo = None
    if str(art.get("featured_photo") or "").startswith("http"):
        cands = [f for f in os.listdir(d) if f.startswith("src_") and not f.endswith(("_16x9.jpg", "_blur.jpg"))]
        photo = os.path.join(d, cands[0]) if cands else None
    wp_publish.notify(item, art, r, photo)
    print(r["status"], r.get("link") or r.get("edit_url"))


def cmd_drop(pid, kind, reason=""):
    p, m = load_q(pid)
    wp(f"/posts/{pid}", {"title": ("✖ " if kind == "skip" else "⛔ ") + html.unescape(p["title"]["raw"]).lstrip("⏳ "),
                         "content": "<p>" + html.escape(reason) + "</p>" + p["content"]["raw"].split(" -->", 1)[1]}, "POST")
    if kind == "reject":
        wp_publish.notify(m["item"], {}, {"status": "rejected", "reject_reason": reason}, None)
    print("dropped", pid)


def cmd_fix(pid, path):
    p = wp(f"/posts/{pid}", params={"context": "edit", "_fields": "content"})
    body = p["content"]["raw"]
    n = 0
    for old, new in load_json(path):
        if old in body:
            body = body.replace(old, new, 1); n += 1
    wp(f"/posts/{pid}", {"content": body}, "POST")
    print(f"fixed {n} in {pid}")


def cmd_reviewed():
    os.makedirs(STATE, exist_ok=True)
    open(LAST, "w").write(datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%SZ"))


if __name__ == "__main__":
    a = sys.argv[1:]
    {"list": lambda: cmd_list(), "finish": lambda: cmd_finish(a[1], a[2]), "drop": lambda: cmd_drop(*a[1:4]),
     "fix": lambda: cmd_fix(a[1], a[2]), "reviewed": lambda: cmd_reviewed()}[a[0]]()
