"""Small Claude API calls for the few stories code can't finish, so they publish right away.

- link news: read the linked page, write our own report (EDITORIAL rules, compact)
- sensitive reporter news: look at the photos (no corpse/suicide photo; blur blood)
- election allegations: check balance (unbalanced -> draft, owner told)
Needs the GitHub secret ANTHROPIC_API_KEY. Model: config.json "ai_model" (default claude-haiku-5-5).
Any failure returns None and the story falls back to the 10:00/18:00 Claude queue.
"""
import os, re, sys, json, html, base64, io, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

RULES = """তুমি বাংলার খবর (banglarkhabor24.com, হবিগঞ্জের মাধবপুরভিত্তিক) অনলাইন পোর্টালের ডেস্ক সম্পাদক।
নিয়ম:
- কোনো নাম, সংখ্যা, স্থান, তারিখ, উদ্ধৃতি বানাবে না বা বদলাবে না। উৎসে যা নেই তা লিখবে না।
- উৎসের বাক্য হুবহু নেবে না; নিজের ভাষায়, নিজের গঠনে প্রমিত বাংলায় লিখবে। সংখ্যা বাংলা অঙ্কে।
- অন্য কোনো পত্রিকা/টিভি/সাইটের নাম কোথাও লিখবে না ("সংশ্লিষ্ট সূত্র জানায়" লিখবে)। "তথ্যসূত্র" লাইন নয়।
- নির্বাচন: সব প্রার্থীর প্রতি নিরপেক্ষ; প্রশংসা/আক্রমণ নয়। কারো বিরুদ্ধে অভিযোগ থাকলে তা কার অভিযোগ স্পষ্ট লিখবে।
- গুজব, ব্যক্তিগত বিবাদ, সাম্প্রদায়িক/ঘৃণাসূচক লেখা, ধর্ষণের শিকার বা অপরাধে জড়িত শিশুর পরিচয় থাকলে decision "reject"।
- body_html: প্রথম <p> শুরু হবে <strong>বাংলার খবর ডেস্ক:</strong> দিয়ে; মোট ৩-৬টি অনুচ্ছেদ, প্রতিটিতে ৩-৫ বাক্য;
  শুধু <p>, <strong>, <em>, <blockquote> ট্যাগ; কোনো উপশিরোনাম, তালিকা বা লিংক নয়। তথ্য থাকলে প্রায় ৩০০ শব্দ, কিন্তু বাড়তি কথা নয়।
- title: ৪০-৬০ অক্ষর, focus_keyword (২-৩ শব্দ) দিয়ে শুরু; চটকদার নয়। meta_description: ১২০-১৫০ অক্ষর, focus_keyword সহ।
- channel_ok false: সহিংসতা, লাশ, যৌন অপরাধ, আত্মহত্যা, অপ্রমাণিত অভিযোগ, উসকানিমূলক উক্তি থাকলে।
- lead true শুধু বড় জাতীয় খবর, সরকারি বড় সিদ্ধান্ত, বড় দুর্ঘটনা বা নির্বাচনের খবরে।"""


def client():
    import anthropic
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=2, timeout=120)


def model():
    return config().get("ai_model") or "claude-haiku-5-5"


def ask(content, schema, max_tokens=8000):
    """One call with a JSON schema. Returns dict or None (refusal / error)."""
    try:
        r = client().messages.create(
            model=model(), max_tokens=max_tokens, output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}},
            messages=[{"role": "user", "content": content}])
    except Exception as e:
        log(f"ai call failed: {type(e).__name__}: {str(e)[:160]}"); return None
    if r.stop_reason in ("refusal", "max_tokens"):
        log(f"ai stop_reason {r.stop_reason}"); return None
    u = r.usage
    log(f"ai {model()} in={u.input_tokens} out={u.output_tokens}")
    try:
        return json.loads(next(b.text for b in r.content if b.type == "text"))
    except Exception as e:
        log(f"ai json failed: {e}"); return None


