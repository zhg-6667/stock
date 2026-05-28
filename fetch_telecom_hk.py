# -*- coding: utf-8 -*-
"""三大运营商 港股 近十年股息率(yfinance,需代理)。
移动0941.HK / 电信0728.HK / 联通0762.HK。股息率=自然年每股股息合计 ÷ 年末收盘(港元)。"""
import sys, os
os.environ["HTTP_PROXY"]="http://127.0.0.1:7890"
os.environ["HTTPS_PROXY"]="http://127.0.0.1:7890"
os.environ.pop("NO_PROXY", None); os.environ.pop("no_proxy", None)
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
import yfinance as yf
import pandas as pd

def strip_tz(idx):
    return idx.tz_convert(None) if getattr(idx,"tz",None) is not None else idx

TICK=[("0941.HK","中国移动"),("0728.HK","中国电信"),("0762.HK","中国联通")]
results={}
for code,name in TICK:
    t=yf.Ticker(code)
    div=t.dividends
    hist=t.history(period="12y", auto_adjust=False)
    if div is None or len(div)==0 or hist is None or len(hist)==0:
        print(f"{name} {code}: 无数据(代理/连接问题?)"); continue
    div=div.copy(); div.index=strip_tz(div.index)
    close=hist["Close"].copy(); close.index=strip_tz(close.index)
    annual=div.groupby(div.index.year).sum()
    yearend=close.groupby(close.index.year).last()
    cur=float(close.iloc[-1]); curd=close.index[-1].date()
    results[name]={"annual":annual,"yearend":yearend,"cur":cur,"curd":curd}

print("="*70)
print("港股·近十年每股股息(HKD)")
print("-"*70)
hdr="年份   " + "".join(f"{n[2:]:>10}" for _,n in TICK)
print(hdr)
for y in range(2016,2027):
    line=f"{y}  "
    for _,name in TICK:
        r=results.get(name)
        v=r["annual"].get(y) if r else None
        line+=f"{(f'{v:.4f}' if v is not None else '-'):>10}"
    print(line)

print("\n"+"="*70)
print("港股·近十年股息率(自然年股息 ÷ 年末收盘)")
print("-"*70)
print(hdr)
for y in range(2016,2027):
    line=f"{y}  "
    for _,name in TICK:
        r=results.get(name)
        if r:
            d=r["annual"].get(y); p=r["yearend"].get(y)
            dy=(d/p*100) if (d is not None and p) else None
            line+=f"{(f'{dy:.2f}%' if dy is not None else '-'):>10}"
        else: line+=f"{'-':>10}"
    print(line)

print("\n"+"-"*70)
for _,name in TICK:
    r=results.get(name)
    if not r: continue
    last2=r["annual"].tail(2).sum()  # 近两期≈近一年(港股一年两派)
    print(f"{name}: 现价 {r['cur']:.2f} HKD（{r['curd']}）  近一年股息率 ≈ {last2/r['cur']*100:.2f}%")
