#!/usr/bin/env python3
"""Sonda (14/09/2026) — passo 3 dos handovers "Rota preventiva do fogo" e "Mapa do dinheiro da saúde":
o que a execução mensal do Portal da Transparência (CSV público, sem chave) permite ler sobre
  (a) FNMA → estados/municípios (transferência direta, Lei 15.143/2025, art. 3º-A da Lei 7.797) e o edital FNMA/FDD;
  (b) FNS → municípios: ações de VIGILÂNCIA EM SAÚDE e incentivos de ARBOVIROSES (Portaria GM/MS 2.298/2023 e sucessoras).
Só mede: lista as ações orçamentárias, UGs e favorecidos que casam com os padrões, mês a mês (2025-01 … mês corrente), com
contagens e alguns exemplos — para o coletor nascer com as colunas e os filtros certos, sem adivinhar. Nada é gravado em data/.
Provado em 14/09 (relatório portal_transparencia): o CSV mensal baixa sem chave (~7 MB/mês; latin-1; ';').
"""
import csv, io, re, sys, zipfile, urllib.request, datetime as dt
from collections import Counter, defaultdict

UA = "Monitor El Nino Brasil (monitorelnino.com.br; contato@futuraevidencelab.com.br)"
PADROES = {
  "fogo_fnma": {"ug": re.compile(r"FUNDO NACIONAL DO MEIO AMBIENTE|FNMA", re.I), "acao": re.compile(r"INC[EÊ]NDIO|FOGO|MANEJO INTEGRADO|PREVEN[CÇ][AÃ]O E COMBATE", re.I)},
  "fogo_fdd": {"ug": re.compile(r"DIREITOS DIFUSOS|FDD", re.I), "acao": re.compile(r"INC[EÊ]NDIO|FOGO|BRIGAD", re.I)},
  "saude_vigilancia": {"ug": re.compile(r"FUNDO NACIONAL DE SA[UÚ]DE|FNS", re.I), "acao": re.compile(r"VIGIL[AÂ]NCIA EM SA[UÚ]DE|ARBOVIROS|DENGUE|CHIKUNGUNYA", re.I)},
}
ENTE = re.compile(r"^(MUNICIPIO|PREFEITURA|FUNDO MUNICIPAL|GOVERNO DO ESTADO|ESTADO D[EOA]|FUNDO ESTADUAL|SECRETARIA DE ESTADO)|.+", re.I)   # no conjunto de transferências o favorecido/município já é o ente


def meses():
    hoje = dt.date.today(); m = []
    a, mm = 2025, 1
    while (a, mm) <= (hoje.year, hoje.month):
        m.append(f"{a}{mm:02d}"); mm += 1
        if mm == 13: a, mm = a + 1, 1
    return m


def baixar(mes):
    # 15/09/2026: o CSV de EXECUÇÃO é agregado por classificação (sem favorecido). O de TRANSFERÊNCIAS traz UF, município,
    # órgão subordinado, ação e valor transferido — é o grão do mapa "recebeu".
    url = f"https://portaldatransparencia.gov.br/download-de-dados/transferencias/{mes}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def main():
    print("=== SONDA Portal da Transparência — FNMA (fogo) e FNS (vigilância/arboviroses) — 14/09/2026 ===")
    tot = {k: Counter() for k in PADROES}; ex = {k: [] for k in PADROES}; acoes = {k: Counter() for k in PADROES}; ugs = {k: Counter() for k in PADROES}
    entes = {k: Counter() for k in PADROES}; valores = {k: defaultdict(float) for k in PADROES}
    cab = None
    for mes in meses():
        try:
            bruto = baixar(mes)
        except Exception as e:  # noqa: BLE001
            print(f"-- {mes}: download falhou: {e}"); continue
        try:
            z = zipfile.ZipFile(io.BytesIO(bruto))
        except zipfile.BadZipFile:
            print(f"-- {mes}: não é zip ({len(bruto)} bytes)"); continue
        nome = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if not nome:
            print(f"-- {mes}: sem CSV"); continue
        with z.open(nome[0]) as f:
            rd = csv.reader(io.TextIOWrapper(f, encoding="latin-1", errors="replace", newline=""), delimiter=";")
            cab = next(rd)
            ci = {c: i for i, c in enumerate(cab)}
            if mes == meses()[0]: print("   colunas:", cab)
            iug = next((ci[c] for c in cab if "Nome Órgão Subordinado" in c or "Nome Unidade Gestora" in c), None); iac = next((ci[c] for c in cab if "Nome Ação" in c or ("Ação" in c and "Nome" in c)), None)
            ifav = next((ci[c] for c in cab if "Nome Favorecido" in c or "Nome Município" in c), None); ival = next((ci[c] for c in cab if "Valor Transferido" in c or "Valor Pago" in c), None); iel = next((ci[c] for c in cab if "Tipo Transferência" in c or "Linguagem Cidadã" in c), None)
            if None in (iug, iac, ifav, ival):
                print(f"-- {mes}: colunas não localizadas: ug={iug} acao={iac} fav={ifav} valor={ival} · cabeçalho={cab}"); continue
            n = 0
            for row in rd:
                n += 1
                if len(row) <= max(iug, iac, ifav, ival): continue
                ug, ac, fav = row[iug], row[iac], row[ifav]
                try: val = float(row[ival].replace(".", "").replace(",", "."))
                except ValueError: val = 0.0
                for k, p in PADROES.items():
                    if p["ug"].search(ug) or p["acao"].search(ac):
                        tot[k][mes] += 1; acoes[k][ac] += 1; ugs[k][ug] += 1; valores[k][mes] += val
                        if ENTE.search(fav): entes[k][fav] += 1
                        if len(ex[k]) < 6 and ENTE.search(fav) and val > 0: ex[k].append((mes, ug[:40], ac[:60], fav[:45], val, row[iel][:30] if iel is not None else ""))
            print(f"-- {mes}: {n:,} linhas · " + " · ".join(f"{k}={tot[k][mes]}" for k in PADROES))
    print("\n=== RESUMO POR PADRÃO ===")
    for k in PADROES:
        print(f"\n## {k}: {sum(tot[k].values())} linha(s) em {len(tot[k])} mês(es) · valor pago somado R$ {sum(valores[k].values()):,.0f}")
        print("   UGs:", ugs[k].most_common(6))
        print("   ações:", acoes[k].most_common(10))
        print(f"   favorecidos que parecem entes (municípios/estados): {len(entes[k])} distintos · top: {entes[k].most_common(8)}")
        for e in ex[k]: print("   ex:", e)
    print("\n→ sonda concluída (só leitura).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
