#!/usr/bin/env python3
"""
gerar_dados_abertos.py — exportação citável dos dados do Monitor El Niño Brasil.

Sugestão aceita por Patricia em 31/08/2026: os JSON de `data/` já são públicos,
mas pesquisador cita dataset, não site. Este script gera, em `dados-abertos/`:
  - CSVs planos (indice, estados, municipios, atos_resposta, historico_mudancas)
  - datapackage.json (Frictionless Data Package: esquema, licença, versão)
e, na raiz, CITATION.cff (GitHub "Cite this repository"). O DOI é emitido pelo
Zenodo a partir de um release do GitHub — passo humano, roteiro em
docs/DADOS_ABERTOS.md; o campo fica em branco até lá (nunca inventar DOI).

Determinístico: mesma entrada → mesmos arquivos. A verificação de consistência
confere que as linhas dos CSVs batem com os JSON de origem.
Uso: python3 gerar_dados_abertos.py [--self-test]
"""
import csv
import io
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).parent
DATA = RAIZ / "data"
SAIDA = RAIZ / "dados-abertos"
VERSAO = "2.3"
SITE = "https://monitorelnino.com.br"
FAIXAS = [(25, "estágio inicial"), (50, "em construção"), (70, "consolidado"), (101, "avançado")]


def faixa(v):
    """Faixa interpretativa (mesmos cortes do site)."""
    return next(r for c, r in FAIXAS if v < c)


def _csv(linhas, campos):
    """CSV UTF-8 com cabeçalho, quebra de linha \\n, determinístico."""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=campos, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for l in linhas:
        w.writerow({k: ("" if l.get(k) is None else l.get(k)) for k in campos})
    return buf.getvalue()


