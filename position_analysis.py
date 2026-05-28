"""每笔交易后实时统计持仓股数和持仓成本（LIFO 口径），找出峰值。"""
import xlrd
import sys
from collections import deque

sys.stdout.reconfigure(encoding='utf-8')

SRC = r"C:\project\股票\标普3倍做多日期20150101-20260527交易复盘.xls"
sh = xlrd.open_workbook(SRC).sheet_by_name('原始交易记录')

stack = deque()  # [日期, 剩余股数, 买入价]
timeline = []    # 每笔交易后快照

for r in range(1, sh.nrows):
    date = sh.cell_value(r, 0)
    side = sh.cell_value(r, 3).strip()
    qty = float(sh.cell_value(r, 4))
    price = float(sh.cell_value(r, 5))

    if side == '买入':
        stack.append([date, qty, price])
    else:
        remaining = qty
        while remaining > 1e-9 and stack:
            top = stack[-1]
            take = min(top[1], remaining)
            top[1] -= take
            remaining -= take
            if top[1] <= 1e-9:
                stack.pop()

    total_qty = sum(t[1] for t in stack)
    total_cost = sum(t[1] * t[2] for t in stack)
    avg_cost = total_cost / total_qty if total_qty else 0
    timeline.append({
        'date': date, 'side': side, 'qty': qty, 'price': price,
        'pos_qty': total_qty, 'pos_cost': total_cost, 'avg_cost': avg_cost,
        'snapshot': [(t[0], t[1], t[2]) for t in stack],
    })

# 输出时间线
print(f"{'日期':>10} {'动作':>5} {'股数':>5} {'成交价':>9} | {'持仓股数':>8} {'持仓成本':>12} {'持仓均价':>9}")
print('-' * 78)
for t in timeline:
    print(f"{t['date']:>10} {t['side']:>5} {t['qty']:>5.0f} {t['price']:>9.2f} | "
          f"{t['pos_qty']:>8.0f} {t['pos_cost']:>12.2f} {t['avg_cost']:>9.2f}"
          + (" ←" if False else ''))

# 峰值
print('\n' + '=' * 78)
max_qty = max(timeline, key=lambda x: x['pos_qty'])
max_cost = max(timeline, key=lambda x: x['pos_cost'])
print(f"\n【峰值持仓股数】 {max_qty['pos_qty']:.0f} 股")
all_max_qty = [t for t in timeline if abs(t['pos_qty'] - max_qty['pos_qty']) < 1e-9]
for t in all_max_qty:
    print(f"  {t['date']} {t['side']} 后 → {t['pos_qty']:.0f} 股 / 成本 {t['pos_cost']:.2f} USD")
print(f"\n【峰值持仓成本】 {max_cost['pos_cost']:.2f} USD ({max_cost['pos_qty']:.0f} 股)")
print(f"  发生于 {max_cost['date']} {max_cost['side']} 后")
print(f"  持仓明细:")
for d, q, p in max_cost['snapshot']:
    print(f"    {d} 买入剩余 {q:.0f} 股 @ {p:.2f}  小计 {q*p:.2f}")
