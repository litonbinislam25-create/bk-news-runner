// node build.js <edir>   (edir has plan.json, news.json, img/)
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const E = path.resolve(process.argv[2]), A = path.resolve(__dirname, 'assets'), F = path.resolve(__dirname, 'node_modules/@fontsource');
const plan = JSON.parse(fs.readFileSync(E + '/plan.json'));
const N = JSON.parse(fs.readFileSync(E + '/news.json'));
let TOTALP = 8;
const TG = 'file://' + require('path').resolve(__dirname, 'assets') + '/';
const W = 1123, H = 1587, PX = 44, TAG = plan.tag, GAP = 26;
const LW = Math.round((W - 2 * PX - GAP) * 0.55), RW = W - 2 * PX - GAP - LW, HALF = (W - 2 * PX - GAP) / 2;
const bn = n => String(n).replace(/\d/g, d => '০১২৩৪৫৬৭৮৯'[d]);
const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
const CSS = `
@font-face{font-family:'Lalsalu';src:url('file://${A}/lalsalu.ttf')}
:root{--navy:#0d4568;--red:#d7232e;--ink:#111;--muted:#55524c;--rule:#cfcac0}
*{box-sizing:border-box;margin:0;padding:0}
body{background:#fff;width:${W}px}
.page{position:relative;width:${W}px;height:${H}px;overflow:hidden;background:#fff;font-family:Lalsalu;color:var(--ink)}
.wm{position:absolute;width:560px;opacity:.06;z-index:0;pointer-events:none;transform:rotate(-18deg)}
.z{position:relative;z-index:1}
.band{height:160px;background:var(--navy);color:#fff;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;padding:0 ${PX}px}
.band .l{font-size:17px;line-height:1.7}
.band .logo{height:150px}
.band .r{display:flex;align-items:center;gap:12px;justify-content:flex-end}
.band .r span{font-size:19px;line-height:1.35;text-align:right;width:200px}
.band .r .qb{background:#fff;border-radius:8px;padding:7px 7px 3px;text-align:center;color:#1f4e8c;font-size:11px}
.band .r .qb img{width:112px;height:112px;display:block}
.pill{display:inline-block;background:var(--red);color:#fff;font-weight:700;font-size:14px;padding:2px 10px;border-radius:3px}
.dstrip{margin:0 ${PX}px;display:flex;justify-content:space-between;font-size:15.5px;padding:9px 0;color:#333}
.dstrip .mid{color:var(--red)}
.hdr{height:104px;margin:0 ${PX}px;display:flex;align-items:center;justify-content:space-between;border-bottom:4px double var(--navy)}
.hdr .lg{background:var(--navy);padding:6px 12px;border-radius:2px;height:78px;display:flex;align-items:center}
.hdr .lg img{height:66px}
.hdr .sec{flex:1;margin-left:24px;font-size:40px;font-weight:400;color:var(--navy);border-left:8px solid var(--red);padding-left:16px;line-height:1.05}
.hdr .r{display:flex;align-items:center;gap:12px;text-align:right;font-size:15px;line-height:1.5}
.hdr .r img{width:84px;height:84px;border:1.5px solid #1f4e8c;border-radius:6px;padding:3px}
.foot{position:absolute;left:${PX}px;right:${PX}px;bottom:10px;border-top:1px solid var(--ink);display:flex;justify-content:space-between;font-size:13px;color:var(--muted);padding-top:5px}
.body{position:absolute;left:${PX}px;right:${PX}px;display:flex;gap:${GAP}px}
.col{display:flex;flex-direction:column;justify-content:space-between;position:relative}
.col+.col:before{content:'';position:absolute;left:-${GAP / 2}px;top:0;bottom:0;border-left:1px solid var(--rule)}
.st{position:relative}
.st h2{font-weight:700;line-height:1.22;color:var(--ink);-webkit-text-stroke:.5px currentColor;margin-bottom:8px}
.th h2{margin-bottom:4px}
.kk{color:var(--red);font-weight:700;font-size:15px;margin-bottom:4px}
.kk:before{content:'■ '}
.th{display:flex;gap:12px;align-items:flex-start;margin-bottom:2px}
.th figure{width:38%;flex:none;margin:0}
.th .tt{flex:1}
.th .tt .by{border:0;margin:0;padding:0}
.th + .rl{border-top:1px solid #cfcac0;margin:6px 0 8px}
.st .by{color:#1f4e8c;font-size:16px;padding-bottom:7px;border-bottom:1px solid var(--rule);margin-bottom:9px}
.st figure img{width:100%;aspect-ratio:16/9;object-fit:cover;display:block}
.st figcaption{color:var(--muted);font-size:12.5px;margin:3px 0 5px}
.bd{columns:2;column-gap:20px;column-rule:1px solid var(--rule);font-size:15px;line-height:1.55;text-align:justify;text-align-last:left;-webkit-text-stroke:.35px #000;color:#000;hyphens:none}
.bd p{margin:0;text-indent:0}
.bd p:first-child{text-indent:0}
.jump{color:var(--red);font-weight:700;font-size:15px;text-align:left;text-indent:0;break-inside:avoid;margin-top:2px;-webkit-text-stroke:0}
.ct{font-weight:700;font-size:15px;color:#fff;background:var(--red);display:inline-block;padding:2px 10px;border-radius:3px;margin-bottom:6px}
.sep{border-top:2px solid #222;padding-top:12px}
.ad{text-align:center}
.ad img{width:100%;display:block;max-height:600px;object-fit:contain}
.ad{position:relative;border:1px solid #bbb}
.ad .lb{position:absolute;left:0;top:0;background:var(--red);color:#fff;font-size:12px;font-weight:700;padding:1px 7px;z-index:2}
.lead{margin-bottom:12px}
.blood{border:1.5px solid #9e1219;font-family:Lalsalu;background:#fff}
.blood .tp{background:linear-gradient(#b5141c,#8e0f15);color:#fff;text-align:center;padding:10px 12px 12px}
.blood .tp .s{font-size:14px;opacity:.9}
.blood .tp .t{font-size:36px;font-weight:700;line-height:1.3}
.blood .tp .d{font-size:14.5px;line-height:1.5}
.blood .tp .d b{background:#fff;color:#b5141c;padding:0 6px;border-radius:3px}
.blood .bx{display:flex;gap:14px;padding:12px 14px 6px}
.blood .bx>div{flex:1;border:1.5px dashed #c9353c;border-radius:6px;text-align:center;padding:8px 6px;color:#555;font-size:11.5px}
.blood .bx .h{color:#b5141c;font-size:15.5px;margin-bottom:4px}
.blood .bx img{width:130px;height:130px;display:block;margin:4px auto}
.blood .ck{text-align:center;font-size:12.5px;color:#333;padding:2px 0 8px}
.blood .ft{background:#1d1d1d;color:#fff;display:flex;justify-content:space-between;align-items:center;padding:8px 14px;font-size:14px}
.blood .ft span{background:#25a244;border-radius:20px;padding:3px 14px}
.lead h1{color:var(--red);font-weight:700;font-size:76px;line-height:1.15;text-align:justify;text-align-last:justify;-webkit-text-stroke:.5px currentColor}
.adband{position:absolute;left:${PX}px;right:${PX}px;bottom:44px;height:92px;border:2px solid var(--navy);display:flex;align-items:center;padding:0 0 0 18px;background:#f7f9fb}
.adband .tg{background:var(--red);color:#fff;font-size:12px;writing-mode:vertical-rl;transform:rotate(180deg);padding:6px 3px;margin-right:18px}
.adband .nm{color:var(--red);font-weight:700;font-size:40px;line-height:1.1}
.adband .ad2{font-size:14.5px;color:var(--navy)}
.adband .ph{background:var(--navy);color:#fff;font-weight:700;font-size:32px;padding:6px 24px;margin-right:22px}
.imp{font-size:13.5px;line-height:1.75;border-top:1px solid #999;padding:10px 4px 0;color:#1f4e8c;text-align:center}
.imp b{font-weight:700}
`;

