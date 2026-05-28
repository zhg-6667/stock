# -*- coding: utf-8 -*-
"""回测：当日最低跌破前收-3%时在-3%价位买100股，涨回买入价+3%时卖出。"""
import sys
import akshare as ak
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

df = ak.stock_us_daily(symbol="UPRO", adjust="")
df["date"] = pd.to_datetime(df["date"])
df = df[df["date"] >= "2026-01-01"].sort_values("date").reset_index(drop=True)
df["prev_close"] = df["close"].shift(1)
df = df.dropna().reset_index(drop=True)
df["low_pct"] = (df["low"] - df["prev_close"]) / df["prev_close"] * 100
buys = df[df["low_pct"] <= -3.0].reset_index(drop=True)

last_close = float(df.iloc[-1]["close"])
last_date = df.iloc[-1]["date"]

rows = []
for _, b in buys.iterrows():
    bp = round(b["prev_close"] * 0.97, 4)      # 买入价 = 前收×0.97
    tgt = round(bp * 1.03, 4)                   # 卖出目标 = 买入×1.03
    bd = b["date"]
    fut = df[df["date"] > bd]
    hit = fut[fut["high"] >= tgt]
    if len(hit):
        s = hit.iloc[0]
        sd = s["date"]
        hold = (sd - bd).days
        profit = (tgt - bp) * 100
        rows.append([bd, bp, bp * 100, sd, tgt, hold, profit, "已平仓"])
    else:
        hold = (last_date - bd).days
        profit = (last_close - bp) * 100
        rows.append([bd, bp, bp * 100, None, None, hold, profit, "持仓中"])

print(f"{'买入日':>11} {'买入价':>8} {'买入成本':>9} {'卖出日':>11} {'卖出价':>8} {'持仓天':>5} {'收益':>8} 状态")
for r in rows:
    bd, bp, cost, sd, sp, hold, profit, st = r
    sd_s = sd.strftime("%Y-%m-%d") if sd is not None else "—"
    sp_s = f"{sp:.2f}" if sp is not None else "—"
    print(f"{bd.strftime('%Y-%m-%d'):>11} {bp:>8.2f} {cost:>9.2f} {sd_s:>11} {sp_s:>8} {hold:>5} {profit:>+8.2f} {st}")

closed = [r for r in rows if r[7] == "已平仓"]
holding = [r for r in rows if r[7] == "持仓中"]
tot_cost = sum(r[2] for r in rows)
realized = sum(r[6] for r in closed)
unreal = sum(r[6] for r in holding)
avg_hold = sum(r[5] for r in closed) / len(closed) if closed else 0

print("\n===== 汇总 =====")
print(f"总笔数 {len(rows)}：已平仓 {len(closed)}，持仓中 {len(holding)}")
print(f"总买入成本（累计）: {tot_cost:.2f} USD")
print(f"已实现收益: {realized:+.2f} USD")
print(f"未平仓浮动盈亏(按最新收盘{last_close:.2f}): {unreal:+.2f} USD")
print(f"合计盈亏: {realized + unreal:+.2f} USD（占累计成本 {(realized+unreal)/tot_cost*100:+.2f}%）")
print(f"已平仓平均持仓天数: {avg_hold:.1f} 天")

# 同一时间最高持仓成本：扫描每个交易日，统计当时仍持仓各笔成本之和的峰值
spans = []
for r in rows:
    end = r[3] if r[3] is not None else last_date   # 卖出日；未平仓用最新日
    spans.append((r[0], end, r[2]))
peak = 0.0
peak_date = None
peak_n = 0
for d in df["date"]:
    held = [c for (bd, ed, c) in spans if bd <= d <= ed]
    if sum(held) > peak:
        peak = sum(held)
        peak_date = d
        peak_n = len(held)
print(f"同一时间最高持仓成本: {peak:.2f} USD（发生于 {peak_date.strftime('%Y-%m-%d')}，同时持有 {peak_n} 笔 / {peak_n*100} 股）")

# 手续费估算：每笔买卖约 2.3+2.5=4.8 USD
fee = len(closed) * 4.8 + len(holding) * 2.3
print(f"估算手续费(买卖各约2.3/2.5): -{fee:.2f} USD -> 扣费后已实现≈{realized-fee:+.2f}")
