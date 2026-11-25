"""Turn one Telegram batch (item.json) into articles.json WITHOUT AI.

Rules (owner 2026-11-21): headline = reporter's first line (never reworded); "X প্রতিনিধি:" goes to
the byline field; "আরও পড়ুন", blank lines, phone numbers and stray subheads are dropped; short lines are
joined into 3-5 sentence paragraphs; category from place names; first photo = featured image.
Anything code can't handle safely is marked decision "queue" (Claude looks at it at 10:00 / 18:00).
"""
import os, re, sys, json, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

N = lambda s: unicodedata.normalize("NFC", s or "")

HABIGANJ = ["মাধবপুর", "চুনারুঘাট", "বাহুবল", "নবীগঞ্জ", "বানিয়াচং", "আজমিরীগঞ্জ", "লাখাই", "শায়েস্তাগঞ্জ", "হবিগঞ্জ সদর"]
EXTRA_AREAS = ["নাসিরনগর", "শ্রীমঙ্গল", "কমলগঞ্জ", "কুলাউড়া", "মৌলভীবাজার", "সিলেট", "সুনামগঞ্জ", "ব্রাহ্মণবাড়িয়া",
               "জামালপুর", "মালদ্বীপ", "হাইমচর", "হবিগঞ্জ", "ঢাকা", "চট্টগ্রাম"]
TOPICS = [  # (category, words) first match wins
    ("আইন আদালত", ["আদালত", "কারাদণ্ড", "রায় ঘোষণা", "জামিন"]),
    ("অপরাধ", ["আটক", "গ্রেপ্তার", "গ্রেফতার", "মাদক", "গাঁজা", "ইয়াবা", "চুরি", "ডাকাতি", "ছিনতাই", "মাদকসহ", "কারাগারে", "সংঘর্ষ", "কুপিয়ে", "মারধর", "হামলা"]),
    ("দুর্ঘটনা", ["দুর্ঘটনা", "সংঘর্ষে", "আগুন", "অগ্নিকাণ্ড", "পানিতে ডুবে"]),
    ("প্রবাস", ["প্রবাসী", "মালদ্বীপ", "সৌদি", "দুবাই", "প্রবাসে", "মালয়েশিয়া"]),
    ("রাজনীতি", ["বিএনপি", "বিএনপির", "বি এন পি", "আওয়ামী", "জামায়াত", "এনসিপি", "নির্বাচন", "প্রার্থী"]),
    ("শিক্ষা", ["বিদ্যালয়", "কলেজ", "মাদ্রাসা", "শিক্ষার্থী", "পরীক্ষা", "বিশ্ববিদ্যালয়"]),
    ("কৃষি ও প্রকৃতি", ["কৃষক", "ধান", "ফসল", "চাষ", "কৃষি"]),
    ("স্বাস্থ্য", ["হাসপাতাল", "স্বাস্থ্য", "চিকিৎসা", "ডেঙ্গু"]),
    ("খেলাধুলা", ["টুর্নামেন্ট", "ফুটবল", "ক্রিকেট", "খেলা"]),
    ("ধর্ম", ["মসজিদ", "মন্দির", "ওয়াজ", "মাহফিল", "পূজা"]),
]
# Need a human eye (photos may show bodies; election allegations need balance) -> Claude queue
SENSITIVE = ["লাশ", "মরদেহ", "আত্মহত্যা", "ধর্ষণ", "নিহত", "রক্তাক্ত", "ঝুলন্ত", "খুন", "হত্যা", "শিশু নির্যাতন"]
ELECTION_ALLEGATION = (["অভিযোগ", "হামলা", "হুমকি", "টাকা বিতরণ", "ভোট কেনা"], ["প্রার্থী", "ইউপি নির্বাচন", "নির্বাচনী", "ভোটার", "ভোটকেন্দ্র"])


def has(text, w):
    """Whole-word-ish match (so 'রায়' does not match 'চলাফেরায়')."""
    return re.search(r"(?<![\u0980-\u09FF])" + re.escape(w), text) is not None


def first_area(text):
    best = None
    for a in areas():
        k = text.find(a)
        if k >= 0 and (best is None or k < best[0] or (k == best[0] and len(a) > len(best[1]))):
            best = (k, a)
    return best
NOT_CHANNEL = ["সংঘর্ষ", "হামলা", "সাম্প্রদায়িক", "মামলা"]

PHONE = re.compile(r"(\+?88)?0১?[1১][3-9৩-৯][\d০-৯]{8}")
SUBHEAD_END = tuple("।?!\"'”’:);৷.,")


def site_cats():
    return {N(c["name"]): c for c in load_json(os.path.join(STATE, "site_categories.json"), [])}


