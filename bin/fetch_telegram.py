"""Pull new reporter messages from the Telegram group and group them into news items.

Messages from the same reporter within `merge_window_minutes` are merged into one item
(text + photos + links). Items are only finalised once the reporter has been quiet for
that window, so a half-sent report is never processed.

Output: inbox/<item_id>/item.json (+ photo_N.jpg). Prints the new item ids.
"""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

URL_RE = re.compile(r"https?://\S+")


def text_of(m):
    return m.get("text") or m.get("caption") or ""


def links_of(m):
    out = []
    for ent_key in ("entities", "caption_entities"):
        for e in m.get(ent_key, []) or []:
            if e["type"] == "text_link":
                out.append(e["url"])
    out += URL_RE.findall(text_of(m))
    seen, res = set(), []
    for u in out:
        u = u.rstrip(").,।")
        if u not in seen:
            seen.add(u); res.append(u)
    return res


def epaper_button(cq, st):
    """E-paper buttons: ep:pub:<date> starts the publish workflow, ep:hold:<date> keeps it off the site."""
    data = cq.get("data", "")
    owner = str(st.get("owner_chat_id") or os.environ.get("OWNER_CHAT_ID", "")).strip()
    if not data.startswith("ep:") or str(cq["from"]["id"]) != owner:
        tg("answerCallbackQuery", callback_query_id=cq["id"]); return
    _, act, day = data.split(":", 2)
    msg = cq.get("message") or {}
    if act in ("pub", "re"):
        import urllib.request as ur
        r = ur.Request(f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/actions/workflows/epaper.yml/dispatches",
                       data=json.dumps({"ref": "main", "inputs": {"action": "publish" if act == "pub" else "rebuild", "day": day}}).encode(), method="POST",
                       headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"], "Accept": "application/vnd.github+json"})
        ur.urlopen(r, timeout=30).read()
        tg("answerCallbackQuery", callback_query_id=cq["id"], text="শুরু হয়েছে, কয়েক মিনিট লাগবে।")
        note = "⏳ সাইটে তোলা হচ্ছে… শেষ হলে জানানো হবে।" if act == "pub" else "🔄 নতুন নিউজসহ আবার বানানো হচ্ছে… তৈরি হলে নতুন PDF পাঠানো হবে।"
    else:
        tg("answerCallbackQuery", callback_query_id=cq["id"], text="ঠিক আছে, প্রকাশ আটকে রাখা হলো।")
        note = "⏸ এই সংখ্যা প্রকাশ হয়নি। কী ভুল আছে Claude-কে লিখে জানান।"
    if msg:
        tg("editMessageReplyMarkup", chat_id=msg["chat"]["id"], message_id=msg["message_id"], reply_markup={"inline_keyboard": []})
        tg("sendMessage", chat_id=msg["chat"]["id"], text=note, reply_to_message_id=msg["message_id"])


def epaper_timer():
    """Start the nightly e-paper build at 00:05 Dhaka (GitHub's own cron often runs an hour late).
    Stateless: does nothing if an e-paper run was already started since 00:04 Dhaka today."""
    import datetime as dt, urllib.request as ur
    now = dt.datetime.utcnow() + dt.timedelta(hours=6)
    if not (now.hour == 0 and now.minute >= 5 or 1 <= now.hour < 4) or not os.environ.get("GH_TOKEN"):
        return
    since = (now.replace(hour=0, minute=4, second=0, microsecond=0) - dt.timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")
    api = f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/actions/workflows/epaper.yml"
    h = {"Authorization": "Bearer " + os.environ["GH_TOKEN"], "Accept": "application/vnd.github+json"}
    runs = json.loads(ur.urlopen(ur.Request(f"{api}/runs?created=%3E%3D{since}&per_page=30", headers=h), timeout=30).read())
    if runs.get("total_count"):  # built already (cron, manual run or an earlier check)
        return
    ur.urlopen(ur.Request(f"{api}/dispatches", data=json.dumps({"ref": "main", "inputs": {"action": "build", "day": now.date().isoformat()}}).encode(),
                          method="POST", headers=h), timeout=30).read()
    log(f"epaper: nightly build started for {now.date()}")


def main():
    try: epaper_timer()
    except Exception as ex: print("epaper timer error", ex)
    cfg = config()
    sec = secrets()
    st = load_json(os.path.join(STATE, "telegram.json"), {"offset": 0, "pending": [], "groups": {}, "owner_chat_id": None, "reporters": {}})
    updates = tg("getUpdates", offset=st["offset"], timeout=0, allowed_updates=["message", "channel_post", "edited_message", "callback_query"])
    for u in updates:
        st["offset"] = u["update_id"] + 1
        if u.get("callback_query"):
            try: epaper_button(u["callback_query"], st)
            except Exception as ex: print("epaper button error", ex)
            continue
        m = u.get("message") or u.get("channel_post") or u.get("edited_message")
        if not m:
            continue
        chat = m["chat"]
        txt = text_of(m).strip()
        # Owner registration: private message "/owner <code>"
        if chat["type"] == "private":
            if txt.startswith("/owner") and txt.split()[-1] == str(sec.get("owner_code")):
                st["owner_chat_id"] = chat["id"]
                tg("sendMessage", chat_id=chat["id"], text="✅ আপনি সম্পাদক হিসেবে যুক্ত হলেন। কোনো খবরে তথ্যের সমস্যা থাকলে এখানে জানানো হবে।")
            elif txt.startswith("/start"):
                tg("sendMessage", chat_id=chat["id"], text="আমি বাংলার খবর-এর নিউজ বট। সংবাদ পাঠাতে প্রতিনিধিদের গ্রুপে পাঠান।")
            continue
        if chat["type"] not in ("group", "supergroup"):  # own public channel posts (e-paper etc.) are not submissions
            continue
        if txt.startswith("/"):
            continue
        st["groups"][str(chat["id"])] = chat.get("title", "")
        frm = m.get("from") or {}
        uid = str(frm.get("id", chat["id"]))
        name = " ".join(x for x in [frm.get("first_name"), frm.get("last_name")] if x) or chat.get("title", "")
        st["reporters"].setdefault(uid, {"telegram_name": name, "username": frm.get("username"), "byline": None, "area": None})
        photo_id = None
        if m.get("photo"):
            photo_id = max(m["photo"], key=lambda p: p.get("file_size", 0))["file_id"]
        elif (m.get("document") or {}).get("mime_type", "").startswith("image/"):
            photo_id = m["document"]["file_id"]
        st["pending"].append({
            "chat_id": chat["id"], "message_id": m["message_id"], "user_id": uid, "name": name,
            "date": m["date"], "text": txt, "links": links_of(m), "photo_id": photo_id,
            "has_video": bool(m.get("video")), "media_group_id": m.get("media_group_id"),
            "forward_from": (m.get("forward_origin") or {}).get("chat", {}).get("title") or
                            (m.get("forward_from_chat") or {}).get("title"),
            "edited": "edited_message" in u,
        })
    save_json(os.path.join(STATE, "telegram.json"), st)  # ack early so nothing is lost

    # Group pending messages: same chat + reporter, gap < window
    window = cfg.get("merge_window_minutes", 10) * 60
    now = time.time()
    pend = sorted(st["pending"], key=lambda p: (p["chat_id"], p["user_id"], p["date"]))
    groups, cur = [], []
    for p in pend:
        if cur and (p["chat_id"], p["user_id"]) == (cur[-1]["chat_id"], cur[-1]["user_id"]) and p["date"] - cur[-1]["date"] < window:
            cur.append(p)
        else:
            if cur: groups.append(cur)
            cur = [p]
    if cur: groups.append(cur)

    keep, new_ids = [], []
    for g in groups:
        if now - g[-1]["date"] < window:
            keep.extend(g)  # reporter may still be sending
            continue
        item_id = time.strftime("%Y%m%d-%H%M", time.gmtime(g[0]["date"])) + f"-{abs(g[0]['chat_id'])}-{g[0]['message_id']}"
        if not any(p["text"] or p["links"] or p["photo_id"] for p in g):
            continue  # service messages only (joins, pins, upgrades)
        d = os.path.join(INBOX, item_id)
        os.makedirs(d, exist_ok=True)
        photos, messages = [], []
        for p in g:
            fn = None
            if p["photo_id"]:
                fn = f"photo_{len(photos)+1}.jpg"
                try:
                    tg_download(p["photo_id"], os.path.join(d, fn))
                    photos.append(fn)
                except Exception as e:
                    log(f"photo download failed {item_id}: {e}"); fn = None
            messages.append({"time_utc": time.strftime("%H:%M:%S", time.gmtime(p["date"])), "message_id": p["message_id"],
                             "text": p["text"], "links": p["links"], "photo": fn,
                             "album": p["media_group_id"], "has_video": p["has_video"]})
        rep = st["reporters"].get(g[0]["user_id"], {})
        item = {
            "id": item_id, "chat_id": g[0]["chat_id"], "first_message_id": g[0]["message_id"],
            "reporter": {"user_id": g[0]["user_id"], "telegram_name": g[0]["name"],
                         "byline": rep.get("byline"), "area": rep.get("area")},
            "received_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(g[0]["date"])),
            "text": "\n\n".join(p["text"] for p in g if p["text"]),
            "links": [l for p in g for l in p["links"]],
            "photos": photos,
            "messages": messages,
            "has_video": any(p["has_video"] for p in g),
            "forwarded_from": sorted({p["forward_from"] for p in g if p["forward_from"]}),
            "status": "new",
        }
        if not item["text"] and not item["links"] and not photos:
            continue
        save_json(os.path.join(d, "item.json"), item)
        new_ids.append(item_id)
        if cfg.get("ack_reporters", True):
            try:
                tg("sendMessage", chat_id=g[0]["chat_id"], reply_to_message_id=g[0]["message_id"],
                   text="📥 সংবাদটি পাওয়া গেছে। যাচাই ও সম্পাদনার পর প্রকাশ হবে।", disable_notification=True)
            except Exception as e:
                log(f"ack failed: {e}")
    st["pending"] = keep
    save_json(os.path.join(STATE, "telegram.json"), st)
    if updates or new_ids: log(f"fetch: {len(updates)} updates, {len(new_ids)} new items, {len(keep)} msgs waiting")
    for i in new_ids:
        print("NEW", i)


if __name__ == "__main__":
    main()
