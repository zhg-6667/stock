# -*- coding: utf-8 -*-
"""三大运营商 A股 分红/股息率/估值。A股直连(清代理)。
移动600941(2022上市)/电信601728(2021上市)/联通600050(老股,十年全)。"""
import sys, os, time
for k in ("HTTP_PROXY","HTTPS_PROXY","http_proxy","https_proxy","ALL_PROXY","all_proxy"):
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = "*"
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
import akshare as ak
import pandas as pd
from datetime import datetime

def retry(fn, n=4, wait=1.2):
    last=None
    for _ in range(n):
        try: return fn()
        except Exception as e: last=e; time.sleep(wait)
    raise last

STOCKS = [("600941","中国移动"),("601728","中国电信"),("600050","中国联通")]

for code,name in STOCKS:
    print("="*74)
    px = retry(lambda: ak.stock_zh_a_daily(symbol="sh"+code, adjust=""))
    px = px.copy(); px["date"]=pd.to_datetime(px["date"]); px=px.sort_values("date").reset_index(drop=True)
    cur=px.iloc[-1]["close"]; curd=px.iloc[-1]["date"].date()
    def close_before(d):
        s=px[px["date"]<pd.Timestamp(d)]; return float(s.iloc[-1]["close"]) if len(s) else None
    pe=pb="N/A"
    try: pe=ak.stock_zh_valuation_baidu(symbol=code,indicator="市盈率(TTM)",period="近一年").iloc[-1]["value"]
    except Exception: pass
    try: pb=ak.stock_zh_valuation_baidu(symbol=code,indicator="市净率",period="近一年").iloc[-1]["value"]
    except Exception: pass
    print(f"{name} {code}  现价 {cur}（{curd}）  PE_TTM {pe}  PB {pb}")
    d=retry(lambda: ak.stock_history_dividend_detail(symbol=code, indicator="分红"))
    pay=[c for c in d.columns if "派息" in c][0]; ex=[c for c in d.columns if "除权除息" in c][0]
    d=d.dropna(subset=[ex]).copy(); d[ex]=pd.to_datetime(d[ex],errors="coerce"); d=d.dropna(subset=[ex])
    d[pay]=pd.to_numeric(d[pay],errors="coerce").fillna(0.0)
    d=d[(d[ex]>="2015-06-01")&(d[pay]>0)].sort_values(ex)
    print(f"  {'除息日':<12}{'每10股派息':>12}{'每股':>8}{'除息前价':>10}{'当次股息率':>11}")
    rows=[]
    for _,r in d.iterrows():
        exd=r[ex].date(); per10=float(r[pay]); dps=per10/10; base=close_before(exd)
        dy=(dps/base*100) if base else None; rows.append((exd,dps,dy))
        print(f"  {str(exd):<12}{per10:>12.3f}{dps:>8.3f}{(f'{base:.2f}' if base else 'NA'):>10}{(f'{dy:.2f}%' if dy else 'NA'):>11}")
    lastyr=pd.Timestamp(datetime.today())-pd.Timedelta(days=370)
    ry=sum(dps for exd,dps,dy in rows if pd.Timestamp(exd)>=lastyr)
    tot=sum(dps for exd,dps,dy in rows)
    print(f"  >> 近一年每股分红 {ry:.3f} -> 当前股息率 {ry/cur*100:.2f}%  | 区间累计每股分红 {tot:.3f}")