def page(url):
    """Title, main photo and paragraph text of a news page (no AI)."""
    raw = http(url, headers=UA, raw=True, timeout=40).decode("utf-8", "replace")
    meta = lambda p: (re.search(r'<meta[^>]+(?:property|name)=["\']' + p + r'["\'][^>]+content=["\']([^"\']+)', raw, re.I) or
                      re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']' + p, raw, re.I))
    title = meta("og:title"); img = meta("og:image")
    body = re.sub(r"(?is)<(script|style|nav|footer|header|aside)[^>]*>.*?</\1>", " ", raw)
    paras = [html.unescape(re.sub(r"<[^>]+>", "", p)).strip() for p in re.findall(r"(?is)<p[^>]*>(.*?)</p>", body)]
    paras = [p for p in paras if len(p) > 40]
    return (html.unescape(title.group(1)) if title else ""), (img.group(1) if img else None), "\n".join(paras)


def cat_names():
    return [c["name"] for c in load_json(os.path.join(STATE, "site_categories.json"), []) if c["name"] not in ("লিড নিউজ",)]


def link_story(item, art):
    st = art["story"]
    url = next((l for l in st.get("links", []) if "facebook.com" not in l and "fb.watch" not in l), None)
    if not url:
        if st.get("links"):
            return {"decision": "reject", "reject_reason": "ফেসবুক লিংক খোলা যায় না — পোস্টের লেখা ও ছবি সরাসরি গ্রুপে পাঠাতে হবে",
                    "reply_to_message_id": st.get("msg")}
        return None
    try:
        title, img, text = page(url)
    except Exception as e:
        log(f"page fetch failed {url}: {e}"); return None
    if len(text) < 200:
        log(f"page too short {url}"); return None
    schema = {"type": "object", "additionalProperties": False,
              "required": ["decision", "reject_reason", "title", "focus_keyword", "meta_description", "tags", "categories",
                           "body_html", "channel_ok", "lead"],
              "properties": {"decision": {"type": "string", "enum": ["publish", "reject"]}, "reject_reason": {"type": "string"},
                             "title": {"type": "string"}, "focus_keyword": {"type": "string"}, "meta_description": {"type": "string"},
                             "tags": {"type": "array", "items": {"type": "string"}},
                             "categories": {"type": "array", "items": {"type": "string", "enum": cat_names()}},
                             "body_html": {"type": "string"}, "channel_ok": {"type": "boolean"}, "lead": {"type": "boolean"}}}
    note = "\n".join(st.get("lines", []))
    out = ask(f"{RULES}\n\nনিচের সংবাদটি পড়ে আমাদের নিজস্ব প্রতিবেদন লেখো। categories: ১-২টি (তালিকা থেকে)। tags: ৩-৫টি।\n"
              f"প্রতিনিধির নোট: {note or '-'}\nউৎসের শিরোনাম: {title}\nউৎসের লেখা:\n{text}", schema)
    if not out:
        return None
    if out["decision"] == "reject":
        return {"decision": "reject", "reject_reason": out["reject_reason"] or "সম্পাদকীয় নীতিমালার সঙ্গে মেলে না",
                "reply_to_message_id": st.get("msg")}
    return {"decision": "publish", "title": out["title"], "categories": out["categories"], "tags": out["tags"],
            "focus_keyword": out["focus_keyword"], "slug": out["focus_keyword"], "meta_description": out["meta_description"],
            "excerpt": out["meta_description"], "body_html": out["body_html"], "featured_photo": img,
            "featured_caption": "ছবি: সংগৃহীত", "photo_alt": out["title"], "body_photos": [], "reporter_name": "",
            "source_type": "website", "risk": "low", "needs_editor": False, "channel_ok": out["channel_ok"],
            "lead": out["lead"], "reply_to_message_id": st.get("msg"), "sources": [{"name": "", "url": url}]}


def small_jpeg(path):
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB"); im.thumbnail((1024, 1024))
    b = io.BytesIO(); im.save(b, "JPEG", quality=80)
    return base64.standard_b64encode(b.getvalue()).decode()


