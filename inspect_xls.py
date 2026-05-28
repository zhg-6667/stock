import xlrd
import sys

sys.stdout.reconfigure(encoding='utf-8')

f = r"C:\project\股票\标普3倍做多日期20150101-20260527交易复盘.xls"
wb = xlrd.open_workbook(f)
print("Sheets:", wb.sheet_names())
for name in wb.sheet_names():
    sh = wb.sheet_by_name(name)
    print(f"\n=== Sheet: {name}  rows={sh.nrows} cols={sh.ncols} ===")
    for r in range(min(sh.nrows, 50)):
        row = [sh.cell_value(r, c) for c in range(sh.ncols)]
        print(r, row)
