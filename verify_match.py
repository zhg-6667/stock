import openpyxl, sys
sys.stdout.reconfigure(encoding='utf-8')
wb = openpyxl.load_workbook(r"C:\project\股票\标普3倍做多日期20150101-20260527交易复盘_已匹配.xlsx")
ws = wb.active
for row in ws.iter_rows(min_row=1, max_row=31, values_only=True):
    print(row)
