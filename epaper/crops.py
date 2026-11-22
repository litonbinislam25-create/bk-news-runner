# crops.py <edir> : map.json + out/*.jpg -> up/ (pages + branded crops) + alts.json
import sys, json, os, shutil
from PIL import Image, ImageDraw, ImageFont
E = sys.argv[1]; plan = json.load(open(f'{E}/plan.json')); N = json.load(open(f'{E}/news.json'))
M = json.load(open(f'{E}/map.json')); T = plan['tag']; A = os.path.dirname(os.path.abspath(__file__)) + '/assets'
os.makedirs(f'{E}/up', exist_ok=True)
logo = Image.open(f'{A}/logo.jpg').convert('RGB')
fnt = ImageFont.truetype(f'{os.path.dirname(os.path.abspath(__file__))}/node_modules/@fontsource/hind-siliguri/files/hind-siliguri-bengali-600-normal.woff2', 40) if False else None
def brand(im):
    w, h = im.size; bh = max(90, w // 12)
    lg = logo.resize((int(logo.width * bh * .8 / logo.height), int(bh * .8)))
    out = Image.new('RGB', (w, h + bh), (15, 68, 104)); out.paste(lg, (20, int(bh * .1))); out.paste(im, (0, bh))
    return out
alts = {}
for n, items in M.items():
    pf = f'{T}-p{n}.jpg'; shutil.copy(f'{E}/out/{pf}', f'{E}/up/{pf}')
    P = Image.open(f'{E}/out/{pf}').convert('RGB'); W, H = P.size
    box = lambda r: P.crop((int(r[0] * W / 100) - 6, int(r[1] * H / 100) - 6, int((r[0] + r[2]) * W / 100) + 6, int((r[1] + r[3]) * H / 100) + 6))
    its = []
    for it in items:
        sid = it['id'].lstrip('c'); k = it['kind']
        name = f'{T}-{sid}.jpg' if k == 'f' else f'{T}-{sid}-{"b" if k == "b" else "a"}.jpg'
        parts = [box(r) for r in it['rects']]
        cw = max(p.width for p in parts); im = Image.new('RGB', (cw, sum(p.height for p in parts)), 'white'); y = 0
        for p in parts: im.paste(p, ((cw - p.width) // 2, y)); y += p.height
        if os.path.exists(f'{E}/cards/{name}'): shutil.copy(f'{E}/cards/{name}', f'{E}/up/{name}')  # designed story card
        else: brand(im).save(f'{E}/up/{name}', quality=88)
        its.append({'title': N[sid]['title'], 'img': name, 'rects': it['rects']})
    alts[pf] = 'BKMAP' + json.dumps({'items': its}, ensure_ascii=False, separators=(',', ':'))
json.dump(alts, open(f'{E}/alts.json', 'w'), ensure_ascii=False)
tot = sum(os.path.getsize(f'{E}/up/' + f) for f in os.listdir(f'{E}/up'))
print(len(os.listdir(f'{E}/up')), 'files', round(tot / 1e6, 1), 'MB')
