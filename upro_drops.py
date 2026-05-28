# -*- coding: utf-8 -*-
"""分别用 akshare 与 yfinance 获取 UPRO 近两个月日线，筛出日跌幅 > 3% 的交易日。"""
import sys
import datetime as dt
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

TICKER = "UPRO"
TODAY = dt.date(2026, 5, 28)
START = TODAY - dt.timedelta(days=62)          # 近两个月
FETCH_START = START - dt.timedelta(days=10)    # 多取几天用于算首日前收
THRESH = -3.0  # 跌幅阈值（%）


def show(df, src):
    """df 需含列: date(datetime), close(float)"""
    df = df.sort_values('date').reset_index(drop=True)
    df['pct'] = df['close'].pct_change() * 100
    win = df[(df['date'].dt.date >= START) & (df['date'].dt.date <= TODAY)].copy()
    drops = win[win['pct'] < THRESH]
    print(f"\n{'='*60}\n[{src}]  {TICKER}  {START} ~ {TODAY}")
    print(f"窗口内交易日 {len(win)} 天，日跌幅 > 3% 的有 {len(drops)} 天：")
    if drops.empty:
        print("  （无）")
    else:
        print(f"  {'日期':>12} {'前收':>9} {'收盘':>9} {'跌幅':>8}")
        for _, r in drops.iterrows():
            prev = r['close'] / (1 + r['pct']/100)
            print(f"  {r['date'].date()!s:>12} {prev:>9.2f} {r['close']:>9.2f} {r['pct']:>7.2f}%")
    return drops


# ---------- akshare ----------
ak_drops = None
try:
    import akshare as ak
    a = ak.stock_us_daily(symbol=TICKER, adjust="")
    a = a.rename(columns={'date': 'date'})
    a['date'] = pd.to_datetime(a['date'])
    a = a[['date', 'close']].astype({'close': float})
    a = a[a['date'].dt.date >= FETCH_START]
    ak_drops = show(a, "akshare / 东方财富")
except Exception as e:
    print(f"\n[akshare] 失败: {type(e).__name__}: {e}")

# ---------- yfinance ----------
yf_drops = None
try:
    import yfinance as yf
    y = yf.download(TICKER, start=str(FETCH_START), end=str(TODAY + dt.timedelta(days=1)),
                    progress=False, auto_adjust=False)
    if y is None or y.empty:
        raise RuntimeError("返回空数据（很可能国内无法直连 Yahoo，需要代理）")
    if isinstance(y.columns, pd.MultiIndex):
        y.columns = y.columns.get_level_values(0)
    y = y.reset_index()
    y = y.rename(columns={y.columns[0]: 'date', 'Close': 'close'})
    y = y[['date', 'close']]
    y['date'] = pd.to_datetime(y['date'])
    y['close'] = y['close'].astype(float)
    yf_drops = show(y, "yfinance / Yahoo")
except Exception as e:
    print(f"\n[yfinance] 失败: {type(e).__name__}: {e}")
