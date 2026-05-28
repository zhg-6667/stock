# -*- coding: utf-8 -*-
"""红利组合估值/股息核验：全程国内源直连。
ETF/个股价用新浪源(绕开 eastmoney 限流)；个股 PE/PB 用百度；
个股股息率用 stock_history_dividend_detail 自算(近一年派息/现价)；
红利指数 PE/股息率用中证官方；固收锚用中债国债收益率曲线。"""
import sys, os, time
for k in ("HTTP_PROXY","HTTPS_PROXY","http_proxy","https_proxy","ALL_PROXY","all_proxy"):
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = "*"
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

def retry(fn, n=4, wait=1.2):
    last = None
    for _ in range(n):
        try:
            return fn()
        except Exception as e:
            last = e; time.sleep(wait)
    raise last

ETFS = {"510880":"上证红利ETF","512890":"红利低波ETF","515080":"中证红利ETF",
        "511990":"华宝添益(货币ETF)","511360":"海富通短融ETF","511260":"十年国债ETF"}
STOCKS = {"601398":"工商银行","600900":"长江电力","600941":"中国移动","601088":"中国神华"}
INDEXES = {"000015":"上证红利","000922":"中证红利","H30269":"红利低波"}

def sina_close(code):
    d = retry(lambda: ak.fund_etf_hist_sina(symbol="sh"+code))
    r = d.iloc[-1]; return r["close"], r["date"]

def stock_close(code):
    d = retry(lambda: ak.stock_zh_a_daily(symbol="sh"+code, adjust=""))
    r = d.iloc[-1]; return r["close"], r.name if not hasattr(r,'date') else r["date"]

def div_yield(code, price):
    """近一年现金派息合计 / 现价。"""
    d = retry(lambda: ak.stock_history_dividend_detail(symbol=code, indicator="分红"))
    pay_col = next((c for c in d.columns if "派息" in c), None)
    ex_col  = next((c for c in d.columns if "除权除息" in c), None)
    if pay_col is None or ex_col is None: return None, None
    d = d.dropna(subset=[ex_col]).copy()
    d[ex_col] = pd.to_datetime(d[ex_col], errors="coerce")
    one_yr = pd.Timestamp(datetime.today() - timedelta(days=400))
    recent = d[d[ex_col] >= one_yr]
    if recent.empty: return None, None
    per10 = pd.to_numeric(recent[pay_col], errors="coerce").sum()  # 每10股派息合计
    dps = per10 / 10.0
    return round(dps/float(price)*100, 2), recent[ex_col].max().date()

print("="*72)
print("一、ETF 最新价（新浪）")
print("-"*72)
for code,name in ETFS.items():
    try:
        c,dt = sina_close(code); print(f"  {code} {name:<16} {dt}  收盘 {c}")
    except Exception as e: print(f"  {code} {name:<16} 失败 {type(e).__name__}")
    time.sleep(0.3)

print("\n"+"="*72)
print("二、个股：现价 / 股息率(自算,近一年派息÷现价) / PE_TTM / PB")
print("-"*72)
for code,name in STOCKS.items():
    try: price,_ = stock_close(code)
    except Exception as e: price = None
    pe = pb = "N/A"
    try: pe = ak.stock_zh_valuation_baidu(symbol=code, indicator="市盈率(TTM)", period="近一年").iloc[-1]["value"]
    except Exception: pass
    try: pb = ak.stock_zh_valuation_baidu(symbol=code, indicator="市净率", period="近一年").iloc[-1]["value"]
    except Exception: pass
    dy = exdate = None
    if price is not None:
        try: dy, exdate = div_yield(code, price)
        except Exception: pass
    pstr = f"{price}" if price is not None else "价N/A"
    dystr = f"{dy}%(末除息 {exdate})" if dy is not None else "股息率N/A"
    print(f"  {code} {name:<8} 价 {pstr}  股息率 {dystr}  PE_TTM {pe}  PB {pb}")
    time.sleep(0.3)

print("\n"+"="*72)
print("三、红利指数 PE / 股息率（中证官方，月度更新）")
print("-"*72)
for code,name in INDEXES.items():
    try:
        r = retry(lambda: ak.stock_zh_index_value_csindex(symbol=code)).iloc[-1]
        print(f"  {code} {name:<8} {r['日期']}  PE {r['市盈率1']}  股息率 {r['股息率1']}%")
    except Exception as e: print(f"  {code} {name:<8} 失败 {type(e).__name__}: {e}")

print("\n"+"="*72)
print("四、中债国债收益率曲线（固收类利率锚）")
print("-"*72)
try:
    d = retry(lambda: ak.bond_china_yield(start_date=(datetime.today()-timedelta(days=10)).strftime("%Y%m%d"), end_date=datetime.today().strftime("%Y%m%d")))
    r = d.iloc[-1]
    print(f"  {r.iloc[1]}  1年 {r.iloc[4]}%  3年 {r.iloc[5]}%  5年 {r.iloc[6]}%  10年 {r.iloc[8]}%  30年 {r.iloc[9]}%")
except Exception as e: print(f"  失败 {type(e).__name__}: {e}")
