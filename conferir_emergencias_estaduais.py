#!/usr/bin/env python3
"""Confere no diário oficial cada emergência declarada por governo de estado (`data/emergencias_estaduais.json`).

O ato entra no arquivo pela leitura do diário (`coletar_edicoes_doe.py` acha o decreto que declara emergência em
todo o estado; 15/11/2026: até então só a curadoria, e o Decreto nº 7.251 do Tocantins ficou de fora) ou por
curadoria, com o endereço da edição (PDF do diário ou página oficial do ato); só vai ao mapa com `conferido: true`, que este
script grava depois de achar no texto da edição o número do decreto, a data por extenso e a palavra emergência,
com a cópia preservada em `evidencias/`. Não achou: fica `conferido: false`, com o motivo, e o mapa não o mostra.
`vigente_ate` = publicação + dias − 1 (vigor na data da publicação, dias corridos).

Prorrogação: `coletar_edicoes_doe.py` lê cada edição do diário do estado e marca nela o decreto que
prorroga um ato daqui; este script, sem rede, soma os dias à vigência e diz até onde o diário foi lido.

USO
  python3 conferir_emergencias_estaduais.py --autoteste
  python3 conferir_emergencias_estaduais.py [--forcar]
"""
import datetime
import re
import sys

from coletores_base import RAIZ, gravar_em, hoje_editorial, ler, rodar_autoteste

ARQUIVO = RAIZ / "data" / "emergencias_estaduais.json"
MESES = "janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro".split()


def confere(ato: dict, texto: str) -> str:
    """'' quando o texto traz o decreto; senão, o que faltou. Pura."""
    t = " ".join(str(texto or "").split())
    d = datetime.date.fromisoformat(ato["data_ato"])
    faltou = []
    if not re.search(r"DECRETO\s+N[ºo°.]*\s*" + re.escape(ato["numero"]) + r"\b", t, re.I):
        faltou.append(f"Decreto nº {ato['numero']}")
    if not re.search(rf"\b0?{d.day}º?\s+de\s+{MESES[d.month - 1]}\s+de\s+{d.year}", t, re.I):
        faltou.append(f"a data {d.day} de {MESES[d.month - 1]} de {d.year}")
    if not re.search(r"emerg[êe]ncia", t, re.I):
        faltou.append("a palavra emergência")
    return "não achados no texto da edição: " + ", ".join(faltou) if faltou else ""


def vigente_ate(ato: dict) -> str:
    dias = ato["dias"] + sum(p["dias"] for p in ato.get("prorrogacoes") or [])
    return (datetime.date.fromisoformat(ato["data_publicacao"]) + datetime.timedelta(days=dias - 1)).isoformat()


# Cabeçalho de ato no diário, em maiúsculas (a citação no corpo vem em minúsculas: "Decreto n.º").
RX_CABECALHO = re.compile(r"DECRETO\s+N[ºO°.]*\s*([\d.]{3,12})\s*,?\s+DE\s+(\d{1,2})\.?[º°]?\s+DE\s+("
                          + "|".join(m.upper() for m in MESES) + r")\s+DE\s+(\d{4})")
RX_PRORROGA = re.compile(r"prorrog.{0,400}emerg[êe]ncia|emerg[êe]ncia.{0,400}prorrog", re.I)
RX_DIAS = re.compile(r"(\d{1,3})\s*\([^)]{3,40}\)\s*dias", re.I)
RX_DECLARA = re.compile(r"declar\w*[^.;]{0,200}?(?:situa[çc][ãa]o|estado)\s+de\s+emerg[êe]ncia", re.I)
RX_TODO_ESTADO = re.compile(r"tod[oa]\s+(?:a\s+|o\s+)?(?:territ[óo]rio|extens[ãa]o\s+territorial)\s+(?:do|da|deste|desta|estadual)"
                            r"|territ[óo]rio\s+estadual|todos\s+os\s+munic[íi]pios\s+d[oe]\s+Estado", re.I)
