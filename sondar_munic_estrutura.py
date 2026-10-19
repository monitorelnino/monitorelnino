import io
from coletores_base import buscar
import openpyxl
b = buscar("https://ftp.ibge.gov.br/Perfil_Municipios/2020/Base_de_Dados/Base_MUNIC_2020.xlsx", timeout=180)
wb = openpyxl.load_workbook(io.BytesIO(b), read_only=True, data_only=True)
ws = wb["Dicionário"]
try: ws.reset_dimensions()
except Exception as e: print("RESET_ERRO", e)
rows = list(ws.iter_rows(values_only=True))
print("DIC_LINHAS", len(rows), "DIM", ws.max_row, ws.max_column)
k = 0
for i, r in enumerate(rows):
    t = [str(c).replace("\n", " ")[:120] for c in r if c is not None]
    if i < 4: print("DIC", i, t[:6])
    if any("Mgrd" in x for x in t):
        k += 1
        if k <= 12 or k % 25 == 0: print("MGRD", i, t[:6])
print("MGRD_TOTAL", k)
wb.close()
wb2 = openpyxl.load_workbook(io.BytesIO(b), read_only=False, data_only=True)
w2 = wb2["Dicionário"]
print("DIC_NAO_READONLY", w2.max_row, w2.max_column)
n = 0
for r in w2.iter_rows(values_only=True):
    t = [str(c).replace("\n", " ")[:120] for c in r if c is not None]
    if any("Mgrd" in x for x in t):
        n += 1
        if n <= 10 or n % 25 == 0: print("MGRD2", t[:6])
print("MGRD2_TOTAL", n)
