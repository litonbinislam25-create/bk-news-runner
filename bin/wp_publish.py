"""Send one processed item to WordPress (draft by default) and tell the editor on Telegram.

Usage: python3 bin/wp_publish.py inbox/<item_id>
Needs article.json (written by Claude) and card-wide.jpg / card-square.png (bin/photocard.js).
"""
import base64, datetime, re, time, unicodedata, json, mimetypes, os, shutil, sys, uuid, urllib.error, urllib.parse, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *


def wp_base():
    url = (config().get("site_url") or "").rstrip("/")
    if not url:
        raise SystemExit("config.json-এ site_url নেই।")
    return url + "/wp-json/wp/v2"


def auth():
    s = secrets()
    tok = base64.b64encode(f"{s['wp_user']}:{s['wp_app_password']}".encode()).decode()
    return {"Authorization": "Basic " + tok, "User-Agent": "BanglarKhoborNewsBot/1.0"}


def wp(path, body=None, method=None, params=None, _try=0):
    url = wp_base() + path + ("?" + urllib.parse.urlencode(params) if params else "")
    h = auth()
    data = None
    if body is not None:
        data = json.dumps(body).encode(); h["Content-Type"] = "application/json"
    try:
        return http(url, data=data, headers=h, method=method)
    except urllib.error.HTTPError as e:
        if e.code in (502, 503, 504, 429) and _try < 3:
            time.sleep(5 * (_try + 1))
            return wp(path, body, method, params, _try + 1)
        raise RuntimeError(f"WP {path} {e.code}: {e.read().decode('utf-8', 'replace')[:400]}")
    except (urllib.error.URLError, ConnectionError, TimeoutError) as e:  # network blip (connection reset)
        if _try < 3 and (method in (None, "GET") or not path.startswith("/posts") or body is None or "status" not in (body or {})):
            time.sleep(5 * (_try + 1))
            return wp(path, body, method, params, _try + 1)
        raise