RX_NAO_E_DECLARACAO = re.compile(r"prorrog|homolog|revoga|sa[úu]de\s+p[úu]blica|epidemi|dengue|arbovir", re.I)
NATUREZAS = (("por estiagem", r"estiagem|\bseca\b|h[íi]dric"), ("por incêndios florestais", r"inc[êe]ndio|queimada"),
             ("por chuvas", r"chuva|inunda|enchente|alagamento|desliza"))
JANELA_DIAS = 30        # antes e depois do vencimento: quando o diário do estado é lido toda noite
ATRASO_TOLERADO = 7     # dias corridos sem edição lida, dentro da janela, antes de avisar


def prorrogacoes_no_texto(atos: list, texto: str) -> list:
    """Decretos do texto que prorrogam a emergência de um dos `atos`. Função pura.
    Vale o decreto posterior ao ato cujo corpo cita o número dele e fala em prorrogar a emergência;
    sem prazo escrito, o período é o do ato ("por igual período"). Na dúvida, não acha."""
    t = " ".join(str(texto or "").split())
    cab, achados = list(RX_CABECALHO.finditer(t)), []
    for ato in atos or []:
        outros = [m for m in cab if m.group(1) != ato["numero"]]
        for i, m in enumerate(outros):
            fim = outros[i + 1].start() if i + 1 < len(outros) else len(t)
            corpo = t[m.end():min(fim, m.end() + 6000)]
            data = datetime.date(int(m.group(4)), [x.upper() for x in MESES].index(m.group(3)) + 1, int(m.group(2)))
            if (data > datetime.date.fromisoformat(ato["data_ato"]) and RX_PRORROGA.search(corpo)
                    and re.search(r"(?<![\d.])" + re.escape(ato["numero"]) + r"(?![\d])", corpo)):
                dias = RX_DIAS.search(corpo)
                achados.append({"de": ato["numero"], "numero": m.group(1), "data_ato": data.isoformat(),
                                "dias": int(dias.group(1)) if dias else ato["dias"]})
    return achados


def declaracoes_no_texto(texto: str) -> list:
    """Decretos do texto que declaram emergência em todo o estado: candidatos à camada, que `confere` ainda
    acha na edição. Prorrogação, homologação de município e emergência em saúde (outro canal) não entram;
    sem prazo escrito nem alcance estadual, também não: na dúvida, não acha. Função pura."""
    t = " ".join(str(texto or "").split())
    cab, achados = list(RX_CABECALHO.finditer(t)), []
    for i, m in enumerate(cab):
        corpo = t[m.end():min(cab[i + 1].start() if i + 1 < len(cab) else len(t), m.end() + 6000)]
        ementa, dias = corpo[:1500], RX_DIAS.search(corpo)
        if not (RX_DECLARA.search(ementa) and RX_TODO_ESTADO.search(ementa) and dias) or RX_NAO_E_DECLARACAO.search(ementa[:400]):
            continue
        achados.append({"numero": m.group(1), "dias": int(dias.group(1)),
                        "data_ato": datetime.date(int(m.group(4)), [x.upper() for x in MESES].index(m.group(3)) + 1,
                                                  int(m.group(2))).isoformat(),
                        "natureza": next((n for n, rx in NATUREZAS if re.search(rx, ementa, re.I)), "declarada pelo estado"),
                        "preventiva": bool(re.search(r"car[áa]ter\s+preventivo", ementa, re.I))})
    return achados


def incorporar_declaracoes(doc: dict, uf: str, declaracoes: list, fonte: str) -> list:
    """Põe em `doc['atos']` o decreto que a leitura do diário achou e o arquivo não tem (`conferido: false`
    até `confere` o achar na edição). Devolve os novos. Função pura."""
    tem = {(a["uf"], a["numero"]) for a in doc.setdefault("atos", [])}
    novos = []
    for d in declaracoes or []:
        if (uf, d["numero"]) in tem:
            continue
        tem.add((uf, d["numero"]))
        novos.append({"uf": uf, "natureza": d["natureza"], "numero": d["numero"], "data_ato": d["data_ato"],
                      "data_publicacao": d["data_publicacao"], "dias": d["dias"], "fonte": fonte, "edicao": None,
                      "pagina": d.get("pagina"), "url": d["url"], "preventiva": d["preventiva"] or None, "conferido": False,
                      "motivo": "achado na leitura do diário; conferência pendente", "prorrogacoes": []})
    doc["atos"] += novos
    return novos