def areas():
    cats = site_cats()
    up = [n for n, c in cats.items() if c["parent"] and c["parent"] not in ("সারাদেশ",)]
    return sorted(set(map(N, HABIGANJ + EXTRA_AREAS + up)), key=len, reverse=True)


def sentences(s):
    return [x for x in re.split(r"(?<=[।?!])\s+", s) if x.strip()]


def parse_dateline(lines):
    """Find 'X প্রতিনিধি:' in the first 3 lines. Returns (index, name, area_str, rest_of_line)."""
    for i, ln in enumerate(lines[:3]):
        m = re.match(r"^(.{0,80}?)(প্রতিনিধি|প্রতিবেদক|সংবাদদাতা)\s*[:：ঃ]\s*(.*)$", ln) \
            or re.match(r"^(.{0,80}?)(প্রতিনিধি|প্রতিবেদক|সংবাদদাতা)\s*[।.]?()$", ln)
        if not m:
            continue
        pre = m.group(1).strip(" ,-–—")
        name, area = "", pre
        fa = first_area(pre)
        if fa:
            name, area = pre[:fa[0]].strip(" ,-–—"), pre[fa[0]:].strip()
        else:
            if not re.search(r"\(", pre) and len(pre.split()) <= 3 and pre not in ("নিজস্ব", "স্টাফ"):
                name, area = "", pre
        return i, name, area, m.group(2), m.group(3).strip()
    # "আফতাবুল ইসলাম মেহেরাব হাইমচর।" = name + place on its own short line
    for i, ln in enumerate(lines[1:3], 1):
        fa = first_area(ln)
        if len(ln) <= 50 and fa and fa[0] > 0 and len(ln.split()) <= 6 and not re.search(r"[,:]", ln):
            return i, ln[:fa[0]].strip(), ln[fa[0]:].strip(" ।.") , "প্রতিনিধি", ""
    return None


def clean_lines(text):
    out = []
    for ln in text.splitlines():
        ln = re.sub(r"\s+", " ", ln).strip()
        if not ln or re.match(r"^(আরও|আরো)\s*পড়ুন", ln) or re.match(r"^https?://\S+$", ln):
            continue
        ln = PHONE.sub("", ln).strip(" ,-–")
        if re.match(r"^(মোবাইল|মোবাঃ|ফোন|যোগাযোগ)\s*[:：ঃ]?\s*$", ln):
            continue
        if ln:
            out.append(ln)
    return out


def paragraphs(lines):
    """Join short lines into 3-5 sentence paragraphs (owner style), drop stray subheads."""
    keep = []
    for i, ln in enumerate(lines):
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if len(ln) <= 50 and not ln.endswith(SUBHEAD_END) and len(nxt) > 60:
            continue  # subhead like "যা বললেন ওসি" – dropped
        keep.append(ln)
    paras, cur = [], ""
    for ln in keep:
        cur = (cur + " " + ln).strip()
        if len(cur) >= 280 and len(sentences(cur)) >= 3:
            paras.append(cur); cur = ""
    if cur:
        if paras and (len(cur) < 120 or len(sentences(cur)) < 2):
            paras[-1] += " " + cur
        else:
            paras.append(cur)
    return paras


def pick_categories(title, body, area):
    cats = site_cats()
    text = N(title + " " + body)
    found = []
    best = first_area(N(area)) if area else None
    best = best or first_area(text)
    if best:
        found.append(best[1])
    res = [a for a in found if a in cats]
    if res and cats[res[0]]["parent"] and N(cats[res[0]]["parent"]) in cats and len(res) < 2:
        res.append(N(cats[res[0]]["parent"]))
    score = []
    for cat, words in TOPICS:
        hits = sum(1 for w in words if has(text, w)) + 2 * sum(1 for w in words if has(N(title), w))
        if hits >= 2 and N(cat) in cats:
            score.append((hits, N(cat)))
    if score:
        res.append(max(score)[1])
    if not res:
        res = ["সারাদেশ"]
    return res[:3], found[0] if found else ""


def _secs(hms):
    h, m, x = (int(v) for v in hms.split(":"))
    return h * 3600 + m * 60 + x


