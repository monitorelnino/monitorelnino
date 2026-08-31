#!/usr/bin/env python3
"""
monitorar_politica_por_inteiro.py
=================================
Vigia de DESCOBERTA sobre o painel "El Niño 2026/2027" da Política Por Inteiro
(Instituto Talanoa): https://politicaporinteiro.org/el-nino/ — levantamento de
decretos, comitês e programas federais, estaduais e municipais.

Estatuto da fonte (METODOLOGIA §4 e §17; decisão de Patricia, 31/08/2026):
  AGREGADOR TERCEIRO = fonte de PISTAS, nunca de registro. Cada ato citado no
  painel exige confirmação no documento oficial antes de entrar no banco — o
  próprio painel avisa que "não substitui o texto oficial dos decretos".
  Este script NUNCA escreve em estados.json, municipios.json ou indice.json:
  só enfileira em data/pistas_imprensa.json (estadual/municipal) e
  data/pistas_sinais.json (federal), com a trava absoluta das filas.

Como funciona (rede tolerante a falha, como os demais vigias):
  1. Baixa a página do painel. Os dados são carregados por JavaScript, então a
     página em si não traz os atos — o script procura na marcação a fonte de
     dados referenciada (JSON, CSV, planilha Google, endpoint wp-json) e a lê.
  2. Normaliza cada registro (esfera, UF, município, tipo, data, título, link)
     por nomes de campo heurísticos, já que o esquema do painel não é nosso.
  3. Classifica o alvo no vocabulário do orquestrador (C-estado-amplo/UF,
     D-municipio-prioritario/Nome/UF, resposta/UF) e descarta o que já está
     no banco (município por nome+UF).
  4. Registra as pistas inéditas. Se não achar fonte de dados legível, registra
     UMA pista de manutenção (deduplicada) pedindo triagem manual do painel.
Uso:
  python3 monitorar_politica_por_inteiro.py             # roda (na Action, com rede)
  python3 monitorar_politica_por_inteiro.py --dry-run   # mostra o que faria, não grava
  python3 monitorar_politica_por_inteiro.py --self-test # lógica com fixture, sem rede
"""
import argparse
import csv
import hashlib
import io
import json
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).parent
DATA = RAIZ / "data"
PAGINA = "https://politicaporinteiro.org/el-nino/"
FONTE = "Política Por Inteiro (Instituto Talanoa) — agregador terceiro; exige confirmação no documento oficial"
UFS = {"AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE",
       "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"}
NOME_UF = {"acre": "AC", "alagoas": "AL", "amazonas": "AM", "amapa": "AP", "bahia": "BA", "ceara": "CE",
           "distrito federal": "DF", "espirito santo": "ES", "goias": "GO", "maranhao": "MA", "minas gerais": "MG",
           "mato grosso do sul": "MS", "mato grosso": "MT", "para": "PA", "paraiba": "PB", "pernambuco": "PE",
           "piaui": "PI", "parana": "PR", "rio de janeiro": "RJ", "rio grande do norte": "RN", "rondonia": "RO",
           "roraima": "RR", "rio grande do sul": "RS", "santa catarina": "SC", "sergipe": "SE", "sao paulo": "SP",
           "tocantins": "TO"}
PADROES_FONTE_DADOS = [
    r"https?://[^\"'\s<>]+\.json(?:\?[^\"'\s<>]*)?",
    r"https?://[^\"'\s<>]+\.csv(?:\?[^\"'\s<>]*)?",
    r"https?://docs\.google\.com/spreadsheets/[^\"'\s<>]+",
    r"https?://sheets\.googleapis\.com/[^\"'\s<>]+",
    r"https?://opensheet\.elk\.sh/[^\"'\s<>]+",
    r"https?://[^\"'\s<>]*politicaporinteiro\.org/wp-json/[^\"'\s<>]+",
    r"https?://api\.airtable\.com/[^\"'\s<>]+",
]
TERMOS_RESPOSTA = ("situação de emergência", "situacao de emergencia", "calamidade")


def nrm(s):
    """Normaliza texto para comparação: sem acento, minúsculo, espaços colapsados."""
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().lower()