def em_janela(ato: dict, hoje: str) -> bool:
    return bool(ato.get("conferido") and ato.get("vigente_ate")
                and abs((datetime.date.fromisoformat(ato["vigente_ate"]) - datetime.date.fromisoformat(hoje)).days) <= JANELA_DIAS)


def ufs_em_janela(doc: dict, hoje: str) -> list:
    return sorted({a["uf"] for a in (doc or {}).get("atos", []) if em_janela(a, hoje)})


def aplicar_prorrogacoes(ato: dict, edicoes: dict, hoje: str) -> str:
    """Grava no ato as prorrogações que o diário lido traz e até onde o diário foi lido; devolve o
    atraso a avisar, ou ''. Só lê o que `coletar_edicoes_doe` já gravou: nenhuma rede aqui."""
    achadas = {}
    for data, e in sorted((edicoes or {}).items()):
        for p in (e or {}).get("prorrogacoes") or []:
            if p["de"] == ato["numero"]:
                achadas[p["numero"]] = {"numero": p["numero"], "data_ato": p["data_ato"], "dias": p["dias"],
                                        "data_publicacao": data.split("#")[0], "url": e.get("url"),
                                        "hash_evidencia": e.get("hash_evidencia")}
    lidas = sorted(d.split("#")[0] for d, e in (edicoes or {}).items() if (e or {}).get("decisao") == "lida")
    ato["prorrogacoes"] = sorted(achadas.values(), key=lambda p: p["data_ato"])
    ato["vigente_ate"] = vigente_ate(ato)
    ato["diario_lido_ate"] = lidas[-1] if lidas else None
    if not em_janela(ato, hoje):
        return ""
    atraso = (datetime.date.fromisoformat(hoje) - datetime.date.fromisoformat(lidas[-1])).days if lidas else None
    if atraso is None or atraso > ATRASO_TOLERADO:
        return (f"{ato['uf']}, Decreto nº {ato['numero']} (vence em {ato['vigente_ate']}): diário do estado "
                + (f"sem edição lida há {atraso} dias" if lidas else "sem nenhuma edição lida")
                + " — prorrogação não verificável")
    return ""