def split_stories(item):
    """Split one batch into stories and attach each photo.

    Photos sent on their own (no text) are matched to a story like this (owner 2026-11-25, after the
    Lakhai / Andiura mix-up where every photo slid one story down):
      1. a photo from the same album as a story's message goes to that story;
      2. link news never takes a loose photo (it uses the source article's photo);
      3. the reporter's own habit in this batch decides: photos before the first story = "photo first,
         then text" (each photo goes to the NEXT story); photos after the last story = "text first,
         then photo" (each goes to the PREVIOUS story);
      4. if that is not clear, the photo goes to the story it was sent much closer in time to;
      5. still not clear -> the stories next to it are marked photo_unsure and are NOT published
         automatically (a wrong photo is worse than a short wait).
    """
    seq, stories, last = [], [], None
    t0 = None
    for m in item["messages"]:
        t = (m.get("text") or "").strip()
        if t.startswith(("📌", "/")):
            continue
        sec = _secs(m.get("time_utc") or "00:00:00")
        if t0 is not None and sec < t0 - 43200:
            sec += 86400  # batch crossed midnight UTC
        t0 = sec if t0 is None else max(t0, sec)
        lines = clean_lines(t)
        body_len = sum(len(x) for x in lines)
        starts = body_len >= 250 or (lines and parse_dateline(lines) is not None and body_len >= 120)
        if starts:
            last = {"lines": lines, "photos": [m["photo"]] if m.get("photo") else [], "links": list(m.get("links") or []),
                    "msg": m["message_id"], "t": sec, "album": m.get("album")}
            stories.append(last); seq.append(("S", last))
        elif m.get("links") and body_len < 250:
            last = {"lines": lines, "photos": [m["photo"]] if m.get("photo") else [], "links": m["links"],
                    "msg": m["message_id"], "link_only": True, "t": sec, "album": m.get("album")}
            stories.append(last); seq.append(("S", last))
        elif m.get("photo"):
            if seq and seq[-1][0] == "P" and seq[-1][1]["albums"] == {m.get("album")}:
                seq[-1][1]["photos"].append(m["photo"]); seq[-1][1]["albums"].add(m.get("album"))
            else:
                seq.append(("P", {"photos": [m["photo"]], "t": sec, "albums": {m.get("album")}}))
        elif last and body_len >= 60:
            last["lines"] += lines  # continuation of the same report
        # else: chit-chat -> silently skipped

    text_idx = [i for i, (k, x) in enumerate(seq) if k == "S" and not x.get("link_only")]
    runs = [i for i, (k, x) in enumerate(seq) if k == "P"]
    if not text_idx or not runs:
        return stories
    # 1. albums: photos that belong to a story's own album
    for i in list(runs):
        run = seq[i][1]
        owner = next((x for k, x in seq if k == "S" and x.get("album") and x["album"] in run["albums"]), None)
        if owner:
            owner["photos"] += run["photos"]; runs.remove(i)
    if len(text_idx) == 1:  # only one story with text: every loose photo is its photo
        for i in runs:
            seq[text_idx[0]][1]["photos"] += seq[i][1]["photos"]
        return stories
    fwd = any(i < text_idx[0] for i in runs)
    back = any(i > text_idx[-1] for i in runs)
    for i in runs:
        run = seq[i][1]
        prev = next((seq[j][1] for j in reversed(text_idx) if j < i), None)
        nxt = next((seq[j][1] for j in text_idx if j > i), None)
        target = None
        if fwd and not back:
            target = nxt
        elif back and not fwd:
            target = prev
        if target is None:
            gp = run["t"] - prev["t"] if prev else None
            gn = nxt["t"] - run["t"] if nxt else None
            if gp is not None and gn is not None:
                if gp * 2 <= gn and gp <= 600:
                    target = prev
                elif gn * 2 <= gp and gn <= 600:
                    target = nxt
            elif prev is None and nxt is not None:
                target = nxt
            elif nxt is None and prev is not None:
                target = prev
        if target is not None:
            target["photos"] += run["photos"]
        else:
            for x in (prev, nxt):  # both get the photo as a candidate; a person/Claude picks before publishing
                if x is not None:
                    x["photo_unsure"] = True
                    x["photos"] += run["photos"]
    return stories