const PROMO = (H, A) => { // fills empty space: Telegram / Facebook QR boxes, blood-donation banner, house ads
  window.__pk = (window.__pk || 0);
  const qr = (h, tg) => { const q = Math.max(90, Math.min(220, h - 150)), c = tg ? '#229ed9' : '#1877f2';
    return [h, `<div style="height:${h}px;border:2px solid ${c};border-radius:6px;background:${tg ? '#eef8fd' : '#eef3fd'};display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:8px;padding:10px;font-family:Lalsalu;overflow:hidden">
<div style="color:#0d4568;font-size:${h > 300 ? 30 : 22}px;font-weight:700;line-height:1.25">${tg ? 'সবার আগে খবর পেতে<br>টেলিগ্রাম চ্যানেলে যুক্ত হোন' : 'দেশের সকল খবর জানতে<br>ফেসবুকে আমাদের ফলো করুন'}</div>
<img src="${A}${tg ? 'qr_tg.png' : 'qr_fb.png'}" style="width:${q}px;height:${q}px;background:#fff;padding:4px;border-radius:4px">
<div style="background:${c};color:#fff;font-size:17px;padding:3px 14px;border-radius:14px">${tg ? 't.me/banglarkhabor24news' : 'facebook · বাংলার খবর'}</div></div>`]; };
  const ad = (h, f) => [h, `<div class="ad" style="height:${h}px;display:flex;align-items:center;justify-content:center;background:#fff"><div class="lb">বিজ্ঞাপন</div><img src="${A}${f}" style="max-height:${h - 4}px;width:auto;max-width:100%;object-fit:contain"></div>`];
  const blood = w => { const h = Math.round(w * 9 / 16); return [h, `<div style="height:${h}px"><img src="${A}blood.png" style="width:100%;height:100%;display:block;border:1px solid #9e1219"></div>`]; };
  const ADS = ['ad_sunni.jpg', 'ad_jamia.jpg', 'ad_epaper.jpg'];
  let rem = H, out = [];
  while (rem > 130) {
    const k = window.__pk++; let p;
    if (rem >= 600 && k % 3 !== 2) p = ad(Math.min(rem, 780), ADS[k % 3]);
    else if (rem >= 320 && k % 2 === 0) p = blood(500);
    else p = qr(Math.min(rem, 420), k % 2 === 0);
    if (p[0] > rem) p = qr(rem, true);
    out.push(p[1]); rem -= p[0] + 12;
  }
  return out.map((x, i) => `<div class="promo" style="margin-top:${i ? 12 : 0}px">${x}</div>`).join('');
};
const FIXH = `window.fitAll=function(){
const m=document.createElement('span');m.style.cssText='position:absolute;visibility:hidden;white-space:nowrap;font-family:Lalsalu;font-weight:700;font-size:50px;-webkit-text-stroke:.5px';document.body.appendChild(m);
const wid=t=>{m.textContent=t;return m.offsetWidth};
for(const e of document.querySelectorAll('[data-fit]')){
 const ws=(e.dataset.t||e.textContent).trim().split(/ +/);e.dataset.t=ws.join(' ');const W=e.clientWidth*0.985;const mx=+e.dataset.max;
 if(ws.length<2){e.style.fontSize=mx+'px';continue}
 let best=null;for(let i=1;i<ws.length;i++){const a=wid(ws.slice(0,i).join(' ')),b=wid(ws.slice(i).join(' '));const sc=Math.min(a,b)/Math.max(a,b);if(!best||sc>best.sc)best={i,a,b,sc}}
 const L=Math.max(best.a,best.b);const f=Math.min(mx,50*W/L);
 const fl=w=>Math.min(f*1.14,f*(L/w)>mx*1.14?mx*1.14:f*(L/w));
 const f1=f<mx?Math.min(f*1.2,50*W/best.a):f, f2=f<mx?Math.min(f*1.2,50*W/best.b):f;
 e.innerHTML='<span style="display:block;white-space:nowrap;font-size:'+f1.toFixed(1)+'px">'+ws.slice(0,best.i).join(' ')+'</span><span style="display:block;white-space:nowrap;font-size:'+f2.toFixed(1)+'px">'+ws.slice(best.i).join(' ')+'</span>';
 e.style.fontSize=f.toFixed(1)+'px';e.style.textAlign='center';e.style.textAlignLast='center';}
m.remove()}`;
const HEAD = `<!doctype html><html><head><meta charset="utf-8"><style>${CSS}</style><script>${FIXH}</script></head><body>`;
const qr = 'file://' + A + '/qr_fb.png', logo = 'file://' + A + '/logo.jpg';
function header(n, sec) {
  if (n === 1) return `<div class="band z"><div class="l"><span class="pill">ই-পেপার</span><br>অনলাইন সংস্করণ · মোট ${bn(TOTALP)} পৃষ্ঠা<br>banglarkhabor24.com</div><img class="logo" src="${logo}"><div class="r"><span>দেশের সকল খবর জানতে<br><b style="font-size:21px;font-weight:400">ফেসবুকে আমাদের ফলো করুন</b><br><i class="pill" style="font-style:normal;margin-top:6px">QR কোডটি স্ক্যান করুন ➜</i></span><div class="qb"><img src="${qr}">f বাংলার খবর</div></div></div>
<div class="dstrip z"><span>${plan.dateBn2}</span><span class="mid">সত্যের সন্ধানে অক্লান্ত</span><span>${plan.bangla} বঙ্গাব্দ</span></div>`;
  return `<div class="hdr z"><div class="lg"><img src="${logo}"></div><div class="sec">${sec}</div><div class="r"><div>${plan.dateBn2}<br>পৃষ্ঠা ${bn(n)}<br><span class="pill">ফেসবুকে ফলো করতে স্ক্যান করুন ➜</span></div><img src="${qr}"></div></div>`;
}
const foot = n => `<div class="foot z"><span>দৈনিক বাংলার খবর ২৪</span><span>পৃষ্ঠা ${bn(n)}</span><span>${plan.dateBn2}</span></div>`;
const bodyTop = n => n === 1 ? 160 + 38 + 14 : 100 + 16;
const bodyBot = n => n === 1 ? H - 44 - 84 - 16 : H - 46;
const imgsrc = id => 'file://' + E + '/img/' + id + '.jpg';
const ORD = ['', 'প্রথম', 'দ্বিতীয়', 'তৃতীয়', 'চতুর্থ'];
function storyHTML(id, o) { // o: {hs, img, cont, sep, thumb, lead}
  const s = N[id], rid = id.replace(/^c/, '');
  const kk = !o.cont && s.kick ? `<div class="kk">${s.kick}</div>` : '';
  const fit = o.cont ? `data-fit="fill" data-max="44"` : (o.thumb ? `data-fit="fill" data-max="34"` : `data-fit="fill" data-max="${o.hmax || 54}"`);
  const h2 = o.hs ? `<h2 ${fit} style="font-size:${o.hs}px">${esc(s.title)}</h2>` : '';
  const fig = o.img ? `<figure><img src="${imgsrc(rid)}"><figcaption>${s.cap || 'ছবি: সংগৃহীত'}</figcaption></figure>` : '';
  const by = o.cont ? '' : `<div class="by">${esc(s.by)}</div>`;
  const ct = o.cont ? `<div class="ct">${ORD[o.from]} পাতার পর</div>` : '';
  const top = o.thumb && o.img ? `<div class="th">${fig}<div class="tt">${kk}${h2}<div class="by">${esc(s.by)}</div></div></div><div class="rl"></div>` : (o.lead ? `${fig}${by}` : `${ct}${kk}${h2}${fig}${by}`);
  return `<div class="st${o.sep ? ' sep' : ''}" data-id="${id}" data-kind="${o.kind}">${top}<div class="bd"></div></div>`;
}
const adHTML = (f, sep) => `<div class="ad"><div class="lb">বিজ্ঞাপন</div><img src="file://${A}/${f}"></div>`;
const colHTML = (items, w, hs, thumb) => `<div class="col" style="width:${w}px">${items.map((it, i) => it.ad ? adHTML(it.ad, i > 0) : storyHTML(it.replace('!', ''), { hs, thumb, img: !it.endsWith('!'), sep: i > 0, kind: 'a' })).join('')}</div>`;

