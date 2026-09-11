#!/usr/bin/env python3
"""
coletar_boletim_pb_arboviroses.py — arboviroses na Paraíba, por REGIÃO DE SAÚDE (10/09/2026)
====================================================================================================
Fonte: SES-PB / Gerência Executiva de Vigilância em Saúde (GEVS), "Boletim Epidemiológico — Arboviroses
Urbanas" (Sinan Net, Sinan Online, e-SUS Sinan e GAL), com dengue, chikungunya, Zika e Oropouche.
Íntegra conferida em 10/09/2026 no boletim nº 03/2026 (dados até a SE 08).

Formato: o melhor desta frente depois de MS. O Quadro 01 vem em TEXTO extraível, uma linha por Região de
Saúde (16 regiões + Total), com população, casos prováveis dos quatro agravos e cinco incidências por 100
mil. O Fluxograma 01 traz notificados / prováveis / confirmados / descartados por agravo. Ao contrário de
PE (infográfico, tabela municipal em imagem), aqui a granularidade sub-estadual é legível.

Numeração: os boletins são NUMERADOS SEQUENCIALMENTE (nº 01, 02, 03…), não por SE, e a cadência é
irregular (nº 02 ≈ SE 05, nº 03 = SE 08). Portanto o coletor NÃO adivinha a SE: tenta números decrescentes
a partir de um teto e fica com o primeiro que responde, lendo a SE de dentro do texto. Corrige o registro
anterior, que supunha o padrão `no_01_2026.pdf`; o real é
`/diretas/saude/arquivos-1/vigilancia-em-saude/boletim-epidemiologico-arboviroses-urbanas-no-0N_2026.pdf`.

Defensivo em três pontos: (1) o Quadro 01 precisa render ao menos 14 das 16 regiões E a linha Total;
(2) a soma das regiões tem de fechar com a linha Total em cada agravo; (3) as identidades do Fluxograma
(notificados = prováveis + descartados; confirmados ≤ prováveis) têm de fechar. Qualquer falha → lacuna,
nada publicado.

Nota de fonte: no nº 03 o texto corrido diz "totalizam 739" casos prováveis de arboviroses enquanto o
Quadro 01 totaliza 738 (671 dengue + 67 chik). O coletor publica o número do QUADRO (738, auditável linha
a linha) e registra a divergência em `divergencia_fonte` — não silencia nem "corrige" a fonte.
  python coletar_boletim_pb_arboviroses.py --autoteste
"""
import io, re, sys
from pathlib import Path
from coletores_base import ler, gravar, buscar, registrar_lacuna, log_busca, rodar_autoteste

RAIZ = Path(__file__).resolve().parent
BASE = "https://paraiba.pb.gov.br"
PADRAO_URL = BASE + "/diretas/saude/arquivos-1/vigilancia-em-saude/boletim-epidemiologico-arboviroses-urbanas-no-{n:02d}_{ano}.pdf"
TETO_NUMERO = 24          # teto de tentativas por ano (cadência irregular; 2026 tinha nº 03 em março)
MIN_REGIOES = 14          # PB tem 16 Regiões de Saúde; abaixo disso a tabela não veio inteira
ANO_ESPERADO = [2026]     # ajustado em tempo de execução por coletar(); lista para o parse_texto enxergar
RESSALVA = ("O Monitor não atribui casos ao El Niño; dados da SES-PB (Sinan Net, Sinan Online, e-SUS Sinan e GAL), "
            "extraídos do Boletim Epidemiológico de Arboviroses Urbanas em PDF — dados sujeitos a alteração.")


def _hoje():
    import datetime as _dt, json as _js
    try:
        a = _js.load(open(RAIZ / "data" / "meta.json", encoding="utf-8")).get("atualizado_em")
        return _dt.datetime.strptime(a, "%d/%m/%Y").date()
    except Exception:  # noqa: BLE001
        return _dt.date.today()


