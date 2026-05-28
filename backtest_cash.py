# -*- coding: utf-8 -*-
"""带现金约束(5.5万)的网格回测：买点需现金足够才成交，否则跳过。"""
import sys
import akshare as ak
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

CASH0 = 55000.0
SELL_GAIN = float(sys.argv[1]) if len(sys.argv) > 1 else 4.0   # 卖出涨幅(%)
SHARES = int(sys.argv[2]) if len(sys.argv) > 2 else 100        # 每笔股数

df = ak.stock_us_daily(symbol="UPRO", adjust="")
df["date"] = pd.to_datetime(df["date"])
df = df[df["date"] >= "2026-01-01"].sort_values("date").reset_index(drop=True)
df["prev_close"] = df["close"].shift(1)
df = df.dropna().reset_index(drop=True)
df["low_pct"] = (df["low"] - df["prev_close"]) / df["prev_close"] * 100
trigger = set(df[df["low_pct"] <= -3.0]["date"])
last_close = float(df.iloc[-1]["close"])
last_date = df.iloc[-1]["date"]

cash = CASH0
holdings = []      # {buy_date, buy_price, target, cost}
done = []          # 已平仓成交
skipped = []       # 资金不足跳过
peak_used = 0.0
peak_date = None
peak_n = 0

for _, day in df.iterrows():
    d = day["date"]
    # 1. 先结算今天能卖出的持仓（昨天及以前买入、今日最高价触及目标）
    keep = []
    for h in holdings:
        if d > h["buy_date"] and day["high"] >= h["target"]:
            cash += h["target"] * SHARES
            done.append({**h, "sell_date": d, "sell_price": h["target"],
                         "hold": (d - h["buy_date"]).days,
                         "profit": (h["target"] - h["buy_price"]) * SHARES})
        else:
            keep.append(h)
    holdings = keep
    # 2. 今天是买点？现金够就买，否则跳过
    if d in trigger:
        bp = round(day["prev_close"] * 0.97, 4)
        cost = bp * SHARES
        if cash >= cost:
            cash -= cost
            holdings.append({"buy_date": d, "buy_price": bp, "target": round(bp * (1 + SELL_GAIN / 100), 4), "cost": cost})
        else:
            skipped.append({"date": d, "buy_price": bp, "cost": cost, "cash_then": cash})
    # 3. 记录峰值占用
    used = sum(h["cost"] for h in holdings)
    if used > peak_used:
        peak_used, peak_date, peak_n = used, d, len(holdings)

# 期末仍持仓的（浮动）
open_pos = holdings

print("===== 成交并卖出的交易 =====")
print(f"{'买入日':>11} {'买入价':>8} {'买入成本':>9} {'卖出日':>11} {'卖出价':>8} {'持仓天':>5} {'收益':>8}")
done.sort(key=lambda x: x["buy_date"])
for t in done:
    print(f"{t['buy_date'].strftime('%Y-%m-%d'):>11} {t['buy_price']:>8.2f} {t['cost']:>9.2f} "
          f"{t['sell_date'].strftime('%Y-%m-%d'):>11} {t['sell_price']:>8.2f} {t['hold']:>5} {t['profit']:>+8.2f}")

if open_pos:
    print("\n===== 期末仍持仓（未触及卖出目标）=====")
    for h in open_pos:
        fl = (last_close - h["buy_price"]) * SHARES
        print(f"  {h['buy_date'].strftime('%Y-%m-%d')} 买入价{h['buy_price']:.2f} 成本{h['cost']:.2f} 浮动{fl:+.2f}")

print("\n===== 因资金不足跳过的买点 =====")
if skipped:
    for s in skipped:
        print(f"  {s['date'].strftime('%Y-%m-%d')} 想买价{s['buy_price']:.2f} 需成本{s['cost']:.2f}，当时仅剩现金{s['cash_then']:.2f}")
else:
    print("  （无）")

realized = sum(t["profit"] for t in done)
unreal = sum((last_close - h["buy_price"]) * SHARES for h in open_pos)
fee = (len(done) * 4.8) + (len(open_pos) * 2.3)
print("\n===== 汇总（本金{:.0f}，卖出+{}%，每笔{}股）=====".format(CASH0, SELL_GAIN, SHARES))
print(f"触发买点 {len(trigger)} 个：成交 {len(done)+len(open_pos)} 笔（已平仓 {len(done)}，持仓中 {len(open_pos)}），跳过 {len(skipped)} 笔")
print(f"同一时间最高持仓成本(资金占用峰值): {peak_used:.2f} USD（{peak_date.strftime('%Y-%m-%d')}，{peak_n} 笔/{peak_n*SHARES} 股）")
print(f"已实现收益: {realized:+.2f} USD")
if open_pos:
    print(f"未平仓浮动盈亏(按最新{last_close:.2f}): {unreal:+.2f} USD")
print(f"按本金 {CASH0:.0f} 收益率: {realized/CASH0*100:+.2f}%（已实现）")
print(f"期末现金: {cash:.2f} USD")
print(f"估算手续费: -{fee:.2f} -> 扣费后已实现≈{realized-fee:+.2f}")
