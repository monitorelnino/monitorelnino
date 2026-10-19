import io, re
from coletores_base import buscar
base = "https://ftp.ibge.gov.br/Perfil_Municipios/2020/"
for d in (base, base + "Base_de_Dados/", base + "Documentacao/", base + "Dicionario/"):
    try:
        h = buscar(d, timeout=60).decode("utf-8", "replace")
        print("LISTA", d, re.findall(r'href="([^"?/][^"]*)"', h)[:40])
    except Exception as e:
        print("LISTA_ERRO", d, type(e).__name__, str(e)[:80])