def destino_do_intersticio(corpo: bytes) -> str:
    """Destino declarado numa página intermediária do portal (meta refresh, window.location ou link .pdf direto).
    Função pura; None se a página não declarar destino — o coletor nunca adivinha uma URL de arquivo."""
    try:
        html = corpo.decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return None
    for padrao in (r'<meta[^>]+http-equiv=["\']?refresh["\']?[^>]+content=["\'][^"\']*url=([^"\'>\s]+)',
                   r'(?:window\.location(?:\.href)?|location\.replace\()\s*=?\s*["\']([^"\']+)["\']',
                   r'href="([^"]+\.pdf(?:\?[^"]*)?)"'):
        m = re.search(padrao, html, re.I)
        if m:
            return m.group(1).strip()
    return None


def _n(s: str) -> int:
    return int(s.replace(".", ""))


def _f(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def parse_quadro01(texto: str) -> dict:
    """Quadro 01: uma linha por Região de Saúde — 'reg pop dengue chik zika oropouche arbo inc×5'.
    Exige ≥MIN_REGIOES regiões, a linha Total, e que a soma das regiões feche com o Total em cada agravo.
    Função pura; ValueError se algo essencial falhar — nunca adivinha."""
    linha = re.compile(r"^\s*(\d{1,2})\s+(\d{5,8})\s+(\d[\d.]*)\s+(\d[\d.]*)\s+(\d[\d.]*)\s+(\d[\d.]*)\s+(\d[\d.]*)\s+"
                       r"([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s*$", re.M)
    regioes = {}
    for m in linha.finditer(texto):
        regioes[int(m.group(1))] = {
            "populacao": _n(m.group(2)), "dengue_provaveis": _n(m.group(3)), "chik_provaveis": _n(m.group(4)),
            "zika_provaveis": _n(m.group(5)), "oropouche_confirmados": _n(m.group(6)), "arbo_provaveis": _n(m.group(7)),
            "inc_dengue_100k": _f(m.group(8)), "inc_chik_100k": _f(m.group(9)), "inc_zika_100k": _f(m.group(10)),
            "inc_oropouche_100k": _f(m.group(11)), "inc_arbo_100k": _f(m.group(12))}
    mt = re.search(r"^\s*Total\s+(\d{5,8})\s+(\d[\d.]*)\s+(\d[\d.]*)\s+(\d[\d.]*)\s+(\d[\d.]*)\s+(\d[\d.]*)\s+"
                   r"([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s*$", texto, re.M)
    if not mt:
        raise ValueError("Quadro 01: linha 'Total' não encontrada")
    total = {"populacao": _n(mt.group(1)), "dengue_provaveis": _n(mt.group(2)), "chik_provaveis": _n(mt.group(3)),
             "zika_provaveis": _n(mt.group(4)), "oropouche_confirmados": _n(mt.group(5)), "arbo_provaveis": _n(mt.group(6)),
             "inc_dengue_100k": _f(mt.group(7)), "inc_chik_100k": _f(mt.group(8)), "inc_zika_100k": _f(mt.group(9)),
             "inc_oropouche_100k": _f(mt.group(10)), "inc_arbo_100k": _f(mt.group(11))}
    if len(regioes) < MIN_REGIOES:
        raise ValueError(f"Quadro 01: só {len(regioes)} de 16 regiões reconhecidas — resultado recusado")
    for campo in ("populacao", "dengue_provaveis", "chik_provaveis", "zika_provaveis", "oropouche_confirmados", "arbo_provaveis"):
        soma = sum(r[campo] for r in regioes.values())
        if soma != total[campo]:
            raise ValueError(f"Quadro 01: soma das regiões em '{campo}' ({soma}) ≠ Total ({total[campo]})")
    return {"por_regiao": regioes, "total": total}


def parse_fluxograma(texto: str) -> dict:
    """Fluxograma 01: blocos 'Notificados/Prováveis/Confirmados/Descartados' com 'Agravo N' em linhas seguintes.
    Exige notificados = prováveis + descartados e confirmados ≤ prováveis para dengue e chikungunya."""
    def bloco(rotulo: str) -> dict:
        m = re.search(rotulo + r"\s*\n((?:\s*(?:Dengue|Chikungunya|Zika|Oropouche)\s*\n\s*[\d.]+\s*\n?)+)", texto, re.I)
        if not m:
            raise ValueError(f"Fluxograma 01: bloco '{rotulo}' não encontrado")
        return {a.lower(): _n(v) for a, v in re.findall(r"(Dengue|Chikungunya|Zika|Oropouche)\s*\n\s*([\d.]+)", m.group(1), re.I)}
    f = {"notificados": bloco("Notificados"), "provaveis": bloco("Prováveis"),
         "confirmados": bloco("Confirmados"), "descartados": bloco("Descartados")}
    for ag in ("dengue", "chikungunya"):
        n, p, d = f["notificados"].get(ag), f["provaveis"].get(ag), f["descartados"].get(ag)
        if None in (n, p, d):
            raise ValueError(f"Fluxograma 01: {ag} incompleto (n={n} p={p} d={d})")
        if n != p + d:
            raise ValueError(f"Fluxograma 01: {ag}: notificados ({n}) ≠ prováveis ({p}) + descartados ({d})")
        if f["confirmados"].get(ag, 0) > p:
            raise ValueError(f"Fluxograma 01: {ag}: confirmados > prováveis")
    return f


def parse_texto(texto: str) -> dict:
    m = re.search(r"at[ée] a semana epidemiol[óo]gica (\d{1,2})\s*\n?\s*totalizam ([\d.]+)", texto, re.I)
    if not m:
        m2 = re.search(r"At[ée] a SE (\d{1,2}) de (\d{4}) foram notificados", texto, re.I)
        if not m2:
            raise ValueError("referência da semana epidemiológica não encontrada")
        se, arbo_texto = int(m2.group(1)), None
    else:
        se, arbo_texto = int(m.group(1)), _n(m.group(2))
    man = re.search(r"^\s*(\d{2})/(\d{4})\s*$", texto, re.M)
    numero = int(man.group(1)) if man else None
    ano = int(man.group(2)) if man else None
    # 11/09/2026 (achado grave da verificação em navegador real): a URL adivinhada
    # .../boletim-epidemiologico-arboviroses-urbanas-no-03_2026.pdf serviu, no acesso público, o boletim
    # "Nº 05 — 20.04.2023". Ou seja, o nome do arquivo NÃO garante a edição: o padrão de URL é inferido, não
    # publicado. Sem esta guarda, uma rodada gravaria dado de 2023 como leitura corrente. O ano lido DENTRO do
    # documento manda; divergência do ano corrente = recusa.
    if ano is not None and ano != ANO_ESPERADO[0]:
        raise ValueError(f"ano do documento ({ano}) ≠ ano corrente ({ANO_ESPERADO[0]}): a URL pode ter servido edição antiga — recusado")
    quadro = parse_quadro01(texto)
    flux = parse_fluxograma(texto)
    if quadro["total"]["dengue_provaveis"] != flux["provaveis"].get("dengue"):
        raise ValueError(f"Quadro 01 × Fluxograma: dengue prováveis {quadro['total']['dengue_provaveis']} ≠ {flux['provaveis'].get('dengue')}")
    d = {"referencia": {"numero": numero, "ano": ano, "se": se}, "quadro_por_regiao": quadro, "fluxograma": flux}
    if arbo_texto is not None and arbo_texto != quadro["total"]["arbo_provaveis"]:
        d["divergencia_fonte"] = (f"o texto corrido do boletim diz {arbo_texto} casos prováveis de arboviroses, "
                                  f"o Quadro 01 totaliza {quadro['total']['arbo_provaveis']}; publicado o do Quadro (auditável linha a linha)")
    return d


def coletar() -> int:
    hoje = _hoje(); ano = hoje.year
    ANO_ESPERADO[0] = ano
    pdf_url = bruto = None
    interstícios = []
    for num in range(TETO_NUMERO, 0, -1):
        url = PADRAO_URL.format(n=num, ano=ano)
        try:
            # 11/09/2026 (achado da rodada de 22h): timeout de 60s x 24 tentativas x até 2 pedidos por tentativa
            # podia levar quase 50 min no pior caso. O diagnóstico mostrou resposta em ~1s quando o portal
            # responde; 12s é folgado sem represar a rodada quando não responde.
            b = buscar(url, timeout=12)
        except Exception:  # noqa: BLE001
            continue
        if b[:4] == b"%PDF":
            pdf_url, bruto = url, b; break
        # 11/09/2026 (achado da 1ª rodada real): o portal responde HTTP 200 com text/html — uma página de
        # espera do Plone ("Pragma: no-cache", meta refresh / redirecionamento por JS) em vez do arquivo.
        # O coletor recusava, corretamente, tudo que não começasse com %PDF. Agora segue o destino declarado
        # DENTRO dessa página (meta refresh, window.location ou link .pdf) — sem adivinhar URL nenhuma.
        destino = destino_do_intersticio(b)
        if destino:
            try:
                b2 = buscar(destino if destino.startswith("http") else BASE + destino, timeout=12)
            except Exception:  # noqa: BLE001
                interstícios.append(f"nº {num:02d}: destino do interstício não respondeu"); continue
            if b2[:4] == b"%PDF":
                pdf_url, bruto = (destino if destino.startswith("http") else BASE + destino), b2; break
            interstícios.append(f"nº {num:02d}: destino do interstício não é PDF")
        elif b[:15].lower().startswith(b"<!doctype html") or b[:5].lower() == b"<html":
            interstícios.append(f"nº {num:02d}: HTML sem destino declarado")
    if not pdf_url:
        detalhe = f"nenhum boletim nº 01–{TETO_NUMERO} de {ano} respondeu com PDF"
        if interstícios:
            detalhe += f" — o portal devolveu HTML em vez do arquivo ({'; '.join(interstícios[:4])})"
        registrar_lacuna("SES-PB (boletim de arboviroses)", detalhe, canal="site_estadual", camada=2, strings=[PADRAO_URL.format(n=1, ano=ano)])
        print("boletim PB: nenhum número respondeu — lacuna declarada"); return 0
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(bruto)) as pdf:
            texto = "\n".join((pg.extract_text() or "") for pg in pdf.pages)
    except Exception as e:  # noqa: BLE001
        registrar_lacuna(f"SES-PB boletim {pdf_url[-30:]}", type(e).__name__, canal="site_estadual", camada=2, strings=[pdf_url])
        print("boletim PB: falha ao ler o PDF — lacuna declarada"); return 0
    try:
        dados = parse_texto(texto)
    except ValueError as e:
        registrar_lacuna("SES-PB (formato do boletim)", str(e)[:180], canal="site_estadual", camada=2, strings=[pdf_url])
        print(f"boletim PB: {e} — coletor não adivinha; nada publicado"); return 0
    serie = ler("saude_desfechos/ses_pb_arboviroses.json", {"_governanca": "Arboviroses na Paraíba (dengue, chikungunya, Zika, Oropouche) por Região de Saúde — lido do Boletim Epidemiológico de Arboviroses Urbanas da SES-PB. " + RESSALVA + " Cada leitura é o ACUMULADO do ano até a SE do boletim; a série é construída pelo próprio Monitor a partir de 10/09/2026. Boletins numerados sequencialmente, cadência irregular. Peso zero; nunca lido pelo motor.", "serie": {}})
    chave = f"{dados['referencia']['ano'] or ano}-{dados['referencia']['se']:02d}"
    serie.setdefault("serie", {})[chave] = dados
    serie["ultima_atualizacao"] = hoje.strftime("%d/%m/%Y"); serie["fonte_pdf_mais_recente"] = pdf_url
    gravar("saude_desfechos/ses_pb_arboviroses.json", serie)
    t = dados["quadro_por_regiao"]["total"]
    log_busca("site_estadual", 2, [pdf_url], "registro", nivel="estadual", n_resultados=len(dados["quadro_por_regiao"]["por_regiao"]),
              resultados=f"SES-PB: boletim nº {dados['referencia']['numero']} (SE {dados['referencia']['se']}) lido — {len(dados['quadro_por_regiao']['por_regiao'])} regiões de saúde; dengue {t['dengue_provaveis']} prováveis, chik {t['chik_provaveis']}, zika {t['zika_provaveis']}")
    print(f"boletim PB: nº {dados['referencia']['numero']} SE {dados['referencia']['se']} — {len(dados['quadro_por_regiao']['por_regiao'])} regiões; dengue {t['dengue_provaveis']}, chik {t['chik_provaveis']}, zika {t['zika_provaveis']}, arbo {t['arbo_provaveis']}")
    return 0