def to_16x9(path, w=1280, h=720, focus_y=None):
    """OWNER RULE: every image on the site is 16:9. Landscape-ish photos are cropped (slightly
    top-biased so heads stay in); portrait photos are cover-cropped (top-biased); only ultra-wide panoramas go on blur."""
    from PIL import Image, ImageFilter, ImageOps
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    r = im.width / im.height
    if r <= 2.3:  # owner 2026-11-20: portrait photos are cover-cropped too (no small photo on blur)
        if r > 16 / 9:  # too wide: crop sides
            nw = round(im.height * 16 / 9); x = (im.width - nw) // 2
            im = im.crop((x, 0, x + nw, im.height))
        else:  # too tall: crop, keep more of the top
            nh = round(im.width * 9 / 16)
            fy = focus_y if focus_y is not None else (0.45 if r >= 1 else 0.38)  # centre of the crop (0=top, 1=bottom)
            y = max(0, min(im.height - nh, int(fy * im.height - nh / 2)))
            im = im.crop((0, y, im.width, y + nh))
        out = im.resize((w, h), Image.LANCZOS)
    else:
        bg = ImageOps.fit(im, (w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(28))
        bg = Image.blend(bg, Image.new("RGB", (w, h), (0, 0, 0)), 0.25)
        fg = im.copy(); fg.thumbnail((w, h), Image.LANCZOS)
        bg.paste(fg, ((w - fg.width) // 2, (h - fg.height) // 2))
        out = bg
    dst = os.path.splitext(path)[0] + "_16x9.jpg"
    out.save(dst, "JPEG", quality=88, optimize=True, progressive=True)
    return dst


def blur_regions(path, boxes):
    """OWNER RULE 2026-11-20: blood, wounds, bodies and violence are blurred, not dropped.
    boxes = [[x0,y0,x1,y1], ...] as fractions of width/height; [[0,0,1,1]] blurs everything."""
    from PIL import Image, ImageFilter, ImageOps
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    W, H = im.size
    for b in boxes:
        x0, y0, x1, y1 = [int(v * (W if i % 2 == 0 else H)) for i, v in enumerate(b)]
        reg = im.crop((x0, y0, x1, y1)).filter(ImageFilter.GaussianBlur(max(10, (x1 - x0) // 30)))
        im.paste(reg, (x0, y0))
    dst = os.path.splitext(path)[0] + "_blur.jpg"
    im.save(dst, "JPEG", quality=90)
    return dst


def upload(path, alt="", caption="", focus_y=None, blur=None):
    if blur:
        path = blur_regions(path, blur)
    path = to_16x9(path, focus_y=focus_y)
    h = auth()
    h["Content-Type"] = mimetypes.guess_type(path)[0] or "image/jpeg"
    h["Content-Disposition"] = f'attachment; filename="{os.path.basename(path)}"'
    with open(path, "rb") as f:
        try:
            m = http(wp_base() + "/media", data=f.read(), headers=h, method="POST", timeout=180)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"WP media {e.code}: {e.read().decode('utf-8', 'replace')[:400]}")
    if alt or caption:
        wp(f"/media/{m['id']}", {"alt_text": alt, "caption": caption}, "POST")
    return m


def term_id(kind, name):
    for t in wp(f"/{kind}", params={"search": name, "per_page": 50}):
        if html.unescape(t["name"]).strip() == name.strip():
            return t["id"]
    try:
        return wp(f"/{kind}", {"name": name}, "POST")["id"]
    except RuntimeError as e:
        if "term_exists" in str(e):
            return json.loads(str(e).split(": ", 1)[1]).get("data", {}).get("term_id")
        raise


def next_slot():
    """For auto mode: next free publish time, >= min_gap after the last one, within day hours, <= max/day."""
    cfg = config(); sc = cfg["schedule"]; off = datetime.timedelta(hours=cfg.get("timezone_offset_hours", 6))
    st = load_json(os.path.join(STATE, "schedule.json"), {"slots": []})
    now = datetime.datetime.utcnow() + off
    slots = [datetime.datetime.fromisoformat(s) for s in st["slots"]]
    t = max([now + datetime.timedelta(minutes=5)] + [s + datetime.timedelta(minutes=sc["min_gap_minutes"]) for s in slots])
    while True:
        if t.hour < sc["day_start_hour"]:
            t = t.replace(hour=sc["day_start_hour"], minute=0)
        if t.hour >= sc["day_end_hour"]:
            t = (t + datetime.timedelta(days=1)).replace(hour=sc["day_start_hour"], minute=0); continue
        if sum(1 for s in slots if s.date() == t.date()) >= sc["max_posts_per_day"]:
            t = (t + datetime.timedelta(days=1)).replace(hour=sc["day_start_hour"], minute=0); continue
        break
    st["slots"] = [s.isoformat() for s in slots if s > now - datetime.timedelta(days=2)] + [t.isoformat()]
    save_json(os.path.join(STATE, "schedule.json"), st)
    return t


def tg_send_photo(chat_id, photo_path, caption):
    tok = secrets()["telegram_bot_token"]
    b = uuid.uuid4().hex
    parts = []
    for k, v in (("chat_id", str(chat_id)), ("caption", caption), ("parse_mode", "HTML")):
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    with open(photo_path, "rb") as f:
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="photo"; filename="photo.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'.encode() + f.read() + b"\r\n")
    parts.append(f"--{b}--\r\n".encode())
    http(f"https://api.telegram.org/bot{tok}/sendPhoto", data=b"".join(parts),
         headers={"Content-Type": f"multipart/form-data; boundary={b}"}, timeout=120)


ACF_REPORTER_KEY = "field_6a7b083335fd4"   # ACF "প্রতিনিধির নাম" select (meta news_reporter)
ACF_DESK = "প্রতিনিধি নেই / ডেস্ক নিউজ"


def acf_reporter(art):
    """Pick the option of the site's ACF reporter list (used by the monthly reporter report)."""
    opts = load_json(os.path.join(STATE, "reporter_options.json"), [])
    if art.get("acf_reporter") in opts:
        return art["acf_reporter"]
    if art.get("source_type") == "website" or (not art.get("reporter_name") and (
            str(art.get("featured_photo") or "").startswith("http") or any((x or {}).get("url") for x in art.get("sources", [])))):
        return ACF_DESK
    name = (art.get("reporter_name") or "").strip()
    N = lambda x: unicodedata.normalize("NFC", x).replace(" ", "")
    for o in opts:
        if name and (N(o) == N(name) or N(name) in N(o) or N(o.split("-")[0]) in N(name)):
            return o
    # no personal option: use the area ("লাখাই প্রতিনিধি") from the categories / dateline
    lede = re.sub("<[^>]+>", "", art.get("body_html", ""))[:80]
    for area in list(art.get("categories", [])) + [lede]:
        for o in opts:
            if o.endswith("প্রতিনিধি") and len(o.split()) == 2 and o.split()[0] in area:
                return o
    return "মাধবপুর প্রতিনিধি"


def short_paragraphs(body):
    """OWNER STYLE (2026-11-20): keep the writer's full paragraphs (3-5 sentences each), no subheads.
    Bold dateline on its own line, like the hand-written posts."""
    body = re.sub(r"<h[2-6][^>]*>.*?</h[2-6]>\s*", "", body, flags=re.S)
    body = re.sub(r"^\s*<p>\s*(<strong>[^<]{2,60}:</strong>)\s*", r"<p>\1</p><p>", body, count=1)
    return body


BLOOD_LINE = ('<p><strong>🩸 <a href="https://banglarkhabor24.com/blood-donation-organizations">'
              'রক্তদাতা খুঁজতে এবং রক্তদাতা হিসেবে যুক্ত হতে এই লিঙ্কে ক্লিক করুন</a></strong></p>')  # owner rule 2026-11-20


def related_link(cats, tags, exclude_title):
    """One recent post of ours on the same topic, for Yoast's internal-link check ('আরও পড়ুন')."""
    for params in ([{"tags": ",".join(map(str, tags[:3]))}] if tags else []) + ([{"categories": cats[0]}] if cats else []):
        try:
            for q in wp("/posts", params={**params, "per_page": 5, "_fields": "id,link,title"}):
                t = html.unescape(q["title"]["rendered"])
                if t.strip() != exclude_title.strip():
                    return q["link"], t
        except Exception:
            pass
    return None


def publish_one(d, item, art, cfg):
    """Publish one article dict. Returns a result dict (status, post_id, edit_url...)."""
    if art.get("decision") == "queue":
        return queue_one(d, item, art)
    if art.get("decision") == "skip":
        log(f"skipped (not news) {item['id']}")
        return {"status": "skipped", "title": art.get("title", "")}
    if art.get("decision") == "reject":
        log(f"rejected {item['id']}: {art.get('reject_reason')}")
        return {"status": "rejected", "title": art.get("title", ""), "reject_reason": art.get("reject_reason")}

    N = lambda s: unicodedata.normalize("NFD", s or "").strip()  # য় can be written two ways
    site_cats = {N(c["name"]): c["id"] for c in load_json(os.path.join(STATE, "site_categories.json"), [])}
    names = art.get("categories") or ([art["category"]] if art.get("category") else [])
    cats = [site_cats[N(n)] for n in names if N(n) in site_cats] or [site_cats.get(N(cfg.get("default_category")))]
    cats = [c for c in cats if c]
    # OWNER RULE (2026-11-19): lead section = category "লিড নিউজ". Always lead: reporter news and anything
    # about Habiganj district; also any story the editor marks "lead": true (important national news).
    HABIGANJ = {N(x) for x in ("হবিগঞ্জ", "হবিগঞ্জ সদর", "মাধবপুর", "চুনারুঘাট", "বাহুবল", "নবীগঞ্জ",
                                "বানিয়াচং", "আজমিরীগঞ্জ", "লাখাই", "শায়েস্তাগঞ্জ")}
    is_lead = (art.get("lead") is True or art.get("source_type") == "reporter"
               or any(N(n) in HABIGANJ for n in names)
               or "হবিগঞ্জ" in (art.get("title", "") + art.get("body_html", "")[:600]))
    lead_id = site_cats.get(N("লিড নিউজ"))
    if art.get("lead") is not False and is_lead and lead_id and lead_id not in cats:
        cats.insert(0, lead_id)
    tags = [term_id("tags", t) for t in art.get("tags", [])][:10]

    # The site's own photocard plugin makes the card; we only set the best reporter photo as featured image.
    feat_file = art.get("featured_photo")
    if feat_file and feat_file.startswith("http"):  # photo from the source news site
        local = f"src_{abs(hash(feat_file)) % 10**8}.jpg"
        blob = http(feat_file, headers={"User-Agent": "Mozilla/5.0"}, raw=True, timeout=60)
        with open(os.path.join(d, local), "wb") as fh:
            fh.write(blob)
        feat_file = local
    featured = upload(os.path.join(d, feat_file), alt=art.get("photo_alt") or art["title"],
                      caption=art.get("featured_caption", ""), focus_y=art.get("photo_focus_y"), blur=art.get("blur_boxes")) if feat_file else None
    body = art["body_html"]
    for fn in art.get("body_photos", []):
        m = upload(os.path.join(d, fn), alt=art.get("photo_alt", art["title"]), caption=art.get("photo_caption", ""))
        fig = f'<figure class="wp-block-image size-large"><img src="{m["source_url"]}" alt="{html.escape(art.get("photo_alt", art["title"]))}"/>' \
              + (f'<figcaption>{html.escape(art.get("photo_caption", ""))}</figcaption>' if art.get("photo_caption") else "") + "</figure>"
        i = body.find("</p>")
        body = body[:i+4] + fig + body[i+4:] if i >= 0 else fig + body

    body = short_paragraphs(body)
    rel = related_link(cats, tags, art["title"])
    if rel and rel[0] not in body:
        more = f'<p><strong>আরও পড়ুন:</strong> <a href="{rel[0]}">{html.escape(rel[1])}</a></p>'
        body = body + more  # owner: related link at the end, never inside the text
    body += BLOOD_LINE
    post = {"title": art["title"], "content": body, "excerpt": art.get("excerpt", ""),
            "slug": art.get("focus_keyword") or art.get("slug"), "categories": cats, "tags": tags, "status": "draft"}
    if featured:
        post["featured_media"] = featured["id"]
    risky = art.get("risk") in ("medium", "high") or art.get("needs_editor")
    if cfg.get("mode") == "publish" and not risky:
        post["status"] = "publish"
    elif cfg.get("mode") == "auto" and not risky:
        t = next_slot()
        post["status"] = "future"; post["date"] = t.isoformat(timespec="seconds")
    seo = {k: v for k, v in {
        "rank_math_description": art.get("meta_description"), "rank_math_focus_keyword": art.get("focus_keyword"),
        "_yoast_wpseo_metadesc": art.get("meta_description"), "_yoast_wpseo_focuskw": art.get("focus_keyword"),
        "_yoast_wpseo_title": "%%title%%",  # site name not appended -> title fits Google's width
        "news_reporter": acf_reporter(art), "_news_reporter": ACF_REPORTER_KEY,
    }.items() if v}
    path = f"/posts/{art['_post_id']}" if art.get("_post_id") else "/posts"  # finish a queued draft in place
    if cfg.get("force_draft"):
        post["status"] = "draft"
    try:
        p = wp(path, {**post, "meta": seo}, "POST")
    except RuntimeError as e:
        log(f"retry without SEO meta: {e}")
        p = wp(path, post, "POST")
    # Byline: reporter's name; reporter news without a name -> "মাধবপুর প্রতিনিধি";
    # website news -> empty (theme shows "বাংলার খবর ডেস্ক").
    if not art.get("reporter_name") and (art.get("source_type") or ("website" if str(art.get("featured_photo") or "").startswith("http") else "reporter")) == "reporter":
        art["reporter_name"] = cfg.get("default_reporter_byline", "মাধবপুর প্রতিনিধি")
    if art.get("reporter_name"):
        try:
            q = urllib.parse.urlencode({"object_id": p["id"], "object_type": "post", "value": art["reporter_name"]})
            http(config()["site_url"].rstrip("/") + "/wp-json/cmb2/v1/boxes/reporter_information/fields/reporter_name?" + q,
                 data=b"", headers=auth(), method="POST")
        except Exception as e:
            log(f"reporter_name failed {p['id']}: {e}")
    log(f"posted {item['id']} -> {p['id']} ({p['status']}) {art['title']}")
    return {"status": p["status"], "post_id": p["id"], "title": art["title"], "link": p.get("link"),
            "edit_url": f"{cfg['site_url'].rstrip('/')}/wp-admin/post.php?post={p['id']}&action=edit",
            "scheduled_for": post.get("date")}


QUEUE_MARK = "<!--bkq "


def queue_one(d, item, art):
    """Code can't finish this story (link news / sensitive / no headline): keep it as a WordPress draft
    with everything Claude needs; claude_tasks.py lists and finishes these at 10:00 and 18:00."""
    st = art.get("story", {})
    media = []
    for fn in st.get("photos", []):
        try:
            m = upload(os.path.join(d, fn))
            media.append({"file": fn, "id": m["id"], "url": m["source_url"]})
        except Exception as e:
            log(f"queue photo upload failed {item['id']} {fn}: {e}")
    meta = {"item": {k: item.get(k) for k in ("id", "chat_id", "first_message_id", "reporter", "received_utc")},
            "reason": art.get("queue_reason"), "lines": st.get("lines", []), "links": st.get("links", []),
            "msg": st.get("msg"), "media": media, "draft_art": art.get("draft_art")}
    first = (st.get("lines") or st.get("links") or ["খবর"])[0][:90]
    readable = "".join(f"<p>{html.escape(x)}</p>" for x in st.get("lines", []) + st.get("links", []))
    p = wp("/posts", {"title": "⏳ " + first, "status": "draft",
                      "content": QUEUE_MARK + json.dumps(meta, ensure_ascii=False).replace("--", "\\u002d\\u002d") + " -->" + readable}, "POST")
    log(f"queued {item['id']} -> draft {p['id']} ({art.get('queue_reason')})")
    try:  # tell the reporter it arrived
        if config().get("force_draft"):
            raise RuntimeError("test run, no ack")
        tg("sendMessage", chat_id=item["chat_id"], reply_to_message_id=st.get("msg") or item["first_message_id"],
           allow_sending_without_reply=True, text="📥 নিউজটি আমরা পেয়েছি। অল্প কিছুক্ষণের মধ্যে প্রকাশ করা হবে।")
    except Exception as e:
        log(f"queue ack failed: {e}")
    return {"status": "skipped", "queued_post": p["id"], "title": first}


def main(d):
    """A batch may hold several stories: articles.json is a list (article.json = single, legacy)."""
    d = os.path.abspath(d)
    item = load_json(os.path.join(d, "item.json"))
    cfg = config()
    arts = load_json(os.path.join(d, "articles.json"))
    if arts is None:
        arts = [load_json(os.path.join(d, "article.json"))]
    done = {r.get("index") for r in item.get("results", []) if r.get("status") != "error"}
    item.setdefault("results", [])
    for i, art in enumerate(arts):
        if i in done:
            continue  # already published in an earlier, partly failed run
        try:
            r = publish_one(d, item, art, cfg)
        except Exception as e:
            r = {"status": "error", "error": str(e)[:300], "title": art.get("title", "")}
            log(f"error {item['id']}#{i}: {e}")
        r["index"] = i
        item["results"] = [x for x in item["results"] if x.get("index") != i] + [r]
        save_json(os.path.join(d, "item.json"), item)
        if r["status"] != "error" or item.get("attempts", 0) <= 1:  # don't DM the owner every 5 minutes
            notify(item, art, r, os.path.join(d, art["featured_photo"]) if art.get("featured_photo") else None)
    if all(r["status"] != "error" for r in item["results"]):
        item["status"] = "done"
        save_json(os.path.join(d, "item.json"), item)
        shutil.move(d, os.path.join(DONE, os.path.basename(d)))
    else:
        item["status"] = "error"
        save_json(os.path.join(d, "item.json"), item)


def post_to_channel(art, r, photo):
    """Public Telegram channel: photo + title + short summary + link (config telegram_channel)."""
    ch = config().get("telegram_channel")
    if not ch or not r.get("link"):
        return
    # OWNER RULE: nothing risky goes to the channel (a ban killed the old one). See EDITORIAL.md §6.
    if art.get("channel_ok") is False or art.get("risk", "low") != "low" or art.get("needs_editor"):
        log(f"channel skip {r.get('post_id') or r.get('id')}: channel_ok={art.get('channel_ok')} risk={art.get('risk')}")
        return
    esc = html.escape
    summary = (art.get("excerpt") or art.get("meta_description") or "").strip()
    cap = f"<b>{esc(r['title'])}</b>\n\n{esc(summary)}\n\n🔗 বিস্তারিত পড়ুন: {r['link']}"
    try:
        p16 = os.path.splitext(photo)[0] + "_16x9.jpg" if photo else None
        if p16 and os.path.exists(p16):
            tg_send_photo(ch, p16, cap[:1020])
        elif photo and os.path.exists(photo):
            tg_send_photo(ch, photo, cap[:1020])
        else:
            tg("sendMessage", chat_id=ch, text=cap, parse_mode="HTML")
        log(f"channel post ok {r.get('post_id') or r.get('id')}")
    except Exception as e:
        log(f"channel post failed: {e}")


def notify(item, art, r, photo):
    """Tell the owner only about problems: drafts (unverified facts), rejections, errors."""
    if config().get("force_draft"):
        return
    st = load_json(os.path.join(STATE, "telegram.json"), {})
    owner = st.get("owner_chat_id")
    if not owner or r["status"] == "skipped":
        return
    esc = html.escape
    who = esc(item["reporter"]["telegram_name"])
    if r["status"] in ("publish", "future"):
        # OWNER RULE: the published link goes as a reply to the reporter's own message in the group
        # (sent by the anonymous-admin bot, so it shows as the group, not as a bot).
        reply_to = art.get("reply_to_message_id") or item.get("first_message_id")
        try:
            tg("sendMessage", chat_id=item["chat_id"], reply_to_message_id=reply_to,
               allow_sending_without_reply=True, disable_web_page_preview=False,
               text=f"✅ নিউজটি প্রকাশিত হয়েছে\n{r['title']}\n{r.get('link') or ''}")
        except Exception as e:
            log(f"group reply failed: {e}")
        post_to_channel(art, r, photo)
        return
    if r["status"] == "rejected":
        text = f"⛔ একটি সংবাদ প্রকাশ করা হয়নি (প্রতিনিধি: {who})\nকারণ: {esc(r.get('reject_reason') or '')}"
    elif r["status"] == "error":
        text = f"⚠️ একটি সংবাদ প্রকাশে কারিগরি সমস্যা হয়েছে (প্রতিনিধি: {who})। পরের বার আবার চেষ্টা করা হবে।"
    else:
        text = f"<b>{esc(r['title'])}</b>\n\n⚠️ তথ্যে সমস্যা, তাই খসড়ায় রাখা হয়েছে।\n{esc(art.get('editor_notes') or '')}\n✍️ প্রতিনিধি: {who}\n\n✏️ <a href=\"{r['edit_url']}\">দেখে প্রকাশ করুন</a>"
    try:
        if photo and r["status"] == "draft":
            tg_send_photo(owner, photo, text[:1000])
        else:
            tg("sendMessage", chat_id=owner, text=text, parse_mode="HTML")
    except Exception as e:
        log(f"notify failed: {e}")
        try:
            tg("sendMessage", chat_id=owner, text=re.sub("<[^>]+>", "", text))
        except Exception as e2:
            log(f"notify text failed: {e2}")


if __name__ == "__main__":
    main(sys.argv[1])
