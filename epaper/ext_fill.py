# ext_fill.py : fills the e-paper when our own site has fewer than ~22 news of the day (owner 2026-11-25).
# Source: bdnews24 (public Quintype API, one listing call per 100 stories, no scraping). Kalbela and Banglanews24 are
# behind a Cloudflare bot check, so code cannot read them; add them in SRC once they become readable.
# Each story is rewritten in our own words by one small Claude call (config ai_model), with the source named at the end.
# Without ANTHROPIC_API_KEY nothing is added (we never print another outlet's text as is).
import os, re, io, json, html, time, urllib.request, datetime as dt
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36', 'Accept': '*/*'}
# section slug (first part of the story url) -> our desk name
DESK = {'bangladesh': 'জাতীয়', 'politics': 'জাতীয়', 'business': 'জাতীয়', 'economy': 'জাতীয়', 'education': 'জাতীয়', 'law-and-justice': 'জাতীয়', 'ctg': 'সারাদেশ',
        'world': 'আন্তর্জাতিক', 'samagrabangladesh': 'সারাদেশ', 'sport': 'খেলা', 'cricket': 'খেলা', 'football': 'খেলা',
        'glitz': 'বিনোদন', 'entertainment': 'বিনোদন'}
ORDER = ['জাতীয়', 'আন্তর্জাতিক', 'সারাদেশ', 'খেলা', 'বিনোদন']
SKIPW = re.compile(r'(ধর্ষণ|আত্মহত্যা|লাশ|মরদেহ|কুপিয়ে|ছবিতে|ভিডিও|কার্টুন|মতামত|কলাম)')


def get(u, raw=False):
    for i in range(3):
        try: r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read(); break
        except Exception:
            if i == 2: raise
            time.sleep(8 * (i + 1))
    return r if raw else json.loads(r)


def bdnews(a, b):
    """Stories published between a and b (aware datetimes) with section, text and hero photo."""
    out, f = [], 'headline,slug,published-at,hero-image-s3-key,cards'
    for off in (0, 100, 200, 300, 400):
        st = get(f'https://bangla.bdnews24.com/api/v1/stories?limit=100&offset={off}&fields={f}').get('stories', [])
        for s in st:
            t = dt.datetime.fromtimestamp(s['published-at'] / 1000, a.tzinfo)
            if not (a <= t < b): continue
            desk = DESK.get(s['slug'].split('/')[0])
            if not desk or not s.get('hero-image-s3-key') or SKIPW.search(s['headline']): continue
            txt = [html.unescape(re.sub(r'<[^>]+>', ' ', e.get('text', ''))).strip() for c in s.get('cards', []) for e in c.get('story-elements', [])
                   if e.get('type') == 'text' and e.get('subtype') in (None, 'summary')]
            txt = '\n'.join(re.sub(r'\s+', ' ', x) for x in txt if len(x) > 30)
            if len(txt) < 600: continue
            out.append({'key': 'x' + re.sub(r'\W', '', s['slug'].split('/')[-1]), 'desk': desk, 'title': s['headline'], 'text': txt[:6000],
                        'img': 'https://media.assettype.com/' + s['hero-image-s3-key'] + '?w=1600', 'src': 'বিডিনিউজ টোয়েন্টিফোর', 'srcimg': 'বিডিনিউজ২৪'})
        if not st or dt.datetime.fromtimestamp(st[-1]['published-at'] / 1000, a.tzinfo) < a: break
    return out


SRC = [bdnews]
RULES = """তুমি বাংলার খবর-এর ই-পেপারের ডেস্ক সম্পাদক। নিচের খবরটি নিজের ভাষায় নতুন করে লেখো।
- উৎসের বাক্য হুবহু নেবে না; নিজের গঠনে প্রমিত বাংলায় লিখবে। কোনো নাম, সংখ্যা, স্থান, তারিখ, উদ্ধৃতি বানাবে না বা বদলাবে না; উৎসে যা নেই তা লিখবে না।
- title: ৩০-৫৫ অক্ষর, তথ্যভিত্তিক, চটকদার নয়।
- paras: ৩-৪টি অনুচ্ছেদ, প্রতিটিতে ২-৪ বাক্য, মোট ১৬০-২২০ শব্দ। সংখ্যা বাংলা অঙ্কে। কোনো পত্রিকার নাম লিখবে না।
- খবরটি গুজব, সাম্প্রদায়িক, অশ্লীল বা কারো ব্যক্তিগত চরিত্রহনন হলে ok false।"""
SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['ok', 'title', 'paras'],
          'properties': {'ok': {'type': 'boolean'}, 'title': {'type': 'string'}, 'paras': {'type': 'array', 'items': {'type': 'string'}}}}


def rewrite(s, model):
    import anthropic
    try:
        r = anthropic.Anthropic(max_retries=2, timeout=120).messages.create(
            model=model, max_tokens=3000, output_config={'effort': 'low', 'format': {'type': 'json_schema', 'schema': SCHEMA}},
            messages=[{'role': 'user', 'content': f"{RULES}\n\nশিরোনাম: {s['title']}\n\n{s['text']}"}])
        if r.stop_reason in ('refusal', 'max_tokens'): return None
        print('ext ai', model, r.usage.input_tokens, r.usage.output_tokens)
        d = json.loads(next(b.text for b in r.content if b.type == 'text'))
        return d if d.get('ok') and d.get('title') and len(d.get('paras') or []) >= 2 else None
    except Exception as e:
        print('ext ai failed', type(e).__name__, str(e)[:150]); return None


def picks(a, b, n):
    pool = []
    for f in SRC:
        try: pool += f(a, b)
        except Exception as e: print('ext source failed', f.__name__, e)
    by = {d: [s for s in pool if s['desk'] == d] for d in ORDER}
    pick, i = [], 0
    while len(pick) < n and any(by.values()):  # round robin over desks
        d = ORDER[i % len(ORDER)]; i += 1
        if by[d]: pick.append(by[d].pop(0))
    return pick


def use(items, need, E, fit, Image):
    N, meta = {}, []
    for s in items:
        if len(meta) >= need: break
        try: fit(Image.open(io.BytesIO(get(s['img'], True))), f"{E}/img/{s['key']}.jpg")
        except Exception as e: print('ext img', s['key'], e); continue
        paras = [p.strip() for p in s['paras'] if p.strip()] + [f"তথ্যসূত্র: {s['src']}"]
        N[s['key']] = {'title': s['title'].strip(), 'by': 'বাংলার খবর ডেস্ক', 'kick': s['desk'], 'cap': f"ছবি: {s['srcimg']}", 'paras': paras}
        meta.append({'id': s['key'], 'local': False, 'mad': False, 'lead': False, 'img': True, 'words': sum(len(p.split()) for p in paras),
                     'nat': s['desk'] == 'জাতীয়', 'date': '', 'cats': [s['desk']], 'old': False, 'ext': True})
    print('ext added', len(meta), 'of need', need)
    return N, meta


def fill(need, a, b, E, fit, model):
    """Returns {id: news entry} and meta rows for up to `need` outside stories, spread over the desks."""
    if need <= 0: return {}, []
    from PIL import Image
    pre = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'state', 'epaper_ext', b.strftime('%Y-%m-%d') + '.json')
    if os.path.exists(pre): return use(json.load(open(pre)), need, E, fit, Image)  # rewritten earlier by the nightly Claude run
    if not os.environ.get('ANTHROPIC_API_KEY'): print('ext: no rewritten file', pre); return {}, []
    pool = []
    for f in SRC:
        try: pool += f(a, b)
        except Exception as e: print('ext source failed', f.__name__, e)
    by = {d: [s for s in pool if s['desk'] == d] for d in ORDER}
    pick, i = [], 0
    while len(pick) < need + 3 and any(by.values()):  # round robin over desks, a few spare for refusals
        d = ORDER[i % len(ORDER)]; i += 1
        if by[d]: pick.append(by[d].pop(0))
    N, meta = {}, []
    for s in pick:
        if len(meta) >= need: break
        w = rewrite(s, model)
        if not w: continue
        try: fit(Image.open(io.BytesIO(get(s['img'], True))), f"{E}/img/{s['key']}.jpg")
        except Exception as e: print('ext img', s['key'], e); continue
        paras = [p.strip() for p in w['paras'] if p.strip()] + [f"তথ্যসূত্র: {s['src']}"]
        N[s['key']] = {'title': w['title'].strip(), 'by': 'বাংলার খবর ডেস্ক', 'kick': s['desk'], 'cap': f"ছবি: {s['srcimg']}", 'paras': paras}
        meta.append({'id': s['key'], 'local': False, 'mad': False, 'lead': False, 'img': True, 'words': sum(len(p.split()) for p in paras),
                     'nat': s['desk'] == 'জাতীয়', 'date': '', 'cats': [s['desk']], 'old': False, 'ext': True})
    print('ext added', len(meta), 'of need', need, 'pool', len(pool))
    return N, meta


if __name__ == '__main__':
    # python3 epaper/ext_fill.py pool YYYY-MM-DD [n]  -> state/epaper_ext/<day>.pool.json: source stories of the previous day
    # for the nightly Claude run, which writes state/epaper_ext/<day>.json = [{key,desk,title,paras,img,src,srcimg}] in our words.
    import sys
    D = dt.date.fromisoformat(sys.argv[2]); DH = dt.timezone(dt.timedelta(hours=6))
    b = dt.datetime.combine(D, dt.time(0, 0), DH); a = b - dt.timedelta(days=1)
    b = min(b, dt.datetime.now(DH))
    P = picks(a, b, int(sys.argv[3]) if len(sys.argv) > 3 else 16)
    for s in P: s['text'] = s['text'][:1300]
    o = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'state', 'epaper_ext'); os.makedirs(o, exist_ok=True)
    json.dump(P, open(f'{o}/{D}.pool.json', 'w'), ensure_ascii=False, indent=0)
    print(len(P), 'stories ->', f'{o}/{D}.pool.json')