# Texto REAL extraído do boletim nº 03/2026 (SE 08), lido em 10/09/2026 — só os trechos que o parser consome.
TEXTO_REAL_N03 = """03/2026
Observa-se que os casos prováveis de arboviroses em 2026, até a semana epidemiológica 8
totalizam 739, sendo 90,80% para dengue e 9,20% para chikungunya (Gráfico 01).
Confirmados
Dengue 
514
Chikungunya
16
Oropouche
0
Zika
0
Descartados
Dengue
592
Chikungunya
173
Zika 
0
Notificados
Dengue 
1.263
Chikungunya
240
Zika 
0
Prováveis
Dengue 
671
Chikungunya
67
Zika 
0
Reg. Pop. Dengue Prováveis Chik Prováveis Zika Prováveis Confirmados Oropouche Prováveis Arbo Inc Dengue
1 1336175 509 12 0 0 521 38,09 0,90 0,00 0,00 38,99
2 307517 14 2 0 0 16 4,55 0,65 0,00 0,00 5,20
3 198338 10 2 0 0 12 5,04 1,01 0,00 0,00 6,05
4 114101 10 1 0 0 11 8,76 0,88 0,00 0,00 9,64
5 121597 13 0 0 0 13 10,69 0,00 0,00 0,00 10,69
6 239548 10 0 0 0 10 4,17 0,00 0,00 0,00 4,17
7 148467 17 0 0 0 17 11,45 0,00 0,00 0,00 11,45
8 119599 0 0 0 0 0 0,00 0,00 0,00 0,00 0,00
9 178797 3 0 0 0 3 1,68 0,00 0,00 0,00 1,68
10 118110 8 1 0 0 9 6,77 0,85 0,00 0,00 7,62
11 85509 18 0 0 0 18 21,05 0,00 0,00 0,00 21,05
12 176715 1 0 0 0 1 0,57 0,00 0,00 0,00 0,57
13 60792 1 0 0 0 1 1,64 0,00 0,00 0,00 1,64
14 154096 1 0 0 0 1 0,65 0,00 0,00 0,00 0,65
15 151796 20 0 0 0 20 13,18 0,00 0,00 0,00 13,18
16 548748 36 49 0 0 85 6,56 8,93 0,00 0,00 15,49
Total 4059905 671 67 0 0 738 16,53 1,65 0,00 0,00 18,18
"""