def tabelas(dados):
    """Devolve {nome: (linhas, campos, descrição)} a partir dos JSON do banco."""
    est = {u["uf"]: u for u in dados["estados"]["ufs"]}
    indice = [{"uf": uf, "estado": est[uf]["nome"], "mare_total": v["total"], "faixa": faixa(v["total"]),
               "componente_estadual": v.get("estado"), "componente_cobertura_populacional": v.get("cobertura_pop"),
               "componente_antecipacao": v.get("antecipacao"), "status_estadual": v.get("status_estadual")}
              for uf, v in sorted(dados["indice"].items())]
    estados = [{"uf": u["uf"], "estado": u["nome"], "status": u.get("status"), "natureza_doc": u.get("natureza_doc"),
                "documento": u.get("doc"), "data": u.get("data"), "orgao": u.get("orgao"), "url": u.get("url", "")}
               for u in sorted(dados["estados"]["ufs"], key=lambda x: x["uf"])]
    municipios = [{"uf": m["uf"], "municipio": m["nome"], "categoria": m.get("categoria"), "documento": m.get("documento"),
                   "data": m.get("data"), "fonte": m.get("fonte"), "url": m.get("url", "")}
                  for m in sorted(dados["municipios"], key=lambda x: (x["uf"], x["nome"]))]
    atos = [{"uf": e["uf"], "municipio": e["nome"], "data": e.get("data"), "causa": e.get("causa"), "decreto": e.get("decreto"),
             "fonte": e.get("fonte"), "url": e.get("url", "")}
            for e in sorted(dados["atos_resposta"].get("eventos", []), key=lambda x: (x["uf"], x["nome"], x.get("data", "")))]
    hist = [{"data": h["data"], "uf": h["uf"], "tipo": h["tipo"], "titulo": h["titulo"], "resumo": h["resumo"]}
            for h in dados.get("historico", {}).get("eventos", [])]
    verif = [{"ibge": v["ibge"], "uf": v["uf"], "municipio": v["nome"], "nivel_verificacao": v["nivel_verificacao"],
              "ultima_verificacao": v.get("ultima_verificacao") or "", "plano_localizado": v.get("plano_localizado") or "",
              "decreto_reconhecido": "" if v.get("decreto_reconhecido") is None else v["decreto_reconhecido"],
              "decreto_homologado": "" if v.get("decreto_homologado") is None else v["decreto_homologado"]}
             for v in sorted(dados.get("verificacao_municipal", []), key=lambda x: (x["uf"], x["nome"]))]
    saude = [{"uf": uf, "status": u.get("status"), "orgao": u.get("orgao") or "", "documento": u.get("doc") or "",
              "numero": u.get("numero") or "", "data": u.get("data") or "", "natureza_doc": u.get("natureza_doc"),
              "consist": u.get("consist"), "riscos_sanitarios_projetados": "; ".join(u.get("risco_sanitario_projetado", [])),
              "data_verificacao": u.get("data_verificacao") or "", "url": u.get("url") or ""}
             for uf, u in sorted(dados.get("saude_uf", {}).get("uf", {}).items())]
    return {
        "indice": (indice, ["uf", "estado", "mare_total", "faixa", "componente_estadual", "componente_cobertura_populacional", "componente_antecipacao", "status_estadual"],
                   "Índice MARÉ por unidade da federação: nota 0–100, faixa interpretativa e componentes."),
        "estados": (estados, ["uf", "estado", "status", "natureza_doc", "documento", "data", "orgao", "url"],
                    "Instrumento estadual localizado por UF (status NOVO/READ/VIG/ELAB/LAC), documento, data e órgão."),
        "municipios": (municipios, ["uf", "municipio", "categoria", "documento", "data", "fonte", "url"],
                       "Registros municipais verificados individualmente (categoria do vocabulário controlado, documento, fonte)."),
        "atos_resposta": (atos, ["uf", "municipio", "data", "causa", "decreto", "fonte", "url"],
                          "Decretos municipais de emergência/calamidade registrados (atos de resposta; nunca pontuam)."),
        "historico_mudancas": (hist, ["data", "uf", "tipo", "titulo", "resumo"],
                               "Mudanças detectadas pelo pipeline entre atualizações (base dos feeds Atom)."),
        # v2.2.4 (§7.7): verificação por níveis e camada de saúde (peso zero)
        "verificacao_municipal": (verif, ["ibge", "uf", "municipio", "nivel_verificacao", "ultima_verificacao", "plano_localizado", "decreto_reconhecido", "decreto_homologado"],
                                  "Nível de verificação alcançado pelo Monitor em cada um dos 5.571 municípios (nao_verificado/nacional/estadual/municipal_completo); 'nada localizado' só com verificação completa."),
        "saude_uf": (saude, ["uf", "status", "orgao", "documento", "numero", "data", "natureza_doc", "consist", "riscos_sanitarios_projetados", "data_verificacao", "url"],
                     "Instrumento estadual de saúde para o ciclo, por UF (NOVO/READ/VIG/ELAB/LAC/NAO_VERIFICADO). Registro de transparência: nunca pontua."),
    }


def datapackage(tabs, corte):
    """Descritor Frictionless com um recurso por CSV e o esquema de campos."""
    return {
        "name": "monitor-el-nino-brasil-mare", "title": "Monitor El Niño Brasil — índice MARÉ e registros verificados",
        "version": VERSAO, "homepage": SITE, "created": _iso(corte),  # AUD-10: ISO 8601
        "corte_dos_dados": corte,
        "description": "Preparação demonstrável publicamente de estados e municípios brasileiros para o El Niño 2026/2027: instrumentos localizados em fontes oficiais, categorizados por vocabulário controlado, e o índice MARÉ (0–100). Metodologia aberta em METODOLOGIA.md.",
        "licenses": [{"name": "CC-BY-4.0", "path": "https://creativecommons.org/licenses/by/4.0/", "title": "Creative Commons Attribution 4.0 International (dados); código sob MIT"}],
        "contributors": [{"title": "Futura Evidence Lab", "role": "author", "path": "https://futuraevidencelab.com.br"}],
        "resources": [{"name": nome, "path": f"{nome}.csv", "format": "csv", "mediatype": "text/csv", "encoding": "utf-8",
                       "description": desc, "schema": {"fields": [{"name": c, "type": "number" if c.startswith(("mare_", "componente_")) else "string"} for c in campos]},
                       "rowCount": len(linhas)} for nome, (linhas, campos, desc) in tabs.items()],
    }


