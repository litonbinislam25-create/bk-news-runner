# daily.py build  [YYYY-MM-DD]  -> builds the edition in work/<date>/, makes PDF, sends it to the owner on Telegram with 2 buttons
# daily.py publish YYYY-MM-DD   -> uploads work/<date>/up/* to the e-paper site, creates one post per page, tells the owner
# Code only (no AI). Secrets come from env: TELEGRAM_BOT_TOKEN, OWNER_CHAT_ID, EPAPER_USER, EPAPER_APP_PASSWORD.
import sys, os, json, glob, base64, subprocess, datetime as dt, urllib.request, urllib.parse, xmlrpc.client, time, re
HERE = os.path.dirname(os.path.abspath(__file__)); WORK = os.path.join(HERE, 'work')
EP = 'https://banglarkhabor24.com/epaper'
DH = dt.timezone(dt.timedelta(hours=6))
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36', 'Accept': '*/*'}
bn = lambda s: re.sub(r'\d', lambda m: '০১২৩৪৫৬৭৮৯'[int(m.group())], str(s))


def req(url, data=None, headers=None, method=None, timeout=180):
    for i in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers={**UA, **(headers or {})}, method=method), timeout=timeout) as r:
                return json.loads(r.read() or b'null')
        except urllib.error.HTTPError as e:
            if e.code < 500 or i == 4: raise RuntimeError(f'{url} -> {e.code} {e.read()[:300]}')
        except Exception:
            if i == 4: raise
        time.sleep(10 * (i + 1))


def tg(method, files=None, **p):
    tok = os.environ['TELEGRAM_BOT_TOKEN'].strip()
    url = f'https://api.telegram.org/bot{tok}/{method}'
    if not files:
        data = urllib.parse.urlencode({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v) for k, v in p.items()}).encode()
        return req(url, data)
    bnd = '----bk' + str(time.time_ns()); body = b''
    for k, v in p.items():
        v = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
        body += f'--{bnd}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    for k, path in files.items():
        body += f'--{bnd}\r\nContent-Disposition: form-data; name="{k}"; filename="{os.path.basename(path)}"\r\nContent-Type: application/pdf\r\n\r\n'.encode() + open(path, 'rb').read() + b'\r\n'
    body += f'--{bnd}--\r\n'.encode()
    return req(url, body, {'Content-Type': f'multipart/form-data; boundary={bnd}'})


def owner(): return os.environ['OWNER_CHAT_ID'].strip()


def build(day):
    E = os.path.join(WORK, day); os.makedirs(E, exist_ok=True)
    py = [sys.executable, '-I']
    subprocess.run(py + [os.path.join(HERE, 'auto_fetch.py'), E, day], check=True)
    plan = json.load(open(f'{E}/plan.json'))
    subprocess.run(['node', os.path.join(HERE, 'build.js'), E], check=True, env={**os.environ, 'MG': '80'})
    subprocess.run(py + [os.path.join(HERE, 'crops.py'), E], check=True)
    from PIL import Image
    pages = sorted(glob.glob(f'{E}/out/*-p*.jpg'), key=lambda f: int(f.rsplit('-p', 1)[1][:-4]))
    ims = [Image.open(f).convert('RGB').resize((1684, 2380)) for f in pages]
    pdf = f'{E}/epaper-{plan["date"].replace(".", "-")}.pdf'
    ims[0].save(pdf, save_all=True, append_images=ims[1:], resolution=150, quality=80)
    cap = open(f'{E}/caption.txt').read()
    kb = {'inline_keyboard': [[{'text': '✅ সবকিছু ঠিক আছে, পাবলিশ করো', 'callback_data': f'ep:pub:{day}'}],
                              [{'text': '✏️ কিছু ভুল আছে, সংশোধনের জন্য Claude-এ পাঠাচ্ছি', 'callback_data': f'ep:hold:{day}'}]]}
    if os.environ.get('NO_TELEGRAM') != '1':
        tg('sendDocument', files={'document': pdf}, chat_id=owner(), caption=cap[:1024], reply_markup=kb)
    print('built', day, len(pages), 'pages')


def publish(day):
    E = os.path.join(WORK, day); plan = json.load(open(f'{E}/plan.json')); alts = json.load(open(f'{E}/alts.json'))
    user, pw = os.environ['EPAPER_USER'].strip(), os.environ['EPAPER_APP_PASSWORD'].strip()
    auth = {'Authorization': 'Basic ' + base64.b64encode(f'{user}:{pw}'.encode()).decode()}
    title = plan['date']
    old = req(f'{EP}/wp-json/wp/v2/posts?' + urllib.parse.urlencode({'search': title, 'per_page': 20, '_fields': 'id,title'}))
    if any(p['title']['rendered'] == title for p in old):
        print('already on site', title); tg('sendMessage', chat_id=owner(), text=f'ℹ️ {title} সংখ্যা আগেই সাইটে আছে।'); return
    media = {}
    for path in sorted(glob.glob(f'{E}/up/*.jpg')):
        name = os.path.basename(path)
        j = req(f'{EP}/wp-json/wp/v2/media', open(path, 'rb').read(),
                {**auth, 'Content-Type': 'image/jpeg', 'Content-Disposition': f'attachment; filename="{name}"'}, 'POST')
        media[name] = j
        if name in alts:
            req(f'{EP}/wp-json/wp/v2/media/{j["id"]}', json.dumps({'alt_text': alts[name]}).encode(), {**auth, 'Content-Type': 'application/json'}, 'POST')
    # one post per page (theme PrintPaper reads custom fields page_name / epaper_one / epaper_one_id) via XML-RPC
    rpc = xmlrpc.client.ServerProxy(f'{EP}/xmlrpc.php', allow_none=True)
    d0 = dt.datetime.strptime(day, '%Y-%m-%d')
    pages = sorted([k for k in media if re.search(r'-p\d+\.jpg$', k)], key=lambda k: int(k.rsplit('-p', 1)[1][:-4]))
    secs = {p['n']: p['sec'] for p in plan['pages']}
    for k in pages:
        n = int(k.rsplit('-p', 1)[1][:-4]); m = media[k]
        when = d0.replace(hour=0, minute=5 + n)
        rpc.wp.newPost(1, user, pw, {
            'post_type': 'post', 'post_status': 'publish', 'post_title': title, 'post_content': '',
            'post_date': xmlrpc.client.DateTime(when.strftime('%Y%m%dT%H:%M:%S')),
            'custom_fields': [{'key': 'page_name', 'value': f'পৃষ্ঠা {bn(n)} · {secs.get(n, "")}'},
                              {'key': 'epaper_one', 'value': m['source_url']},
                              {'key': 'epaper_one_id', 'value': str(m['id'])}]})
    tg('sendMessage', chat_id=owner(), text=f'✅ {plan["dateBn"]}-এর ই-পেপার ({bn(len(pages))} পাতা) সাইটে প্রকাশ হয়েছে।\n{EP}/')
    print('published', title, len(pages), 'pages', len(media), 'files')


if __name__ == '__main__':
    act = sys.argv[1]
    day = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else (dt.datetime.now(DH) + dt.timedelta(hours=12)).date().isoformat()
    {'build': build, 'publish': publish}[act](day)