def autoteste() -> int:
    def t1():
        r = parse_texto(TEXTO_REAL_N03)["referencia"]
        return r == {"numero": 3, "ano": 2026, "se": 8}
    def t2():
        q = parse_texto(TEXTO_REAL_N03)["quadro_por_regiao"]
        return len(q["por_regiao"]) == 16 and q["por_regiao"][1]["dengue_provaveis"] == 509 and q["por_regiao"][1]["populacao"] == 1336175 and q["por_regiao"][16]["chik_provaveis"] == 49
    def t3():
        t = parse_texto(TEXTO_REAL_N03)["quadro_por_regiao"]["total"]
        return t["dengue_provaveis"] == 671 and t["chik_provaveis"] == 67 and t["arbo_provaveis"] == 738 and t["populacao"] == 4059905 and t["inc_dengue_100k"] == 16.53
    def t4():
        f = parse_texto(TEXTO_REAL_N03)["fluxograma"]
        return f["notificados"]["dengue"] == 1263 and f["provaveis"]["dengue"] == 671 and f["descartados"]["dengue"] == 592 and f["confirmados"]["chikungunya"] == 16
    def t5():
        # divergência entre o texto corrido (739) e o Quadro 01 (738) é registrada, não silenciada
        d = parse_texto(TEXTO_REAL_N03)
        return "divergencia_fonte" in d and "739" in d["divergencia_fonte"] and "738" in d["divergencia_fonte"]
    def t6():
        # soma das regiões não fecha com o Total → recusa
        quebrado = TEXTO_REAL_N03.replace("1 1336175 509 12", "1 1336175 500 12")
        try:
            parse_texto(quebrado); return False
        except ValueError as e:
            return "soma das regiões" in str(e)
    def t7():
        # identidade do fluxograma quebrada → recusa
        quebrado = TEXTO_REAL_N03.replace("Dengue\n592", "Dengue\n500")
        try:
            parse_texto(quebrado); return False
        except ValueError as e:
            return "notificados" in str(e)
    def t8():
        # poucas regiões → recusa (nunca publica tabela parcial)
        linhas = [l for l in TEXTO_REAL_N03.split("\n") if not re.match(r"^\s*(?:[5-9]|1[0-6])\s+\d{5,8}\s", l)]
        try:
            parse_texto("\n".join(linhas)); return False
        except ValueError as e:
            return "regiões reconhecidas" in str(e) or "soma das regiões" in str(e)
    def t8b():
        # 11/09/2026: portal devolve HTML (interstício) em vez do PDF — seguir o destino declarado, nunca adivinhar
        meta = b'<!DOCTYPE html><html><head><meta http-equiv="Pragma" content="no-cache"/>'
        a = destino_do_intersticio(meta + b'<meta http-equiv="refresh" content="0;url=/arquivos/bol.pdf"/></head></html>')
        b = destino_do_intersticio(meta + b'<script>window.location="https://x.gov.br/b.pdf";</script></head></html>')
        c = destino_do_intersticio(meta + b'<body><a href="/d/boletim_03.pdf">baixar</a></body></html>')
        d = destino_do_intersticio(meta + b'<body>sem destino</body></html>')
        return a == "/arquivos/bol.pdf" and b == "https://x.gov.br/b.pdf" and c == "/d/boletim_03.pdf" and d is None
    def t_ano_antigo():
        # 11/09/2026: a URL pública de "no-03_2026.pdf" serviu o boletim "Nº 05 — 20.04.2023".
        # Documento de ano diferente do corrente tem de ser RECUSADO, nunca gravado como leitura atual.
        antigo = TEXTO_REAL_N03.replace("03/2026", "05/2023")
        ANO_ESPERADO[0] = 2026
        try:
            parse_texto(antigo); return False
        except ValueError as e:
            return "ano do documento" in str(e)

    def t9():
        try:
            parse_texto("nada aqui bate com o padrão esperado"); return False
        except ValueError:
            return True
    def t10():
        return "não atribui casos ao El Niño" in RESSALVA and MIN_REGIOES < 16 and "{n:02d}" in PADRAO_URL
    return rodar_autoteste({"documento de ano antigo servido pela URL → recusa": t_ano_antigo,"referência (nº do boletim, ano, SE)": t1, "Quadro 01: 16 Regiões de Saúde": t2,
                            "Quadro 01: linha Total e incidências": t3, "Fluxograma 01 por agravo": t4,
                            "divergência da fonte registrada (739 × 738)": t5,
                            "soma das regiões ≠ Total → recusa": t6, "identidade do fluxograma quebrada → recusa": t7,
                            "tabela parcial → recusa": t8,
                            "interstício HTML: segue destino declarado, nunca adivinha": t8b, "formato inesperado nunca adivinha": t9,
                            "ressalva, limiar e padrão de URL": t10})


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else coletar())