def autoteste() -> int:
    am = {"uf": "AM", "numero": "54.274", "data_ato": "2026-06-01", "data_publicacao": "2026-06-01", "dias": 180,
          "conferido": True, "vigente_ate": "2026-11-27"}
    PRORROGA_AM = ("DECRETO N.º 55.009, DE 24 DE NOVEMBRO DE 2026 NOMEIA servidor. DECRETO N.º 55.010, DE 25 DE "
                   "NOVEMBRO DE 2026 PRORROGA o Estado de Emergência Climática e Ambiental declarado pelo Decreto "
                   "n.º 54.274, de 1.º de junho de 2026. Art. 1.º Fica prorrogado, por 180 (cento e oitenta) dias, o "
                   "estado de emergência. DECRETO N.º 55.013, DE 25 DE NOVEMBRO DE 2026 EXONERA.")
    EDICOES_AM = {"2026-11-26": {"decisao": "lida", "url": "https://exemplo/18300", "hash_evidencia": "h",
                                 "prorrogacoes": prorrogacoes_no_texto([am], PRORROGA_AM)}}
    DECLARA_TO = ("DECRETO Nº 7.250, DE 19 DE OUTUBRO DE 2026 Nomeia servidor. DECRETO Nº 7.251, DE 19 DE OUTUBRO DE 2026 "
                  "DECLARA situação de emergência em todo o território do Estado do Tocantins, em razão da estiagem prolongada. "
                  "Art. 1º Fica declarada situação de emergência, pelo prazo de 180 (cento e oitenta) dias.")
    ato = {"numero": "5.767", "data_ato": "2026-11-11", "data_publicacao": "2026-11-12", "dias": 120}
    bom = "DECRETO Nº 5.767, DE 11 DE NOVEMBRO DE 2026 Declara situação de emergência ambiental e climática"
    return rodar_autoteste({
        "edição com número, data por extenso e emergência confere": lambda: confere(ato, bom) == "",
        "outro número não confere (5.7670 nem 5.76)": lambda: "5.767" in confere(ato, bom.replace("5.767", "5.7670"))
            and "Decreto nº 5.76" in confere({**ato, "numero": "5.76"}, bom.replace("5.767", "5.769")),
        "data ausente e sem emergência são nomeadas": lambda: confere(ato, "DECRETO Nº 5.767 Dispõe sobre férias")
            == "não achados no texto da edição: a data 11 de novembro de 2026, a palavra emergência",
        "vigência: 120 dias corridos a partir da publicação": lambda: vigente_ate(ato) == "2027-03-11",
        "página de legislação (N.º, 1º de junho) confere": lambda: confere(
            {"numero": "54.274", "data_ato": "2026-06-01"},
            "DECRETO N.º 54.274, DE 1º DE JUNHO DE 2026 DECLARA, em caráter preventivo, Estado de Emergência Climática") == "",
        "prorrogação: decreto posterior que cita o número e prorroga a emergência, com o prazo escrito": lambda:
            prorrogacoes_no_texto([am], PRORROGA_AM) == [{"de": "54.274", "numero": "55.010", "data_ato": "2026-11-25", "dias": 180}],
        "prorrogação por igual período herda os dias do ato; a edição do próprio ato não é prorrogação": lambda:
            prorrogacoes_no_texto([am], PRORROGA_AM.replace("180 (cento e oitenta) dias", "igual período"))[0]["dias"] == 180
            and prorrogacoes_no_texto([am], "DECRETO N.º 54.274, DE 1.º DE JUNHO DE 2026 DECLARA Estado de Emergência. "
                                            "Art. 13. podendo ser prorrogado") == [],
        "outro decreto que só cita o número, ou prorroga outra coisa, não é prorrogação": lambda:
            prorrogacoes_no_texto([am], "DECRETO N.º 55.011, DE 25 DE NOVEMBRO DE 2026 ABRE crédito para as ações do "
                                        "Decreto n.º 54.274, de 1.º de junho de 2026.") == []
            and prorrogacoes_no_texto([am], "DECRETO N.º 55.012, DE 25 DE NOVEMBRO DE 2026 PRORROGA a situação de "
                                            "emergência no Município de Tefé, de que trata o Decreto n.º 54.999.") == [],
        "aplicada, a prorrogação estende a vigência e não se soma duas vezes": lambda: (lambda a: (
            aplicar_prorrogacoes(a, EDICOES_AM, "2026-11-27"), aplicar_prorrogacoes(a, EDICOES_AM, "2026-11-28"),
            a["vigente_ate"], len(a["prorrogacoes"]), a["diario_lido_ate"])[2:])(dict(am)) == ("2027-05-26", 1, "2026-11-26"),
        "diário sem edição lida há mais de sete dias, perto do vencimento, vira aviso; longe, não": lambda:
            "sem edição lida há 12 dias" in aplicar_prorrogacoes(dict(am), {"2026-11-10": {"decisao": "lida"}}, "2026-11-22")
            and aplicar_prorrogacoes(dict(am), {"2026-08-10": {"decisao": "lida"}}, "2026-08-30") == ""
            and ufs_em_janela({"atos": [am, dict(am, uf="PA", vigente_ate="2027-03-11")]}, "2026-11-15") == ["AM"],
        "declaração em todo o estado, com prazo escrito, vira candidato com a natureza do texto": lambda:
            declaracoes_no_texto(DECLARA_TO) == [{"numero": "7.251", "dias": 180, "data_ato": "2026-10-19",
                                                  "natureza": "por estiagem", "preventiva": False}],
        "homologação de município, prorrogação, saúde pública e decreto sem alcance estadual não são declaração": lambda: [
            declaracoes_no_texto(DECLARA_TO.replace("DECLARA", x)) for x in ("HOMOLOGA o decreto que declara", "PRORROGA a")]
            == [[], []] and declaracoes_no_texto(DECLARA_TO.replace("estiagem", "emergência em saúde pública")) == []
            and declaracoes_no_texto(DECLARA_TO.replace("em todo o território do Estado do Tocantins", "no Município de Pium")) == []
            and declaracoes_no_texto(DECLARA_TO.replace("180 (cento e oitenta) dias", "prazo indeterminado")) == [],
        "incorporar: entra uma vez, não conferido, e o que já existe não muda": lambda: (lambda doc: (
            len(incorporar_declaracoes(doc, "TO", [dict(declaracoes_no_texto(DECLARA_TO)[0], data_publicacao="2026-10-20",
                                                         url="https://exemplo/to.pdf", pagina=1)] * 2, "Diário Oficial (Tocantins)")),
            incorporar_declaracoes(doc, "AM", [{"numero": "54.274"}], "x"), doc["atos"][-1]["conferido"],
            len(doc["atos"])))({"atos": [dict(am)]}) == (1, [], False, 2),
        "garantia estrutural: a conferência roda toda noite no elo dos sinais, depois da leitura do diário": lambda: (
            lambda w: 0 < w.find("coletar_edicoes_doe.py --emergencias") < w.find("conferir_emergencias_estaduais.py"))(
            (RAIZ / ".github/workflows/noturno_sinais.yml").read_text(encoding="utf-8")),
        "garantia estrutural: só grava o próprio arquivo": lambda: re.findall(
            r"gravar_em\(([^,)]+)", open(__file__, encoding="utf-8").read()) == ["ARQUIVO"],
    })


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    from coletores_base import buscar, preservar_evidencia
    from scripts.sondar_documento import texto_de
    from coletar_saude_estadual import UF_NOME
    doc = ler("emergencias_estaduais.json", {"atos": []})
    for uf, nome in UF_NOME.items():
        for novo in incorporar_declaracoes(doc, uf, list(((ler(f"doe_edicoes/{uf}.json", {}) or {}).get(
                "declaracoes_estaduais") or {}).values()), f"Diário Oficial ({nome})"):
            print(f"[{uf}] Decreto nº {novo['numero']}: achado na leitura do diário, a conferir")
    for ato in doc["atos"]:
        if ato.get("conferido") and "--forcar" not in sys.argv:
            continue
        try:
            corpo = buscar(ato["url"], timeout=180, origem="conferir_emergencias_estaduais")
        except Exception as e:  # noqa: BLE001 — fonte externa: fica não conferido, com o motivo
            ato.update(conferido=False, motivo=f"edição não lida: {type(e).__name__}: {str(e)[:80]}")
            continue
        tipo, texto, _ = texto_de(corpo)
        motivo = confere(ato, texto)
        ato.update(conferido=not motivo, motivo=motivo or None, vigente_ate=vigente_ate(ato),
                   hash_evidencia=preservar_evidencia(corpo, ato["url"], tipo, "conferir_emergencias_estaduais") if not motivo else None,
                   conferido_em=hoje_editorial().isoformat())
        print(f"[{ato['uf']}] Decreto nº {ato['numero']}: {'conferido' if not motivo else motivo}")
    hoje = hoje_editorial().isoformat()
    atrasos = [x for x in (aplicar_prorrogacoes(ato, (ler(f"doe_edicoes/{ato['uf']}.json", {}) or {}).get("edicoes"), hoje)
                           for ato in doc["atos"] if ato.get("conferido")) if x]
    doc.update(verificado_em=hoje, atrasos=atrasos)
    for x in atrasos:
        print(f"::warning::{x}")
    gravar_em(ARQUIVO, doc)
    try:
        avisar(atrasos)
    except Exception as e:  # noqa: BLE001 — o aviso é do GitHub; a conferência já está gravada
        print(f"::warning::aviso não enviado: {type(e).__name__}")
    return 0


TITULO_DO_AVISO = "Emergência estadual: prorrogação não verificável"


def avisar(atrasos: list, gh=None) -> None:
    """Uma Issue enquanto houver atraso; fecha sozinha. Falha do GitHub não derruba a coleta."""
    from scripts import avisos
    avisos.avisar(TITULO_DO_AVISO, "\n".join(f"- {x}" for x in atrasos), "Diário lido de novo. Fechada.", gh or avisos._gh)


if __name__ == "__main__":
    sys.exit(main())
