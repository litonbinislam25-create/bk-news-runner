# auto_fetch.py <edir> [YYYY-MM-DD edition date, Dhaka]  -> <edir>/news.json, img/, plan.json
# Runs nightly 23:45 Dhaka; takes posts from previous 23:45 to this 23:45 and plans 8 pages.
import sys, json, re, os, io, html, datetime as dt, urllib.request, urllib.parse
from PIL import Image
SITE = os.environ.get('SITE', 'https://banglarkhabor24.com')
E = sys.argv[1]; os.makedirs(E + '/img', exist_ok=True)
DH = dt.timezone(dt.timedelta(hours=6))
D = dt.date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else (dt.datetime.now(DH) + dt.timedelta(hours=12)).date()
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36', 'Accept': '*/*'}
import time
def get(u, raw=False):
    for i in range(5):
        try: r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read(); break
        except Exception as ex:
            if i == 4: raise
            time.sleep(10 * (i + 1))
    return r if raw else json.loads(r)
bn = lambda s: re.sub(r'\d', lambda m: '০১২৩৪৫৬৭৮৯'[int(m.group())], str(s))
MON = ['জানুয়ারি', 'ফেব্রুয়ারি', 'মার্চ', 'এপ্রিল', 'মে', 'জুন', 'জুলাই', 'আগস্ট', 'সেপ্টেম্বর', 'অক্টোবর', 'নভেম্বর', 'ডিসেম্বর']
WD = ['সোমবার', 'মঙ্গলবার', 'বুধবার', 'বৃহস্পতিবার', 'শুক্রবার', 'শনিবার', 'রবিবার']
BM = ['বৈশাখ', 'জ্যৈষ্ঠ', 'আষাঢ়', 'শ্রাবণ', 'ভাদ্র', 'আশ্বিন', 'কার্তিক', 'অগ্রহায়ণ', 'পৌষ', 'মাঘ', 'ফাল্গুন', 'চৈত্র']
def bangla(d):  # revised Bangladesh calendar
    y = d.year if d >= dt.date(d.year, 4, 14) else d.year - 1
    n = (d - dt.date(y, 4, 14)).days; leap = (y + 1) % 4 == 0 and ((y + 1) % 100 != 0 or (y + 1) % 400 == 0)
    L = [31] * 6 + [30] * 5 + [30 if leap else 29] + [30]; L = L[:12]
    for i, l in enumerate(L):
        if n < l: return f'{bn(n + 1)} {BM[i]} {bn(y - 593)}'
        n -= l
# ---- fetch posts
a = dt.datetime.combine(D - dt.timedelta(days=1), dt.time(0, 0), DH); b = dt.datetime.combine(D, dt.time(0, 0), DH)
if os.environ.get('EP_UNTIL_NOW') == '1': b = max(b, dt.datetime.now(DH).replace(microsecond=0))  # rebuild: also news the owner added after midnight  # previous calendar day 00:00-23:59 only (owner rule)
q = urllib.parse.urlencode({'after': a.strftime('%Y-%m-%dT%H:%M:%S'), 'before': b.strftime('%Y-%m-%dT%H:%M:%S'), 'per_page': 60, '_embed': 'wp:featuredmedia,wp:term',
     '_fields': 'id,date,title,content,categories,_links,_embedded'})
P = get(f'{SITE}/wp-json/wp/v2/posts?{q}')
# filler pool: earlier 3 days, minus stories already printed in earlier editions (titles in BKMAP alts)
a2 = a - dt.timedelta(days=3)
q = urllib.parse.urlencode({'after': a2.strftime('%Y-%m-%dT%H:%M:%S'), 'before': a.strftime('%Y-%m-%dT%H:%M:%S'), 'per_page': 80, '_embed': 'wp:featuredmedia,wp:term',
     '_fields': 'id,date,title,content,categories,_links,_embedded'})
OLD = get(f'{SITE}/wp-json/wp/v2/posts?{q}')
usedT = set()
for pg in (1, 2):
    for m in get(f'{SITE}/epaper/wp-json/wp/v2/media?per_page=100&page={pg}&_fields=alt_text'):
        if m['alt_text'].startswith('BKMAP'):
            try: usedT |= {i['title'] for i in json.loads(m['alt_text'][5:])['items']}
            except Exception: pass
oldids = set()
P = [p for p in P if html.unescape(re.sub('<[^>]+>', '', p['title']['rendered'])).strip() not in usedT]
for p in OLD:
    t = html.unescape(re.sub('<[^>]+>', '', p['title']['rendered'])).strip()
    if False and t not in usedT and not re.search(r'(আজ|আগামীকাল|কাল থেকে)', t): P.append(p); oldids.add(str(p['id']))
print('filler candidates', len(oldids), 'used titles', len(usedT))
LOCAL = {'মাধবপুর', 'লাখাই', 'হবিগঞ্জ', 'হবিগঞ্জ সদর', 'চুনারুঘাট', 'বাহুবল', 'নবীগঞ্জ', 'বানিয়াচং', 'আজমিরীগঞ্জ', 'শায়েস্তাগঞ্জ'}
SKIPC = {'লিড নিউজ', 'সমগ্র বাংলাদেশ', 'সিলেট বিভাগ', 'চট্টগ্রাম বিভাগ', 'ঢাকা বিভাগ', 'ময়মনসিংহ বিভাগ', 'বরিশাল বিভাগ', 'রাজশাহী বিভাগ', 'রংপুর বিভাগ'}
def fit(im, dst):
    im = im.convert('RGB'); w, h = im.size
    if w / h > 16 / 9: nw = int(h * 16 / 9); box = ((w - nw) // 2, 0, (w - nw) // 2 + nw, h)
    else: nh = int(w * 9 / 16); top = int((h - nh) * 0.3); box = (0, top, w, top + nh)
    im.crop(box).resize((1600, 900), Image.LANCZOS).save(dst, quality=92)
bad = re.compile(r'(আরও পড়ুন|^বার্তা প্রেরক|^ছবি:|^ভিডিও:)')
end = tuple('।?!’”)')
N, meta = {}, []
SKIP = set(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'skip.txt')).read().split()) if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'skip.txt')) else set()
for p in P:
    sid = str(p['id'])
    if sid in SKIP: continue
    t = html.unescape(re.sub('<[^>]+>', '', p['title']['rendered'])).strip()
    c = p['content']['rendered']
    paras = [html.unescape(re.sub(r'<[^>]+>', '', x)).replace('\xa0', ' ').strip() for x in re.findall(r'<p[^>]*>(.*?)</p>', c, re.S)]
    paras = [re.sub(r'\s+', ' ', x) for x in paras if x.strip()]
    if not paras: continue
    by = 'বাংলার খবর ডেস্ক'; f0 = paras[0]; k = f0.find(':')
    if 0 < k < 60: by = f0[:k].strip(); rest = f0[k + 1:].strip(); paras = ([rest] if rest else []) + paras[1:]
    q2 = [x for x in paras if not (bad.search(x) or (not x.endswith(end) and len(x) < 70))]
    mm, cur = [], ''
    for x in q2:
        cur = (cur + ' ' + x).strip() if cur else x
        if len(cur) >= 220: mm.append(cur); cur = ''
    if cur:
        if mm and len(cur) < 80: mm[-1] += ' ' + cur
        else: mm.append(cur)
    terms = [x['name'] for g in p.get('_embedded', {}).get('wp:term', []) for x in g if x.get('taxonomy') == 'category']
    terms = [html.unescape(x) for x in terms]
    loc = [x for x in terms if x in LOCAL and x != 'হবিগঞ্জ'] or [x for x in terms if x in LOCAL]
    kick = (loc or [x for x in terms if x not in SKIPC] or ['সারাদেশ'])[0]
    # image: featured, else first <img> in content
    img = None
    fm = p.get('_embedded', {}).get('wp:featuredmedia', [])
    if fm and fm[0].get('source_url'): img = fm[0]['source_url']
    else:
        m = re.search(r'<img[^>]+src="([^"]+)"', c); img = m.group(1) if m else None
    has = False
    if img:
        try: fit(Image.open(io.BytesIO(get(img, True))), f'{E}/img/{sid}.jpg'); has = True
        except Exception as ex: print('IMGERR', sid, ex)
    local = bool(loc) or 'প্রতিনিধি' in by
    N[sid] = {'title': t, 'by': by, 'kick': kick, 'cap': 'ছবি: প্রতিনিধি' if local else 'ছবি: সংগৃহীত', 'paras': mm}
    words = sum(len(x.split()) for x in mm)
    meta.append({'id': sid, 'local': local, 'mad': 'মাধবপুর' in terms or by.startswith('মাধবপুর'), 'lead': 'লিড নিউজ' in terms,
                 'img': has, 'words': words, 'nat': any(x in terms for x in ('জাতীয়', 'রাজনীতি', 'অর্থনীতি', 'আইন আদালত')), 'date': p['date'], 'cats': terms, 'old': sid in oldids})
# owner 2026-11-25: news still missing for 8 pages (~22) come from outside sites, rewritten in our words with source named
own = len([m for m in meta if m['words'] >= 40 and not m['old']])
if os.environ.get('EP_EXT', '1') == '1' and own < 22:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import ext_fill
    cfg = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.json')))
    try: xN, xm = ext_fill.fill(22 - own, a, b, E, fit, cfg.get('ai_model') or 'claude-haiku-5-5')
    except Exception as ex: print('ext fill failed', ex); xN, xm = {}, []
    N.update(xN); meta += xm
json.dump(N, open(f'{E}/news.json', 'w'), ensure_ascii=False, indent=0)
# ---- plan
meta = [m for m in meta if m['words'] >= 40]
olds = sorted([m for m in meta if m['old'] and m['img']], key=lambda m: (m['local'], m['date']), reverse=True)
meta = [m for m in meta if not m['old']]
score = lambda m: (not m.get('ext'), m['img'], m['mad'] * 3 + m['local'] * 2 + m['lead'] + min(m['words'], 600) / 600)
meta.sort(key=score, reverse=True)
used = set()
def take(pred, n, need_img=False):
    r = []
    for m in meta:
        if len(r) == n: break
        if m['id'] in used or (need_img and not m['img']) or not pred(m): continue
        r.append(m); used.add(m['id'])
    return r
ref = lambda m: m['id'] + ('' if m['img'] else '!')
LF = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'state', 'epaper_lead', D.isoformat() + '.txt')  # owner's chosen lead (post id)
want = open(LF).read().strip() if os.path.exists(LF) else ''
lead = take(lambda m: m['id'] == want and m['img'], 1, True) or take(lambda m: m['img'], 1, True)
right = take(lambda m: True, 3, True)
p2 = take(lambda m: m['local'], 3); p2 += take(lambda m: True, 3 - len(p2))
p3 = take(lambda m: m['nat'], 3); p3 += take(lambda m: True, 3 - len(p3))
p4 = take(lambda m: True, 3)
full = [m['id'] for m in meta if m['id'] not in used and m['img']] + [m['id'] for m in olds]
def secname(ms, dflt):
    ks = [N[m['id']]['kick'] for m in ms]
    if all(m['local'] for m in ms) and ms: return 'হবিগঞ্জ'
    if ms and len(set(ks)) == 1 and ks[0] in ('জাতীয়', 'আন্তর্জাতিক', 'সারাদেশ', 'খেলা', 'বিনোদন'): return ks[0]
    return dflt
AD = ['ad_epaper.jpg', None, 'ad_sunni.jpg']  # page 3 has no ad (owner 2026-11-23); ad_jamia.jpg not used
pages = [{'n': 1, 'sec': 'প্রথম পাতা', 'lead': lead[0]['id'], 'right': [m['id'] for m in right]}]
for i, (ms, dflt) in enumerate([(p2, 'হবিগঞ্জ'), (p3, 'জাতীয়'), (p4, 'সারাদেশ')]):
    if not ms: ms = []
    ms = sorted(ms, key=lambda m: (m['img'], m['words']))  # best photo story goes under the ad
    ids = [ref(m) for m in ms]
    if AD[i] is None:
        pages.append({'n': i + 2, 'sec': secname(ms, dflt), 'left': ids[:2], 'right': ids[2:]}); continue
    if len(ids) < 3: ids = ids[:1] + [None] + ids[1:]  # keep a story under the ad
    pages.append({'n': i + 2, 'sec': secname(ms, dflt), 'left': [x for x in ids[:2] if x], 'right': [{'ad': AD[i]}] + ids[2:]})
# owner 2026-11-24: only as many pages as the news fills; pages 2-4 without stories are left out
pages = [pages[0]] + [pg for pg in pages[1:] if pg['left'] or any(isinstance(x, str) for x in pg['right'])]
for i, pg in enumerate(pages): pg['n'] = i + 1
F = len(pages)
for n in range(F + 1, F + 5): pages.append({'n': n, 'sec': 'বাকি অংশ'})
old = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'e21/plan.json')))
dd = D.strftime('%d-%m-%Y')
plan = {'tag': f'bk-{dd}', 'date': D.strftime('%d.%m.%Y'), 'dateBn': f'{bn(D.day)} {MON[D.month - 1]} {bn(D.year)}, {WD[D.weekday()]}', 'bangla': bangla(D).rsplit(' ', 0)[0],
        'pages': pages, 'F': F, 'nnews': len([m for m in meta if not m.get('ext')]), 'next': len([m for m in meta if m.get('ext')]), 'full': full, 'imprint': old['imprint'], 'dateBn2': f'{WD[D.weekday()]}, {bn(D.day)} {MON[D.month - 1]} {bn(D.year)}'}
json.dump(plan, open(f'{E}/plan.json', 'w'), ensure_ascii=False, indent=0)
print('posts', len(P), 'usable', len(meta), 'full', len(full), plan['dateBn2'], plan['bangla'])
for pg in pages: print(pg)

cap = (f"{plan['dateBn']}-এর বাংলার খবর। বাংলার খবর।Banglar Khabor   ই-পেপার।\n\n"
       "দেশ-বিদেশের সর্বশেষ খবর ও গুরুত্বপূর্ণ সংবাদ পড়তে নিচের লিংকে প্রবেশ করুন।\n\n"
       "🔗 https://banglarkhabor24.com/epaper/\nবাংলার খবর, আপনার প্রতিদিনের সংবাদসঙ্গী।")
open(f'{E}/caption.txt', 'w').write(cap)