def build_article(item, s):
    rep = item.get("reporter", {})
    if s.get("link_only") or not s["lines"]:
        return {"decision": "queue", "queue_reason": "লিংকের খবর", "story": s}
    lines = list(s["lines"])
    dl = parse_dateline(lines)
    title = "" if dl and dl[0] == 0 else (lines[dl[0] - 1] if dl else lines[0])  # headline = line just above the dateline
    if not title or len(title) > 120 or (title.endswith("।") and len(title) > 90):
        return {"decision": "queue", "queue_reason": "শিরোনাম আলাদা করা যায়নি", "story": s}
    name, area, word = "", "", "প্রতিনিধি"
    body_lines = lines[1:]
    if dl:
        i, name, area, word, rest = dl
        body_lines = ([rest] if rest else []) + lines[i + 1:]
    # "বার্তা প্রেরক <name>" / "লেখক:" lines at the end
    for j in range(len(body_lines) - 1, max(-1, len(body_lines) - 3), -1):
        m = re.match(r"^(বার্তা প্রেরক|প্রেরক|লেখক)\s*[:：ঃ,]?\s*(.+)$", body_lines[j])
        if m:
            name = name or m.group(2).strip(); body_lines.pop(j)
    body_lines = [b for b in body_lines if b]
    paras = paragraphs(body_lines)
    if not paras or sum(len(p) for p in paras) < 150:
        return {"decision": "queue", "queue_reason": "লেখা খুব ছোট", "story": s}
    plain = " ".join(paras)
    cats, place = pick_categories(title, plain, area)
    if not area:
        area = f"{place} (হবিগঞ্জ)" if place in map(N, HABIGANJ) else (place or "মাধবপুর (হবিগঞ্জ)")
    if area in HABIGANJ and "(" not in area:
        area = f"{area} (হবিগঞ্জ)"
    dateline = f"{area} {word}:"
    if word == "প্রতিনিধি" and "প্রতিনিধি" not in dateline:
        dateline = f"{area} প্রতিনিধি:"
    full = N(title + " " + plain)
    sensitive = [w for w in SENSITIVE if has(full, w)]
    elect = any(has(full, w) for w in ELECTION_ALLEGATION[0]) and any(has(full, w) for w in ELECTION_ALLEGATION[1])
    html_body = "".join(f"<p>{('<strong>' + html_escape(dateline) + '</strong> ') if k == 0 else ''}{html_escape(p)}</p>"
                        for k, p in enumerate(paras))
    words = title.split()
    focus = " ".join(words[:3]) if len(words) >= 3 else title
    meta = re.sub(r"\s+", " ", paras[0])
    if len(meta) > 150:
        cut = meta[:150]
        meta = cut[:cut.rfind("।") + 1] if cut.rfind("।") > 80 else cut[:cut.rfind(" ")] + "…"
    madhabpur = "মাধবপুর" in N(area) or (not name and place == "মাধবপুর")
    byline = name or (f"{area.split('(')[0].strip()} প্রতিনিধি" if area else "")
    art = {
        "decision": "publish", "title": title, "categories": cats,
        "tags": list(dict.fromkeys([c for c in cats if c not in ("সারাদেশ", "লিড নিউজ")]))[:4],
        "focus_keyword": focus, "slug": focus, "meta_description": meta, "excerpt": meta,
        "body_html": html_body, "featured_photo": s["photos"][0] if s["photos"] else None,
        "body_photos": s["photos"][1:2], "photo_alt": title, "photo_caption": "", "featured_caption": "",
        "reporter_name": byline, "source_type": "reporter", "risk": "low", "needs_editor": False,
        "channel_ok": not any(has(full, w) for w in NOT_CHANNEL), "reply_to_message_id": s["msg"],
        "acf_reporter": "মাধবপুর প্রতিনিধি" if madhabpur else None, "sources": [],
    }
    if s.get("photo_unsure"):
        return {"decision": "queue", "queue_reason": "ছবি কোন খবরের তা নিশ্চিত নয়", "story": s, "draft_art": art}
    if sensitive and not elect and config().get("sensitive_auto", True):
        # OWNER 2026-11-22: reporter's sensitive news (death, murder...) goes up at once, no waiting for a check.
        # Whole photo blurred, no second photo, never on the Telegram channel.
        art["blur_boxes"] = [[0, 0, 1, 1]] if s["photos"] else []
        art["body_photos"] = []
        art["channel_ok"] = False
        if s["photos"]:
            art["featured_caption"] = "ছবি: সংগৃহীত"
        return art
    if sensitive or elect:
        return {"decision": "queue", "queue_reason": ("স্পর্শকাতর: " + ", ".join(sensitive)) if sensitive
                else "নির্বাচনী অভিযোগ, ভারসাম্য দেখা দরকার", "story": s, "draft_art": art}
    if not s["photos"]:
        art["editor_notes"] = "ছবি নেই"
    return art


def html_escape(s):
    import html
    return html.escape(s, quote=False)


def main(d):
    item = load_json(os.path.join(d, "item.json"))
    arts = [build_article(item, s) for s in split_stories(item)]
    save_json(os.path.join(d, "articles.json"), arts)
    return arts


if __name__ == "__main__":
    for a in main(os.path.abspath(sys.argv[1])):
        print(a.get("decision"), a.get("queue_reason", ""), a.get("title", ""), a.get("categories", ""), a.get("reporter_name", ""), a.get("featured_photo"))