def check_sensitive(d, item, art):
    """Reporter story kept exactly as written; AI only decides about photos and balance."""
    draft = dict(art["draft_art"]); st = art["story"]
    photos = [p for p in st.get("photos", []) if os.path.exists(os.path.join(d, p))][:4]
    content = []
    for i, p in enumerate(photos):
        content += [{"type": "text", "text": f"ছবি {i}:"},
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": small_jpeg(os.path.join(d, p))}}]
    schema = {"type": "object", "additionalProperties": False, "required": ["photos", "balanced", "problem", "channel_ok"],
              "properties": {"photos": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                                                                     "required": ["index", "use", "blur_boxes"],
                                                                     "properties": {"index": {"type": "integer"}, "use": {"type": "boolean"},
                                                                                    "blur_boxes": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}}}}},
                             "balanced": {"type": "boolean"}, "problem": {"type": "string"}, "channel_ok": {"type": "boolean"}}}
    content.append({"type": "text", "text":
        "তুমি একটি বাংলা সংবাদ পোর্টালের ছবি ও নীতিমালা পরীক্ষক। প্রতিনিধির লেখা বদলাবে না, শুধু যাচাই করবে।\n"
        "photos: প্রতিটি ছবির জন্য use (লাশ/মৃতদেহ, ঝুলন্ত দেহ, আত্মহত্যার দৃশ্য, ধর্ষণের শিকার বা শিশুর পরিচয় দেখা গেলে false), "
        "blur_boxes: রক্ত/ক্ষত/অস্ত্র তাক করা অংশ থাকলে [x0,y0,x1,y1] (০-১ ভগ্নাংশ), না থাকলে []।\n"
        "balanced: নির্বাচনী বা কারো বিরুদ্ধে অভিযোগ থাকলে তা সরকারি সূত্রে নিশ্চিত, অথবা অভিযুক্তের বক্তব্য/\"বক্তব্য পাওয়া যায়নি\" আছে কিনা; "
        "অভিযোগ না থাকলে true। problem: সমস্যা থাকলে বাংলায় এক লাইনে, না থাকলে ''। channel_ok: লাশ, সহিংসতা, অপ্রমাণিত অভিযোগ থাকলে false।\n\n"
        f"শিরোনাম: {draft['title']}\nলেখা: {re.sub('<[^>]+>', ' ', draft['body_html'])}"})
    out = ask(content, schema, 2000)
    if not out:
        return None
    usable = []
    for x in sorted(out["photos"], key=lambda x: x["index"]):
        if 0 <= x["index"] < len(photos) and x["use"]:
            usable.append((photos[x["index"]], [b for b in x["blur_boxes"] if len(b) == 4]))
    draft["featured_photo"] = usable[0][0] if usable else None
    draft["blur_boxes"] = usable[0][1] if usable else []
    draft["body_photos"] = []
    if not usable:
        draft["featured_photo"] = file_photo(draft)
        draft["featured_caption"] = "প্রতীকী ছবি"
    draft["channel_ok"] = bool(out["channel_ok"]) and draft.get("channel_ok", True)
    if not out["balanced"]:
        draft["needs_editor"] = True; draft["risk"] = "high"
        draft["editor_notes"] = out["problem"] or "অভিযুক্ত পক্ষের বক্তব্য নেই"
    return draft


def file_photo(art):
    """An existing site photo for stories whose own photo can't be shown (owner rule: never a corpse photo)."""
    try:
        from wp_publish import wp
        for q in ([art["title"].split()[0]] if art.get("title") else []) + ["মাধবপুর থানা"]:
            for m in wp("/media", params={"search": q, "per_page": 5, "media_type": "image", "_fields": "source_url"}):
                return m["source_url"]
    except Exception as e:
        log(f"file photo search failed: {e}")
    return None


def resolve(d, item, art):
    """Turn a 'queue' story into a publishable article now. None = leave it for the Claude queue."""
    if not os.environ.get("ANTHROPIC_API_KEY") or not config().get("ai_enabled", True):
        return None
    if art.get("draft_art"):
        return check_sensitive(d, item, art)
    if art.get("story", {}).get("links"):
        return link_story(item, art)
    return None
