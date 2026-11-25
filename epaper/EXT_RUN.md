# Nightly outside-news run (23:30 Dhaka, before the 00:05 e-paper build)
Owner rule 2026-11-25: news our site lacks for an 8-page paper (~22) come from outside sites (bdnews24 now; Kalbela and
Banglanews24 block code). Rewrite in our own words, source named. No permission needed each night. Keep it lean.

1. DAY = tomorrow's date in Dhaka (`TZ=Asia/Dhaka date -d tomorrow +%F`). If state/epaper_ext/DAY.json exists, stop.
2. `python3 epaper/ext_fill.py pool DAY 16` -> state/epaper_ext/DAY.pool.json (key, desk, title, text, img, src, srcimg).
3. Read it once. Skip: rumours, communal/hate, rape/suicide/corpse details, stories about the source outlet itself,
   opinion/feature pieces, one-sided political attacks. Take up to 14, mixed over জাতীয়/আন্তর্জাতিক/সারাদেশ/খেলা/বিনোদন.
4. For each write {key, desk, title, paras, img, src, srcimg} (copy key/desk/img/src/srcimg from the pool):
   title 30-55 chars, factual; paras = 3 paragraphs, 2-3 sentences each, ~120-150 words total, standard Bangla,
   own sentence structure (never copy source sentences), Bangla digits; never invent or change names, numbers,
   places, dates or quotes. Do not add a source line (code adds "তথ্যসূত্র: ...").
5. Save as state/epaper_ext/DAY.json (a JSON list, ensure_ascii False), delete the .pool.json, commit
   "epaper ext DAY" and push to main. Build at 00:05 uses as many as it needs.
6. Do not message the owner. If the source fails, just stop (the paper is built from our own news).
