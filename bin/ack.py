"""Reply 'received' to a reporter's news message in the group. Usage: ack.py inbox/<id> [message_id ...]
Called by Claude right after deciding an item is news (not for skipped chit-chat). Sent once per message."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

d = os.path.abspath(sys.argv[1]); item = load_json(os.path.join(d, "item.json"))
ids = [int(x) for x in sys.argv[2:]] or [item["first_message_id"]]
done = set(item.get("acked", []))
for mid in ids:
    if mid in done:
        continue
    try:
        m = tg("sendMessage", chat_id=item["chat_id"], reply_to_message_id=mid, allow_sending_without_reply=True,
               text="📥 নিউজটি আমরা পেয়েছি। অল্প কিছুক্ষণের মধ্যে প্রকাশ করা হবে।")
        log(f"ack {item['id']} msg {mid} sender_chat={(m.get('sender_chat') or {}).get('title')} from={(m.get('from') or {}).get('username')}")
        done.add(mid)
    except Exception as e:
        log(f"ack failed {item['id']} {mid}: {e}")
item["acked"] = sorted(done); save_json(os.path.join(d, "item.json"), item)
