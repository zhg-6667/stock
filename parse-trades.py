# -*- coding: utf-8 -*-
import json, re, quopri, sys, csv, os
from html.parser import HTMLParser
from email.utils import parsedate_to_datetime

sys.stdout.reconfigure(encoding='utf-8')

JSON_PATH = "C:/project/股票/all-bodies.json"
CSV_PATH  = "C:/project/股票/trades.csv"
MD_PATH   = "C:/project/股票/trades.md"

# read with gbk first (because bash redirect from PowerShell converts utf-8 to gbk)
def load_json():
    for enc in ['utf-8','gbk','gb18030','utf-16']:
        try:
            with open(JSON_PATH,'r',encoding=enc) as f:
                return json.load(f)
        except Exception as e:
            continue
    raise RuntimeError("cannot decode JSON file")

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('style','script'): self.skip += 1
        if tag in ('br','tr','p','div','td','li'): self.parts.append('\n')
    def handle_endtag(self, tag):
        if tag in ('style','script') and self.skip>0: self.skip -= 1
        if tag in ('tr','p','div','li'): self.parts.append('\n')
    def handle_data(self, data):
        if self.skip == 0: self.parts.append(data)
    def text(self): return ''.join(self.parts)

def decode_body(raw):
    # strip MIME headers (everything up to first blank line within the part)
    # The body starts with `------=_Part...\nContent-Type: ...\n\n<html>`
    parts = re.split(r'\r?\n\r?\n', raw, maxsplit=1)
    mime_body = parts[1] if len(parts) > 1 else raw
    try:
        decoded = quopri.decodestring(mime_body).decode('utf-8', errors='replace')
    except Exception:
        decoded = mime_body
    p = TextExtractor()
    p.feed(decoded)
    txt = p.text()
    txt = re.sub(r'[ \t]+', ' ', txt)
    txt = re.sub(r'\n\s*\n+', '\n', txt)
    return txt

# Robust trade-line regex
# Pattern: 买入/卖出<name>（<code>）已成交，成交价<price><cur>，成交数量<qty>股，成交金额<amt><cur>，成交时间HH:MM:SS
TRADE_RE = re.compile(
    r'(买入|卖出)\s*(.+?)\s*[（(]([^）)]+)[）)]\s*已成交\s*[，,]\s*'
    r'成交价\s*([\d.,]+)\s*([^\s，,]+?)\s*[，,]\s*'
    r'成交数量\s*([\d,]+)\s*股\s*[，,]\s*'
    r'成交金额\s*([\d.,]+)\s*([^\s，,]+?)\s*[，,]\s*'
    r'成交时间\s*(\d{1,2}:\d{2}:\d{2})'
)

data = load_json()
print(f"Loaded {len(data)} email records", file=sys.stderr)

trades = []
matched_subjects = 0
for r in data:
    subj = r.get('Subject','') or ''
    if '交易成交' not in subj:
        continue
    matched_subjects += 1
    body = r.get('Body','') or ''
    if not body:
        continue
    text = decode_body(body)
    # email date -> Asia/Shanghai date
    date_str = r.get('Date','')
    try:
        dt = parsedate_to_datetime(date_str)
        ymd = dt.strftime('%Y-%m-%d')
    except Exception:
        ymd = ''

    matches = list(TRADE_RE.finditer(text))
    if not matches:
        # debug: print first 300 chars of text
        print(f"NO MATCH for date={date_str}", file=sys.stderr)
        print(text[:400], file=sys.stderr)
        print("---", file=sys.stderr)
        continue
    for m in matches:
        side, name, code, price, price_cur, qty, amt, amt_cur, t = m.groups()
        trades.append({
            'date': ymd,
            'time': t,
            'side': side,
            'name': name.strip(),
            'code': code.strip(),
            'price': price.replace(',',''),
            'qty': qty.replace(',',''),
            'amount': amt.replace(',',''),
            'currency': amt_cur.strip(),
            'mail_date': date_str,
        })

print(f"Subjects matched: {matched_subjects}", file=sys.stderr)
print(f"Trades parsed: {len(trades)}", file=sys.stderr)

# dedupe (same date+time+code+side+qty+price could appear if multiple mails reference same)
seen = set()
unique = []
for t in trades:
    key = (t['date'], t['time'], t['code'], t['side'], t['qty'], t['price'])
    if key in seen: continue
    seen.add(key)
    unique.append(t)

# sort by date+time
unique.sort(key=lambda x: (x['date'], x['time']))

# CSV
with open(CSV_PATH, 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=['date','time','side','name','code','price','qty','amount','currency'])
    w.writeheader()
    for t in unique:
        row = {k: t[k] for k in w.fieldnames}
        w.writerow(row)

# Markdown
with open(MD_PATH, 'w', encoding='utf-8') as f:
    f.write(f"# 哈富交易成交流水（共 {len(unique)} 笔）\n\n")
    f.write("| 日期 | 时间 | 方向 | 股票 | 代码 | 价格 | 数量 | 成交金额 | 币种 |\n")
    f.write("|------|------|------|------|------|------|------|----------|------|\n")
    for t in unique:
        f.write(f"| {t['date']} | {t['time']} | {t['side']} | {t['name']} | {t['code']} | {t['price']} | {t['qty']} | {t['amount']} | {t['currency']} |\n")

print(f"Wrote {CSV_PATH} and {MD_PATH}", file=sys.stderr)
print(f"Total unique trades: {len(unique)}")