const WM = [[80, 420], [470, 820], [120, 1180]].map(([x, y]) => `<img class="wm" style="left:${x}px;top:${y}px" src="file://${A}/wm.png">`).join('');
const BLOOD = `<div class="blood"><div class="tp"><div class="s">দৈনিক বাংলার খবর ২৪ · নতুন বিভাগ</div><div class="t">🩸 এক ব্যাগ রক্ত, একটি জীবন</div><div class="d">মাধবপুরের সকল রক্তদান সংগঠন ও স্বেচ্ছাসেবী রক্তদাতাদের এক জায়গায় আনতে চালু হলো <b>“রক্তদান”</b> বিভাগ</div></div><div class="bx"><div><div class="h">🏥 সংগঠনের তথ্য দিন</div><img src="file://${A}/qr_org.png">সভাপতি/সম্পাদক পূরণ করবেন<br>banglarkhabor24.com/blood-org-form</div><div><div class="h">🩸 রক্তদাতা হিসেবে যুক্ত হোন</div><img src="file://${A}/qr_donor.png">প্রত্যেক সদস্য নিজে পূরণ করবেন<br>banglarkhabor24.com/blood-donor-form</div></div><div class="ck">✅ সময় লাগবে মাত্র ১-২ মিনিট &nbsp; ✅ আপনার সম্মতি ছাড়া কোনো তথ্য প্রকাশ করা হবে না</div><div class="ft">কিউআর কোড স্ক্যান করে ফর্ম পূরণ করুন<span>হোয়াটসঅ্যাপ: ০১৭৬৫৩৫৯২২৫</span></div></div>`;
function fixedPage(p) { // pages 1-4
  const top = bodyTop(p.n), bot = bodyBot(p.n);
  let inner;
  if (p.n === 1) {
    const L = N[p.lead];
    inner = `<div class="body" style="top:${top}px;height:${bot - top}px;flex-direction:column;gap:0"><div class="lead" id="lh">${L.kick ? `<div class="kk">${L.kick}</div>` : ''}<h1 data-fit="fill" data-max="96" data-min="56">${esc(L.title)}</h1></div>
<div style="display:flex;gap:${GAP}px;flex:1;min-height:0;border-top:2px solid #222;padding-top:14px"><div class="col" style="width:${HALF}px">${storyHTML(p.lead, { hs: 0, img: true, lead: true, kind: 'lead' })}${BLOOD}</div>${colHTML(p.right, HALF, 29, true)}</div></div>
<div class="adband z"><span class="tg">বিজ্ঞাপন</span><div style="flex:1"><div class="nm">বাবুল সিসিটিভি অ্যান্ড নেটওয়ার্ক</div><div class="ad2">আপনার সুরক্ষার জন্য সকল প্রকার সিসিটিভি ও নেটওয়ার্ক সার্ভিস এখানে · ঠিকানা: নোয়াপাড়া মধ্যবাজার, মাধবপুর, হবিগঞ্জ</div></div><div class="ph">০১৭১১-৬৭২৭০২</div></div>`;
  } else inner = `<div class="body" style="top:${top}px;height:${bot - top}px">${colHTML(p.left, HALF, 32)}${colHTML(p.right, HALF, 32)}</div>`;
  return HEAD + `<div class="page">${WM}${header(p.n, p.sec)}${inner}${foot(p.n)}</div></body></html>`;
}

