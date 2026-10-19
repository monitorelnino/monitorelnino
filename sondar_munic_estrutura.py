import io
from coletores_base import buscar
import openpyxl
b = buscar("https://ftp.ibge.gov.br/Perfil_Municipios/2020/Base_de_Dados/Base_MUNIC_2020.xlsx", timeout=180)
wb = openpyxl.load_workbook(io.BytesIO(b), read_only=False, data_only=True)
ws = wb["Dicionário"]
n = 0
for i, r in enumerate(ws.iter_rows(values_only=True)):
    t = [str(c).replace("\n", " ")[:110] if c is not None else "_" for c in r]
    if 11 <= i <= 22: print("DICROW", i, t)
    if any("mgrd" in x.lower() for x in t):
        n += 1
        if n <= 14 or n in (60, 100, 150, 160, 170): print("MGRD", i, t)
print("MGRD_TOTAL", n)
