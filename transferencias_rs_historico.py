"""Transferências da União ao RS em 2024 e 2025, do download de dados abertos do Portal da Transparência (relatório do
RS, 23/11/2026; não vai à main). Só agregados: por mês, por rota, e defesa civil (subfunção 182) por tipo de favorecido
e por município. Uso: python3 transferencias_rs_historico.py 202401 202512"""
import csv, io, json, pathlib, sys, zipfile
import coletar_transferencias_municipais as c
from coletores_base import buscar, ler
ini, fim = sys.argv[1], sys.argv[2]
meses = [f"{a}{m:02d}" for a in range(int(ini[:4]), int(fim[:4]) + 1) for m in range(1, 13) if ini <= f"{a}{m:02d}" <= fim]
chave = c.mapa_siafi_para_ibge(ler("municipios_ibge_referencia.json", []))
saida = {"fonte": "https://portaldatransparencia.gov.br/download-de-dados/transferencias/", "meses": {}, "defesa_civil_por_municipio": {}, "falhas": {}}
for mes in meses:
    try:
        corpo = buscar(c.FONTE.format(mes=mes), timeout=300, origem="coletar_transferencias_municipais")
        por_ibge, nao_casados, sem_mun, linhas, soma = c.ler_mes(corpo, chave)
        rs = {}
        for ibge, rotas in por_ibge.items():
            if str(ibge).startswith("43"):
                for r, v in rotas.items():
                    rs[r] = rs.get(r, 0.0) + v
                if rotas.get("defesa_civil"):
                    d = saida["defesa_civil_por_municipio"].setdefault(str(ibge), {})
                    d[mes] = round(rotas["defesa_civil"], 2)
        # defesa civil por tipo de favorecido (estado, município, outros), UF = RS
        tipos, acoes = {}, {}
        z = zipfile.ZipFile(io.BytesIO(corpo))
        with z.open([n for n in z.namelist() if n.lower().endswith(".csv")][0]) as f:
            leitor = csv.reader(io.TextIOWrapper(f, encoding="latin-1", newline=""), delimiter=";")
            cab = next(leitor); col = {k: i for i, k in enumerate(cab)}
            acao = next((k for k in cab if "AÇÃO" in k.upper() and "NOME" in k.upper()), None)
            for l in leitor:
                if len(l) <= col["VALOR TRANSFERIDO"] or l[col["UF"]].strip() != "RS" or l[col["CÓDIGO SUBFUNÇÃO"]].strip() != "182":
                    continue
                v = c.valor_br(l[col["VALOR TRANSFERIDO"]])
                t = l[col["TIPO FAVORECIDO"]].strip(); tipos[t] = tipos.get(t, 0.0) + v
                if acao:
                    a = l[col[acao]].strip(); acoes[a] = acoes.get(a, 0.0) + v
        saida["meses"][mes] = {"municipal_por_rota": {k: round(v, 2) for k, v in rs.items()},
                               "defesa_civil_por_favorecido": {k: round(v, 2) for k, v in tipos.items()},
                               "defesa_civil_por_acao": {k: round(v, 2) for k, v in acoes.items()},
                               "nao_casados_rs": round(sum(v for (uf, _), v in nao_casados.items() if uf == "RS"), 2),
                               "colunas": cab if mes == meses[0] else None}
        print(mes, "ok", round(rs.get("defesa_civil", 0.0), 2), flush=True)
    except Exception as e:  # noqa: BLE001
        saida["falhas"][mes] = f"{type(e).__name__}: {str(e)[:160]}"
        print(mes, "FALHA", saida["falhas"][mes], flush=True)
pathlib.Path("data/relatorio_rs").mkdir(exist_ok=True)
json.dump(saida, open(f"data/relatorio_rs/transferencias_{ini}_{fim}.json", "w"), ensure_ascii=False)