// ---------- in-page functions ----------
function inFit(arg) {
  const { N, ks, jumps, tg, promo } = arg; const out = {}; const PR = eval(promo);
  const words = id => N[id].paras.map(p => p.split(/\s+/).filter(Boolean));
  const fill = (bd, id, k, jump) => {
    const ws = words(id); let left = k, html = '';
    const all = ws.flat(), t = all.slice(0, k); html = '<p>' + t.join(' ') + (t.length < all.length ? ' …' : '') + '</p>';
    if (jump) html += `<div class="jump">বাকি অংশ দেখুন পৃষ্ঠা ${jump} ►</div>`;
    bd.innerHTML = html;
  };
  const lines = e => Math.round(e.offsetHeight / parseFloat(getComputedStyle(e).lineHeight));
  const shrink = (e, max, min) => { let f = parseFloat(getComputedStyle(e).fontSize); while (lines(e) > max && f > min) { f -= 1; e.style.fontSize = f + 'px'; } };
  window.fitAll();

  const cols = [...document.querySelectorAll('.col')];
  for (const col of cols) {
    const sts = [...col.querySelectorAll(':scope>.st')];
    sts.forEach(st => fill(st.querySelector('.bd'), st.dataset.id, 1e9, ''));
    const kids = [...col.children], Hc = col.clientHeight;
    const tot = kids.reduce((a, e) => a + e.offsetHeight, 0);
    const cut = tot > Hc;
    if (!cut) { sts.forEach(st => out[st.dataset.id] = { k: 1e9, total: words(st.dataset.id).flat().length });
      // short column: absorb empty space by growing photos, then line spacing
      const cnt = () => [...col.children].reduce((a, e) => a + e.offsetHeight, 0);
      let slack = Hc - cnt() - 4 * kids.length;
      const figs = [...col.querySelectorAll('.st figure img')];
      if (slack > 20 && figs.length) { const ih = figs.reduce((a, e) => a + e.offsetHeight, 0); const g = Math.min(1.7, 1 + slack / ih);
        figs.forEach(f => { f.style.aspectRatio = 'auto'; f.style.height = (f.offsetHeight * g).toFixed(1) + 'px'; }); slack = Hc - cnt() - 4 * kids.length; }
      const bds = [...col.querySelectorAll('.bd')];
      if (slack > 20 && bds.length) { const th = bds.reduce((a, e) => a + e.offsetHeight, 0); let f = Math.min(1.25, 1 + slack / th);
        for (let it = 0; it < 30; it++) { bds.forEach(b => b.style.lineHeight = (1.55 * f).toFixed(3)); if (Hc - cnt() - 4 * kids.length < 0) f -= 0.01; else break; } }
      slack = Hc - cnt() - 4 * kids.length;
      if (slack > 130 && tg) { col.insertAdjacentHTML('beforeend', PR(slack - 16, tg)); }
      continue; }
    const other = kids.filter(e => !e.classList.contains('st')).reduce((a, e) => a + e.offsetHeight, 0);
    const fixed = sts.map(st => st.offsetHeight - st.querySelector('.bd').offsetHeight);
    const nat = sts.map(st => st.querySelector('.bd').offsetHeight);
    const B = Hc - other - fixed.reduce((a, b) => a + b, 0) - 6 * sts.length - 8;
    const sumN = nat.reduce((a, b) => a + b, 0);
    sts.forEach((st, i) => {
      const id = st.dataset.id, bd = st.querySelector('.bd'), total = words(id).flat().length;
      const jump = (jumps && jumps[id]) || '৫';
      let k;
      if (ks && ks[id] != null) k = ks[id];
      else {
        const bh = Math.floor(B * nat[i] / sumN);
        bd.style.height = bh + 'px'; bd.style.columnFill = 'auto'; bd.style.overflow = 'hidden';
        let lo = 0, hi = total;
        while (lo < hi) { const m = (lo + hi + 1) >> 1; fill(bd, id, m, jump); if (bd.scrollWidth > bd.clientWidth + 1 || bd.scrollHeight > bh + 1) hi = m - 1; else lo = m; }
        k = lo; bd.style.height = ''; bd.style.columnFill = ''; bd.style.overflow = '';
      }
      fill(bd, id, k, k >= total ? '' : jump);
      out[id] = { k, total };
    });
    if (!ks) for (let pass = 0; pass < 3; pass++) {
      const cs = sts.filter(st => out[st.dataset.id].k < out[st.dataset.id].total); if (!cs.length) break;
      const slack = col.clientHeight - [...col.children].reduce((a, e) => a + e.offsetHeight, 0); if (slack < 8) break;
      for (const st of cs) { const id = st.dataset.id, bd = st.querySelector('.bd'), total = out[id].total, jump = (jumps && jumps[id]) || '৫';
        const bh = bd.offsetHeight + Math.floor(slack / cs.length) - 2; bd.style.height = bh + 'px'; bd.style.columnFill = 'auto'; bd.style.overflow = 'hidden';
        let lo = out[id].k, hi = total; while (lo < hi) { const m = (lo + hi + 1) >> 1; fill(bd, id, m, jump); if (bd.scrollWidth > bd.clientWidth + 1 || bd.scrollHeight > bh + 1) hi = m - 1; else lo = m; }
        bd.style.height = ''; bd.style.columnFill = ''; bd.style.overflow = ''; out[id].k = lo; fill(bd, id, lo, lo >= total ? '' : jump); }
    }
    if (!ks) { let g = 0; const cs = sts.filter(st => out[st.dataset.id].k < out[st.dataset.id].total);
      while (col.scrollHeight > col.clientHeight + 1 && cs.length && g++ < 200) { const st = cs[g % cs.length], id = st.dataset.id; out[id].k -= 3; fill(st.querySelector('.bd'), id, out[id].k, (jumps && jumps[id]) || '৫'); } }
  }
  return out;
}
function inRects() {
  const pg = document.querySelector('.page').getBoundingClientRect();
  const r = e => { const b = e.getBoundingClientRect(); return [b.left / pg.width * 100, b.top / pg.height * 100, b.width / pg.width * 100, b.height / pg.height * 100].map(v => +v.toFixed(3)); };
  const items = [...document.querySelectorAll('.st')].map(st => {
    const rects = [];
    if (st.dataset.kind === 'lead') rects.push(r(document.getElementById('lh')));
    rects.push(r(st)); return { id: st.dataset.id, kind: st.dataset.kind, rects };
  });
  const over = [...document.querySelectorAll('.col,.half')].map((c, i) => [i, c.scrollHeight - c.clientHeight, c.clientHeight]).filter(v => v[1] > 1);
  return { items, over };
}
function inCards() {
  return [...document.querySelectorAll('.st')].map(st => {
    const q = sel => st.querySelector(sel);
    const lead = st.dataset.kind === 'lead', lh = document.getElementById('lh');
    const h = lead ? lh.querySelector('h1') : q('h2');
    return { id: st.dataset.id, kind: st.dataset.kind, lead,
      kk: (lead ? (lh.querySelector('.kk') || {}).textContent : (q('.kk') || {}).textContent) || '',
      title: h ? (h.dataset.t || h.textContent).trim() : '', img: (q('figure img') || {}).src || '', cap: (q('figcaption') || {}).textContent || '',
      by: (q('.by') || {}).textContent || '', ct: (q('.ct') || {}).textContent || '', bd: q('.bd').innerHTML };
  });
}
function inMeasure() { return [...document.querySelectorAll('.mi')].map(e => e.offsetHeight); }
function inStretch([C, tg, promo]) { const PR = eval(promo);
  const res = [];
  for (const h of document.querySelectorAll('.half')) {
    const content = () => [...h.children].reduce((a, e) => a + e.offsetHeight, 0);
    let slack = C - content();
    const bds = [...h.querySelectorAll('.bd')];
    const th = bds.reduce((a, e) => a + e.offsetHeight, 0);
    if (slack < 0 && th) { bds.forEach(b => b.style.lineHeight = (1.55 * Math.max(0.9, 1 + slack / th)).toFixed(3)); slack = C - content(); }
    if (slack > 0 && th) {
      let f = Math.min(1.3, 1 + slack / th);
      for (let it = 0; it < 6; it++) { bds.forEach(b => b.style.lineHeight = (1.55 * f).toFixed(3)); const s = C - content(); if (s < 0) { f -= 0.004; } else break; }
      slack = C - content();
    }
    const figs = [...h.querySelectorAll('figure img')];
    if (slack > 0 && figs.length) {
      const ih = figs.reduce((a, e) => a + e.offsetHeight, 0); const g = Math.min(1.6, 1 + slack / ih);
      figs.forEach(f => { f.style.aspectRatio = 'auto'; f.style.height = (f.offsetHeight * g).toFixed(1) + 'px'; });
      slack = C - content();
    }
    if (slack > 130 && tg) { h.insertAdjacentHTML('beforeend', PR(slack - 16, tg)); slack = C - content(); }
    res.push(Math.round(slack));
  }
  return res;
}
// ---------- per-story cards (shown when a reader taps a story) ----------
const CW = 700;
const cardHTML = (d, n) => HEAD.replace('<body>', `<body style="width:${CW}px">`) + `<div id="card" style="width:${CW}px;background:#fff;position:relative;font-family:Lalsalu;overflow:hidden">
<img src="file://${A}/wm.png" style="position:absolute;width:520px;left:90px;top:420px;opacity:.06;transform:rotate(-18deg)">
<div style="background:var(--navy);height:118px;display:flex;align-items:center;justify-content:space-between;padding:0 14px">
<img src="${logo}" style="height:96px">
<div style="display:flex;align-items:center;gap:12px"><div style="color:#fff;text-align:right;font-size:16px;line-height:1.5">দৈনিক বাংলার খবর ই-পেপার<br>${plan.dateBn2}<br><span class="pill" style="font-size:16px">পৃষ্ঠা ${bn(n)}</span></div>
<div style="background:#fff;border-radius:6px;padding:4px 4px 1px;text-align:center;font-size:9px;color:#1f4e8c"><img src="${qr}" style="width:84px;height:84px;display:block">ফেসবুকে আমরা</div></div></div>
<div class="st z" style="padding:12px 14px 6px">
${d.ct ? `<div class="ct">${esc(d.ct)}</div>` : ''}${d.kk ? `<div class="kk">${esc(d.kk)}</div>` : ''}
<h2 data-fit="fill" data-max="${d.lead ? 60 : 44}" style="color:${d.lead ? 'var(--red)' : (d.kind === 'a' && n === 1 ? 'var(--navy)' : 'var(--ink)')};font-size:40px;border-bottom:${d.lead ? '2px solid #222;padding-bottom:10px' : '0'}">${esc(d.title)}</h2>
${d.img ? `<figure style="margin-top:8px"><img src="${d.img}"><figcaption>${esc(d.cap)}</figcaption></figure>` : ''}
${d.by ? `<div class="by">${esc(d.by)}</div>` : ''}
<div class="bd" style="font-size:17px">${d.bd}</div></div>
<div style="background:var(--navy);color:#fff;display:flex;justify-content:space-between;padding:8px 14px;font-size:14px;margin-top:6px"><span>banglarkhabor24.com</span><span>সত্যের সন্ধানে অক্লান্ত</span></div></div></body></html>`;
let CARDPG = null;
async function renderCards(pg, n, outDir) {
  const ds = await pg.evaluate(inCards);
  fs.mkdirSync(outDir, { recursive: true });
  const cp = CARDPG;
  for (const d of ds) {
    const sid = d.id.replace(/^c/, ''), name = d.kind === 'f' ? `${TAG}-${sid}.jpg` : `${TAG}-${sid}-${d.kind === 'b' ? 'b' : 'a'}.jpg`;
    fs.writeFileSync(E + '/_c.html', cardHTML(d, n)); await cp.goto('file://' + E + '/_c.html');
    await cp.evaluate(() => document.fonts.ready); await cp.evaluate(() => window.fitAll()); await cp.waitForTimeout(80);
    await (await cp.$('#card')).screenshot({ path: `${outDir}/${name}`, type: 'jpeg', quality: 86 });
  }
}
// ---------- main ----------
(async () => {
  const br = await chromium.launch();
  CARDPG = await br.newPage({ viewport: { width: CW, height: 1000 }, deviceScaleFactor: 2 });
  const pg = await br.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: plan.dsf || 3 });
  const outDir = E + '/out'; fs.mkdirSync(outDir, { recursive: true });
  const setc = async html => { fs.writeFileSync(E + '/_p.html', html); await pg.goto('file://' + E + '/_p.html'); await pg.evaluate(() => document.fonts.ready); await pg.waitForTimeout(150); };
  // pass 1: cut pages 1-4
  const fixedP = plan.pages.filter(p => p.n <= 4), cuts = {};
  for (const p of fixedP) { await setc(fixedPage(p)); Object.assign(cuts, await pg.evaluate(inFit, { N, tg: TG, promo: PROMO.toString() })); }
  // continuation remainders
  const rem = id => { let k = cuts[id].k; const ps = []; for (const p of N[id].paras) { const w = p.split(/\s+/).filter(Boolean); if (k >= w.length) { k -= w.length; continue; } ps.push(w.slice(k).join(' ')); k = 0; } return ps; };
  const order = fixedP.flatMap(p => p.n === 1 ? [p.lead, ...p.right] : [...p.left, ...p.right]).filter(x => typeof x === 'string').map(x => x.replace('!', ''));
  const SRC = {}; fixedP.forEach(p => (p.n === 1 ? [p.lead, ...p.right] : [...p.left, ...p.right]).forEach(x => typeof x === 'string' && (SRC[x.replace('!', '')] = p.n)));
  const items = [];
  for (const id of order) if (cuts[id].k < cuts[id].total) items.push({ id, cont: true, paras: rem(id) });
  for (const id of plan.full || []) items.push({ id, cont: false, paras: N[id].paras });
  const contN = {}; order.forEach(id => contN[id] = { ...N[id], paras: cuts[id].k < cuts[id].total ? rem(id) : [] });
  const NN = { ...N, ...Object.fromEntries(items.filter(i => i.cont).map(i => ['c' + i.id, { ...N[i.id], paras: i.paras }])) };
  const HW = (W - 2 * PX - 22) / 2, C = bodyBot(5) - bodyTop(5);
  const itemHTML = (it, sep) => it.imp ? `<div class="imp${sep ? '' : ''}">${plan.imprint}</div>` :
    storyHTML(it.cont ? 'c' + it.id : it.id, { hs: it.cont ? 32 : 40, hmax: 56, img: !it.cont || !!it.pic, cont: it.cont, from: SRC[it.id], sep, kind: it.cont ? 'b' : 'f' });
  const fullBodies = async () => pg.evaluate(NN => { { for (const st of document.querySelectorAll('.st')) st.querySelector('.bd').innerHTML = '<p>' + NN[st.dataset.id].paras.join(' ') + '</p>'; } window.fitAll(); }, NN);
  if (process.env.CARDS_ONLY) { // re-make story cards for an edition already on the site; PAGEOF = {id: page of its continuation}
    const PO = JSON.parse(process.env.PAGEOF), jumps = Object.fromEntries(Object.entries(PO).map(([k, v]) => [k, bn(v)]));
    const ks = Object.fromEntries(Object.entries(cuts).map(([k, v]) => [k, v.k]));
    for (const k in NN) if (!N[k]) N[k] = NN[k];
    for (const p of fixedP) { await setc(fixedPage(p)); await pg.evaluate(inFit, { N, ks, jumps, tg: '', promo: PROMO.toString() }); await renderCards(pg, p.n, E + '/cards'); }
    for (const it of items.filter(i => i.cont && PO[i.id])) {
      await setc(HEAD + `<div class="page" style="height:auto"><div class="col half" style="width:${HW}px">${itemHTML(it, false)}</div></div></body></html>`);
      await fullBodies(); await renderCards(pg, PO[it.id], E + '/cards');
    }
    await br.close(); return;
  }
  // measure
  const all = [...items, { imp: true }];
  for (const k in NN) if (!N[k]) N[k] = NN[k];
  await setc(HEAD + `<div style="width:${HW}px">${all.map(it => `<div class="mi" style="width:${HW}px">${itemHTML(it, true)}</div>`).join('')}</div></body></html>`);
  await fullBodies();
  let hs = await pg.evaluate(inMeasure); all.forEach((it, i) => it.h = hs[i]);
  let tot = hs.reduce((a, b) => a + b, 0);
  { // few stories: show photos with continued parts too, if that does not add a page
    const CX = C - (+process.env.MG || 30), np = t => Math.max(1, Math.min(4, Math.ceil(t / (2 * CX * 0.9))));
    const n0 = np(tot);
    if (tot / (2 * CX * n0) < 0.8) {
      all.forEach(it => { if (it.cont && fs.existsSync(E + '/img/' + it.id + '.jpg')) it.pic = true; });
      await setc(HEAD + `<div style="width:${HW}px">${all.map(it => `<div class="mi" style="width:${HW}px">${itemHTML(it, true)}</div>`).join('')}</div></body></html>`);
      await fullBodies(); const h2 = await pg.evaluate(inMeasure); const t2 = h2.reduce((a, b) => a + b, 0);
      // give photos to continued parts one by one while the pages stay within ~90%
      const lim = 2 * CX * n0 * 0.9; let cur = tot; const gain = all.map((it, i) => [i, h2[i] - hs[i]]).filter(g => g[1] > 0).sort((a, b) => b[1] - a[1]);
      all.forEach(it => delete it.pic); let k = 0;
      for (const [i, g] of gain) if (cur + g <= lim) { all[i].pic = true; all[i].h = h2[i]; cur += g; k++; }
      tot = cur; hs = all.map(it => it.h); console.log('CONT PHOTOS', k);
    }
  }
  console.log('CAP', C, 'x8 =', C * 8, 'need', tot, 'items', all.map(i => (i.imp ? 'IMP' : (i.cont ? 'c' : '') + i.id) + ':' + i.h).join(' '));
  if (process.env.MEASURE) { await br.close(); return; }
  // pack: imprint fixed to last half; LPT on the rest
  const imp = all.at(-1); let rest0 = all.slice(0, -1); const CAPX = C - (+process.env.MG || 30);
  let best = null;
  let NP = 4; // owner: always 8 pages; empty space gets photos, house ads and QR boxes
  for (let drop = 0; !best && drop < 40; drop++) {
  if (drop && NP < 4) { NP++; drop = 0; }
  else if (drop) { const li = rest0.map(x => !x.cont).lastIndexOf(true); if (li < 0) break; console.log('DROP', rest0[li].id); rest0.splice(li, 1); }
  for (let t = 0; t < 4000; t++) {
    const hv = Array.from({ length: 2 * NP }, () => ({ its: [], h: 0 })); hv[2 * NP - 1].its.push(imp); hv[2 * NP - 1].h = imp.h;
    const ord = rest0.map(x => [x, x.h * (t ? 0.75 + Math.random() * 0.5 : 1)]).sort((a, b) => b[1] - a[1]).map(x => x[0]);
    let ok = true;
    for (const it of ord) { const f = hv.filter(x => x.h + it.h <= CAPX); if (!f.length) { ok = false; break; } f.sort((a, b) => a.h - b.h); const pick = (t && Math.random() < 0.3 && f[1]) ? f[1] : f[0]; pick.its.push(it); pick.h += it.h; }
    if (!ok) continue; const sc = Math.max(...hv.map(x => x.h)) - Math.min(...hv.map(x => x.h));
    if (!best || sc < best.sc) best = { hv, sc };
  }
  }
  if (!best) { console.log('NOFIT'); process.exit(2); }
  const halves = best.hv;
  halves.forEach(x => x.its.sort((a, b) => (a.imp ? 2 : a.cont ? 0 : 1) - (b.imp ? 2 : b.cont ? 0 : 1)));
  console.log('FILL', halves.map(x => Math.round(x.h / C * 100) + '%').join(' '));
  const jumps = {}; halves.forEach((x, i) => x.its.forEach(it => { if (it.cont) jumps[it.id] = bn(5 + (i >> 1)); }));
  const ks = Object.fromEntries(Object.entries(cuts).map(([k, v]) => [k, v.k]));
  const map = {};
  // pass 2 pages 1-4
  for (const p of fixedP) {
    await setc(fixedPage(p)); await pg.evaluate(inFit, { N, ks, jumps, tg: TG, promo: PROMO.toString() });
    const r = await pg.evaluate(inRects); map[p.n] = r.items; if (r.over.length) console.log('OVER p' + p.n, r.over);
    await pg.screenshot({ path: `${outDir}/${TAG}-p${p.n}.jpg`, type: 'jpeg', quality: 90 });
    await renderCards(pg, p.n, E + '/cards');
  }
  TOTALP = 4 + NP; console.log('PAGES', TOTALP);
  for (let n = 5; n <= TOTALP; n++) {
    const sec = plan.pages.find(p => p.n === n).sec, top = bodyTop(n);
    const hv = [halves[(n - 5) * 2], halves[(n - 5) * 2 + 1]];
    await setc(HEAD + `<div class="page">${WM}${header(n, sec)}<div class="body" style="top:${top}px;height:${C}px">${hv.map(x => `<div class="col half" style="width:${HW}px;height:${C}px">${x.its.map((it, i) => itemHTML(it, i > 0)).join('')}</div>`).join('')}</div>${foot(n)}</div></body></html>`);
    await fullBodies();
    console.log('SLACK p' + n, await pg.evaluate(inStretch, [C, TG, PROMO.toString()]));
    const r = await pg.evaluate(inRects); map[n] = r.items; if (r.over.length) console.log('OVER p' + n, r.over);
    await pg.screenshot({ path: `${outDir}/${TAG}-p${n}.jpg`, type: 'jpeg', quality: 90 });
    await renderCards(pg, n, E + '/cards');
  }
  fs.writeFileSync(E + '/map.json', JSON.stringify(map));
  await br.close();
})();