def _get(url, timeout=30):
    """GET simples com User-Agent identificado; devolve texto ou levanta a exceção de rede."""
    req = urllib.request.Request(url, headers={"User-Agent": "MonitorElNinoBrasil/1.0 (+https://monitorelnino.com.br)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def descobrir_fontes_dados(html):
    """Lista, sem repetição e na ordem de aparição, as URLs de dados referenciadas na marcação."""
    achadas = []
    for pat in PADROES_FONTE_DADOS:
        for m in re.finditer(pat, html):
            u = m.group(0).rstrip(".,;)")
            if u not in achadas:
                achadas.append(u)
    return achadas


def carregar_registros(texto):
    """Interpreta o corpo de uma fonte de dados como JSON (lista, ou dicionário com a lista) ou CSV."""
    texto = texto.strip()
    try:
        obj = json.loads(texto)
        if isinstance(obj, list):
            return [x for x in obj if isinstance(x, dict)]
        if isinstance(obj, dict):
            for v in obj.values():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    return v
        return []
    except json.JSONDecodeError:
        pass
    try:
        linhas = list(csv.DictReader(io.StringIO(texto)))
        return linhas if linhas and len(linhas[0]) >= 3 else []
    except csv.Error:
        return []


def _campo(reg, *candidatos):
    """Devolve o valor do primeiro campo cujo nome normalizado contenha um dos candidatos."""
    chaves = {nrm(k): k for k in reg.keys()}
    for cand in candidatos:
        for kn, k in chaves.items():
            if cand in kn:
                v = reg.get(k)
                if v not in (None, ""):
                    return str(v).strip()
    return ""


def normalizar(reg):
    """Mapeia um registro de esquema desconhecido para o vocabulário do projeto (heurística declarada)."""
    esfera = nrm(_campo(reg, "esfera", "nivel", "nível", "ambito", "âmbito"))
    uf_bruto = _campo(reg, "uf", "estado", "sigla")
    uf = uf_bruto.upper() if uf_bruto.upper() in UFS else NOME_UF.get(nrm(uf_bruto), "")
    municipio = _campo(reg, "municipio", "município", "cidade")
    tipo = _campo(reg, "tipo", "categoria", "instrumento")
    titulo = _campo(reg, "titulo", "título", "ato", "nome", "descricao", "descrição", "medida")
    url = _campo(reg, "link", "url", "fonte", "documento")
    data = _campo(reg, "data", "publicacao", "publicação")
    if not esfera:
        esfera = "municipal" if municipio else ("estadual" if uf else "federal")
    if "fed" in esfera:
        esfera = "federal"
    elif "est" in esfera:
        esfera = "estadual"
    elif "mun" in esfera:
        esfera = "municipal"
    return {"esfera": esfera, "uf": uf, "municipio": municipio, "tipo": tipo, "titulo": titulo, "url": url, "data": data}


def classificar_alvo(n):
    """Rótulo de alvo no vocabulário do orquestrador; None quando o registro não é acionável (sem UF)."""
    if n["esfera"] == "federal":
        return "federal"
    if not n["uf"]:
        return None
    if n["esfera"] == "municipal" and n["municipio"]:
        texto = nrm(n["tipo"] + " " + n["titulo"])
        if any(t in texto for t in TERMOS_RESPOSTA):
            return f"resposta/{n['uf']}"
        return f"D-municipio-prioritario/{n['municipio']}/{n['uf']}"
    return f"C-estado-amplo/{n['uf']}"


def ja_no_banco(n, municipios):
    """Município já registrado (nome + UF) — a pista seria redundante; estados são sempre enfileirados
    (a comparação de instrumento estadual é juízo humano, e a deduplicação por hash impede repetição)."""
    if n["esfera"] == "municipal" and n["municipio"]:
        return (nrm(n["municipio"]), n["uf"]) in {(nrm(m["nome"]), m["uf"]) for m in municipios}
    return False


def montar_pistas(registros, municipios):
    """Transforma registros normalizados em pistas para as duas filas: (imprensa, sinais_federais)."""
    imprensa, federais = [], []
    for reg in registros:
        n = normalizar(reg)
        if not n["titulo"]:
            continue
        alvo = classificar_alvo(n)
        if alvo is None or ja_no_banco(n, municipios):
            continue
        titulo = n["titulo"] + (f" ({n['tipo']})" if n["tipo"] else "") + (f" · {n['data']}" if n["data"] else "")
        if alvo == "federal":
            federais.append({"fonte": FONTE, "termo": "El Niño", "titulo": titulo, "data": n["data"], "url": n["url"] or PAGINA,
                             "observacao": "Sinal federal citado por agregador terceiro — localizar o ato no DOU antes de qualquer promoção."})
        else:
            imprensa.append({"alvo": alvo, "titulo": titulo, "url": n["url"] or PAGINA, "fonte": FONTE,
                             "observacao": "Citado pelo painel da Política Por Inteiro; confirmar no documento oficial (o link pode ser o do próprio ato ou só o painel)."})
    return imprensa, federais


def pista_manutencao(motivo):
    """Pista única (deduplicada por hash) avisando que o painel não pôde ser lido por máquina."""
    return {"alvo": "manutencao/PPI", "fonte": FONTE, "url": PAGINA,
            "titulo": "Painel da Política Por Inteiro não legível por máquina nesta execução — abrir o painel e triar manualmente",
            "observacao": f"Motivo: {motivo}. O vigia procura na página uma fonte de dados (JSON/CSV/planilha/wp-json); se o painel mudar de estrutura, ajustar PADROES_FONTE_DADOS."}


def _hash_banco():
    """Impressão digital dos arquivos que este script NUNCA pode alterar (garantia verificável)."""
    h = hashlib.sha256()
    for nome in ("estados.json", "municipios.json", "indice.json"):
        p = DATA / nome
        if p.exists():
            h.update(p.read_bytes())
    return h.hexdigest()


def executar(dry_run=False, buscar=_get):
    """Ciclo completo: página → fonte de dados → registros → pistas → filas. Devolve o resumo."""
    sys.path.insert(0, str(RAIZ))
    import monitorar_imprensa_regional as imp
    import monitorar_sinais_federais as msf
    antes = _hash_banco()
    municipios = json.load(open(DATA / "municipios.json", encoding="utf-8"))
    fila_imp, fila_fed = imp.carregar_fila(), msf.carregar_fila()
    resumo = {"fontes_encontradas": [], "registros": 0, "pistas_imprensa": 0, "pistas_federais": 0, "manutencao": None}
    registros = []
    try:
        html = buscar(PAGINA)
        fontes = descobrir_fontes_dados(html)
        resumo["fontes_encontradas"] = fontes
        for u in fontes:
            try:
                registros = carregar_registros(buscar(u))
            except Exception as e:  # rede tolerante a falha: tenta a próxima fonte
                print(f"  fonte {u}: {e}")
                registros = []
            if registros:
                break
    except Exception as e:
        resumo["manutencao"] = f"falha ao baixar a página: {e}"
    if not registros and not resumo["manutencao"]:
        resumo["manutencao"] = ("nenhuma fonte de dados legível encontrada na marcação"
                                if not resumo["fontes_encontradas"] else "fontes encontradas, nenhuma com registros interpretáveis")
    resumo["registros"] = len(registros)
    novas_imp, novas_fed = montar_pistas(registros, municipios)
    if resumo["manutencao"]:
        novas_imp.append(pista_manutencao(resumo["manutencao"]))
    if dry_run:
        resumo["pistas_imprensa"], resumo["pistas_federais"] = len(novas_imp), len(novas_fed)
        return resumo
    resumo["pistas_imprensa"] = len(imp.registrar(fila_imp, novas_imp))
    resumo["pistas_federais"] = len(msf.registrar(fila_fed, novas_fed))
    json.dump(fila_imp, open(DATA / "pistas_imprensa.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(fila_fed, open(DATA / "pistas_sinais.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    assert _hash_banco() == antes, "TRAVA VIOLADA: o banco mudou durante o vigia da Política Por Inteiro"
    return resumo


FIXTURE = [
    {"Esfera": "Estadual", "Estado": "Sergipe", "Tipo": "Decreto", "Título": "Decreto nº 1.234/2026 institui comitê El Niño",
     "Data": "10/08/2026", "Link": "https://www.se.gov.br/decreto-1234"},
    {"Esfera": "Municipal", "UF": "SC", "Município": "Biguaçu", "Tipo": "Decreto de situação de emergência",
     "Título": "Decreto 285-A/2026", "Data": "30/08/2026", "Link": "https://biguacu.sc.gov.br/decreto-285a"},
    {"Esfera": "Municipal", "UF": "SP", "Município": "Sorocaba", "Tipo": "Plano", "Título": "Plano de Contingência El Niño 2026/2027",
     "Data": "15/08/2026", "Link": ""},
    {"Esfera": "Federal", "Tipo": "Portaria", "Título": "Portaria MDS nº 1.207/2026 — Gabinete Extraordinário", "Data": "18/08/2026",
     "Link": "https://www.in.gov.br/web/dou/-/portaria-mds-1207"},
    {"Esfera": "Municipal", "UF": "ES", "Município": "Colatina", "Tipo": "Plano", "Título": "PLANCON 2026", "Data": "", "Link": ""},
    {"Esfera": "Estadual", "Estado": "Marte", "Título": "Ato sem UF reconhecível"},
]


def self_test():
    """Testa normalização, classificação, dedup contra o banco e a garantia de não escrever no banco (sem rede)."""
    municipios = [{"nome": "Colatina", "uf": "ES"}]
    ns = [normalizar(r) for r in FIXTURE]
    assert ns[0]["uf"] == "SE" and ns[0]["esfera"] == "estadual", ns[0]
    assert classificar_alvo(ns[0]) == "C-estado-amplo/SE"
    assert classificar_alvo(ns[1]) == "resposta/SC", "decreto de emergência municipal vai para a fila de resposta"
    assert classificar_alvo(ns[2]) == "D-municipio-prioritario/Sorocaba/SP"
    assert classificar_alvo(ns[3]) == "federal"
    assert ja_no_banco(ns[4], municipios), "Colatina/ES já está no banco — não vira pista"
    assert classificar_alvo(ns[5]) is None, "sem UF reconhecível não é acionável"
    imp, fed = montar_pistas(FIXTURE, municipios)
    assert len(imp) == 3 and len(fed) == 1, (len(imp), len(fed))
    assert imp[2]["url"] == PAGINA, "sem link do ato, a pista aponta para o painel"
    print("✓ self-test OK — normalização heurística, alvos (estadual/municipal/resposta/federal), dedup contra o banco")
    html = '<script>fetch("https://exemplo.org/dados/el-nino.json?v=3")</script><a href="https://docs.google.com/spreadsheets/d/abc/edit">planilha</a>'
    fontes = descobrir_fontes_dados(html)
    assert fontes == ["https://exemplo.org/dados/el-nino.json?v=3", "https://docs.google.com/spreadsheets/d/abc/edit"], fontes
    assert carregar_registros(json.dumps({"itens": FIXTURE}))[0]["Esfera"] == "Estadual"
    assert carregar_registros("Esfera,UF,Título\nEstadual,SC,Decreto X\n")[0]["UF"] == "SC"
    print("✓ self-test OK — descoberta de fonte de dados na marcação; leitura de JSON (lista/dicionário) e CSV")
    antes = _hash_banco()
    r = executar(dry_run=True, buscar=lambda u: "<html>sem dados</html>")
    assert r["manutencao"] and r["pistas_imprensa"] == 1 and r["pistas_federais"] == 0, r
    r2 = executar(dry_run=True, buscar=lambda u: ("<script>src=\"https://x.org/a.json\"</script>" if u == PAGINA else json.dumps(FIXTURE)))
    assert r2["registros"] == 6 and r2["pistas_federais"] == 1 and r2["manutencao"] is None, r2
    assert _hash_banco() == antes
    print("✓ self-test OK — painel ilegível vira 1 pista de manutenção; painel legível vira pistas; banco intocado")
    return 0


def main():
    """Interface de linha de comando."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    r = executar(dry_run=a.dry_run)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