def citation(corte):
    """CITATION.cff (Citation File Format 1.2.0). DOI só depois do depósito."""
    dd, mm, aa = corte.split("/")
    return f"""cff-version: 1.2.0
message: "Se usar estes dados, cite o Monitor El Niño Brasil (índice MARÉ). Após o depósito no Zenodo, substitua o identificador abaixo pelo DOI emitido."
title: "Monitor El Niño Brasil — índice MARÉ (Medida de Antecipação e Resposta ao El Niño), dados verificados"
version: "{VERSAO}"
date-released: "{aa}-{mm}-{dd}"
url: "{SITE}"
# repository-code: "https://github.com/<organizacao>/<repositorio>"   # preencher com a URL real do repositório
license: CC-BY-4.0
type: dataset
authors:
  - name: "Futura Evidence Lab"
    website: "https://futuraevidencelab.com.br"
keywords:
  - El Niño 2026/2027
  - defesa civil
  - planos de contingência
  - preparação demonstrável
  - índice composto
  - Brasil
# identifiers:
#   - type: doi
#     value: "10.5281/zenodo.XXXXXXX"   # preencher após o release + Zenodo (docs/DADOS_ABERTOS.md)
"""


def _iso(d_br: str) -> str:
    """dd/mm/aaaa → aaaa-mm-ddT00:00:00Z (Frictionless exige datetime ISO 8601 em `created`)."""
    try:
        d, m, a = d_br.split("/"); return f"{a}-{m}-{d}T00:00:00Z"
    except ValueError:
        return d_br


def gerar():
    """Escreve dados-abertos/*.csv, datapackage.json e CITATION.cff."""
    dados = {k: json.load(open(DATA / f"{k}.json", encoding="utf-8")) for k in ("indice", "estados", "municipios", "atos_resposta")}
    if (DATA / "historico_mudancas.json").exists():
        dados["historico"] = json.load(open(DATA / "historico_mudancas.json", encoding="utf-8"))
    for k in ("verificacao_municipal", "saude_uf"):  # v2.2.4
        if (DATA / f"{k}.json").exists():
            dados[k] = json.load(open(DATA / f"{k}.json", encoding="utf-8"))
    corte = json.load(open(DATA / "meta.json", encoding="utf-8")).get("corte", "")
    tabs = tabelas(dados)
    SAIDA.mkdir(exist_ok=True)
    for nome, (linhas, campos, _) in tabs.items():
        (SAIDA / f"{nome}.csv").write_text(_csv(linhas, campos), encoding="utf-8")
    (SAIDA / "datapackage.json").write_text(json.dumps(datapackage(tabs, corte), ensure_ascii=False, indent=1), encoding="utf-8")
    (RAIZ / "CITATION.cff").write_text(citation(corte), encoding="utf-8")
    return {nome: len(linhas) for nome, (linhas, _, _) in tabs.items()}


def self_test():
    """Contagens, faixas, determinismo, CSV parseável, sem DOI inventado."""
    fix = {"indice": {"SC": {"total": 78.6, "estado": 100, "cobertura_pop": 90, "antecipacao": 60, "status_estadual": "NOVO"}},
           "estados": {"ufs": [{"uf": "SC", "nome": "Santa Catarina", "status": "NOVO", "doc": "Plano, \"aspas\"", "data": "01/06/2026"}]},
           "municipios": [{"nome": "Blumenau", "uf": "SC", "categoria": "plano", "documento": "PLANCON", "data": "10/06/2026", "fonte": "Prefeitura"}],
           "atos_resposta": {"eventos": []}}
    t = tabelas(fix)
    assert t["indice"][0][0]["faixa"] == "avançado" and len(t["municipios"][0]) == 1
    c = _csv(*t["estados"][:2]); assert c == _csv(*t["estados"][:2]) and list(csv.DictReader(io.StringIO(c)))[0]["documento"] == 'Plano, "aspas"'
    assert "10.5281/zenodo.XXXXXXX" in citation("31/08/2026") and citation("31/08/2026").count("# identifiers") == 1, "DOI deve ficar comentado até existir"
    dp = datapackage(t, "31/08/2026"); assert dp["resources"][0]["rowCount"] == 1
    print("✓ self-test OK — tabelas, faixa, CSV determinístico e parseável, DOI só como placeholder comentado")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    n = gerar()
    print("✓ dados-abertos/: " + ", ".join(f"{k}={v}" for k, v in n.items()) + " · datapackage.json · CITATION.cff")
