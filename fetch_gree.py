# -*- coding: utf-8 -*-
"""格力电器 000651 近十年分红与股息率分析。
分红用 stock_history_dividend_detail；价格用新浪 stock_zh_a_daily。
股息率口径：每次派息(每股) ÷ 除息前最后一个交易日收盘价(含权价)。"""
import sys, os, time
for k in ("HTTP_PROXY","HTTPS_PROXY","http_proxy","https_proxy","ALL_PROXY","all_proxy"):
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = "*"
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
import akshare as ak
import pandas as pd
from datetime import datetime

CODE = "000651"

def retry(fn, n=4, wait=1.2):
    last=None
    for _ in range(n):
        try: return fn()
        except Exception as e: last=e; time.sleep(wait)
    raise last

# 历史日线（新浪，含权口径 adjust=""）
px = retry(lambda: ak.stock_zh_a_daily(symbol="sz"+CODE, adjust=""))
px = px.copy()
px["date"] = pd.to_datetime(px["date"])
px = px.sort_values("date").reset_index(drop=True)
cur_price = px.iloc[-1]["close"]
cur_date = px.iloc[-1]["date"].date()

def close_before(d):
    sub = px[px["date"] < pd.Timestamp(d)]
    return float(sub.iloc[-1]["close"]) if len(sub) else None

# 分红明细
d = retry(lambda: ak.stock_history_dividend_detail(symbol=CODE, indicator="分红"))
pay = [c for c in d.columns if "派息" in c][0]
ex  = [c for c in d.columns if "除权除息" in c][0]
d = d.dropna(subset=[ex]).copy()
d[ex] = pd.to_datetime(d[ex], errors="coerce")
d = d.dropna(subset=[ex])
d[pay] = pd.to_numeric(d[pay], errors="coerce").fillna(0.0)
d = d[d[ex] >= "2015-06-01"].sort_values(ex)

print("="*78)
print(f"格力电器 000651  现价 {cur_price}（{cur_date}）")
print("="*78)
print(f"{'除息日':<12}{'每10股派息(元)':>14}{'每股(元)':>10}{'除息前收盘':>12}{'当次股息率':>12}")
print("-"*78)
rows=[]
for _,r in d.iterrows():
    exd = r[ex].date()
    per10 = float(r[pay])
    if per10 <= 0:
        continue
    dps = per10/10.0
    base = close_before(exd)
    dy = (dps/base*100) if base else None
    rows.append((exd, per10, dps, base, dy))
    dystr = f"{dy:.2f}%" if dy else "N/A"
    bstr = f"{base:.2f}" if base else "N/A"
    print(f"{str(exd):<12}{per10:>14.3f}{dps:>10.3f}{bstr:>12}{dystr:>12}")

# 按自然年汇总（除息日所在年份）
print("\n"+"="*78)
print("按除息日年份汇总（注：某年除息≈对应上一会计年度利润分红）")
print("-"*78)
agg = {}
for exd, per10, dps, base, dy in rows:
    y = exd.year
    agg.setdefault(y, [0.0, 0.0, []])
    agg[y][0]+=per10; agg[y][1]+=dps
    if dy: agg[y][2].append(dy)
print(f"{'年份':<8}{'每10股合计':>12}{'每股合计':>10}{'年内除息次数':>12}{'累计当次股息率':>14}")
print("-"*78)
total_dps=0
for y in sorted(agg):
    per10s, dpss, dys = agg[y]
    total_dps+=dpss
    print(f"{y:<8}{per10s:>12.3f}{dpss:>10.3f}{len(dys):>12}{sum(dys):>13.2f}%")

print("\n"+"-"*78)
# 近一年（365天）派息 / 现价
last_yr = pd.Timestamp(datetime.today()) - pd.Timedelta(days=370)
recent_dps = sum(dps for exd,per10,dps,base,dy in rows if pd.Timestamp(exd) >= last_yr)
print(f"近一年累计每股分红: {recent_dps:.3f} 元  ->  当前股息率 = {recent_dps/cur_price*100:.2f}%（现价 {cur_price}）")
print(f"近十年累计每股分红: {total_dps:.3f} 元")
