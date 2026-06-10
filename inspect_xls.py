import xlrd, sys
sys.stdout.reconfigure(encoding='utf-8')

wb = xlrd.open_workbook(r'D:\sistema de af\sistema_activos\temp_ufv\ufv_2026.xls')
ws = wb.sheet_by_index(0)
for r in range(6, 12):
    row_vals = []
    for c in range(ws.ncols):
        cell = ws.cell(r, c)
        val = cell.value
        row_vals.append(f'T{cell.ctype}V{repr(val)}')
    print(f'R{r}: {row_vals}')
wb.release_resources()
