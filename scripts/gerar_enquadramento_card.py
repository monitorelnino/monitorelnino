#!/usr/bin/env python3
"""Deriva o arquivo enxuto que o cartão do município lê: quem consta de qual lista federal.

PR 4 do handover do enquadramento federal de risco (editoria, 30/09/2026).

POR QUE UM DERIVADO, E NÃO A LEITURA DOS DOIS ARQUIVOS DE ORIGEM
----------------------------------------------------------------
As duas bases de origem servem à transparência e carregam o que ela pede: `cadastro_prioritarios_
federal.json` tem 2.095 registros com nome, UF, ano de acréscimo, tipos de risco e o campo do
art. 3º-A à espera da LAI — 680 kB. `enquadramento_federal.json` tem 1.568 registros com
instrumento e procedência. O cartão precisa de três marcas e um complemento de texto: baixar
680 kB no telemóvel de quem consultou uma cidade para desenhar uma linha seria caro sem motivo.

Este derivado tem só o que a página usa, com chaves curtas. **Não é fonte de nada**: nasce dos
dois arquivos acima, pela cadeia canônica, e não se edita à mão.

A LINHA DE CHUVA SÓ APARECE PARA QUEM CONSTA DO CADASTRO PUBLICADO
------------------------------------------------------------------
O texto aprovado diz "Consta do cadastro federal de municípios suscetíveis a enxurradas e
inundações". Então a marca é `cadastro_casa_civil_2086`, não `prioritario_2095`: os 9 municípios
que só têm risco de deslizamento estão fora do cadastro publicado — a Lei 11.445 trata de
enxurrada e inundação — e dizer que eles constam dele seria falso. Eles continuam no arquivo de
origem, com seus flags, para quem for ver a base.

Pela mesma razão o complemento "Risco identificado" nomeia apenas inundação e enxurrada, que é o
vocabulário do cadastro. Deslizamento aparece nos tipos da nota técnica, e o site não o promove a
risco do cadastro.

USO
    python3 scripts/gerar_enquadramento_card.py
    python3 scripts/gerar_enquadramento_card.py --autoteste
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

CASA_CIVIL = RAIZ / "data" / "cadastro_prioritarios_federal.json"
ENQUADRAMENTO = RAIZ / "data" / "enquadramento_federal.json"
SAIDA = RAIZ / "data" / "enquadramento_card.json"

GOVERNANCA = (
    "DERIVADO — nasce de cadastro_prioritarios_federal.json e enquadramento_federal.json pela "
    "cadeia canônica; não se edita à mão e não é fonte de nada. Uma entrada por município que "
    "consta de ALGUMA lista federal de risco; quem não consta de nenhuma simplesmente não está "
    "aqui. Chaves: `ch` = consta do cadastro federal de enxurradas e inundações (Casa Civil), com "
    "o risco identificado em 'i' (inundação), 'e' (enxurrada), 'ie' (as duas) ou '' (cadastrado "
    "sem tipo nomeado na nota técnica); `tp` = TODOS os tipos de risco que a nota técnica nomeia para o município, em letras ordenadas ('d' deslizamento, 'e' enxurrada, 'i' inundação); `geo` = consta da lista de prioritários só por deslizamento, fora do cadastro de enxurradas e inundações; `sa` = integra a delimitação do Semiárido (Sudene); "
    "`mma` = consta da lista de prioritários para controle do desmatamento (MMA); `mmb` = consta "
    "da lista de desmatamento monitorado e sob controle (MMA). Camada de CONTEXTO, PESO ZERO: "
    "nada disto entra na nota do MARÉ."
)


def risco_de_chuva(tipos) -> str:
    """'i', 'e', 'ei' ou ''. Função pura.

    A ordem é fixa — inundação antes de enxurrada — para o texto do cartão ser sempre o mesmo para
    o mesmo dado. Deslizamento é ignorado de propósito: não é risco do cadastro."""
    nomes = {str(t).lower() for t in (tipos or [])}
    tem_i = any("inunda" in t for t in nomes)
    tem_e = any("enxurrada" in t for t in nomes)
    return ("i" if tem_i else "") + ("e" if tem_e else "")   # 'ie' = "inundação e enxurrada"


def tipos_da_nota(tipos) -> str:
    """Letras ordenadas de TODOS os tipos que a nota tecnica nomeia. Funcao pura.

    `risco_de_chuva` responde o que o CADASTRO cobre (enxurrada e inundacao, o vocabulario da Lei
    11.445). Esta responde o que a FONTE registra, e inclui deslizamento — que estava sendo
    descartado em 1.050 municipios do cadastro: o dado existia na nota e nao chegava ao leitor.
    """
    nomes = {str(t).lower() for t in (tipos or [])}
    letras = []
    if any("desliz" in t for t in nomes):
        letras.append("d")
    if any("enxurrada" in t for t in nomes):
        letras.append("e")
    if any("inunda" in t for t in nomes):
        letras.append("i")
    return "".join(letras)


def registros(casa_civil: dict, enquadramento: dict) -> dict:
    """{codigo_ibge: marcas} de quem consta de alguma lista. Função pura."""
    fora = {}
    # A base da Casa Civil grava `municipios` como MAPA por código; a do enquadramento também.
    # Este leitor aceita as duas formas porque um dia uma delas foi lista, e quebrar por causa da
    # forma do contêiner não é falha que valha a pena ter.
    origem = (casa_civil or {}).get("municipios") or {}
    for r in (origem.values() if isinstance(origem, dict) else origem):
        if not isinstance(r, dict):
            continue
        codigo = str(r.get("codigo_ibge") or "").zfill(7)
        if len(codigo) != 7 or not codigo.isdigit():
            continue
        if not r.get("cadastro_casa_civil_2086"):
            # Os 9 municipios que estao na lista de prioritarios (2.095) e fora do cadastro (2.086)
            # constam por deslizamento. Dizer que eles constam do cadastro de enxurradas seria
            # falso; omiti-los tambem — eles tem linha propria, com o nome da lista deles.
            if r.get("prioritario_2095") and tipos_da_nota(r.get("tipos_de_risco")) == "d":
                fora.setdefault(codigo, {})["geo"] = 1
            continue
        marcas_cc = {"ch": risco_de_chuva(r.get("tipos_de_risco"))}
        tipos = tipos_da_nota(r.get("tipos_de_risco"))
        if tipos:
            marcas_cc["tp"] = tipos
        fora.setdefault(codigo, {}).update(marcas_cc)
    dos_dois = (enquadramento or {}).get("municipios") or {}
    if not isinstance(dos_dois, dict):
        dos_dois = {str(x.get("codigo_ibge")): x for x in dos_dois if isinstance(x, dict)}
    for codigo, r in dos_dois.items():
        codigo = str(codigo).zfill(7)
        if not (len(codigo) == 7 and codigo.isdigit()):
            continue
        marcas = {}
        if r.get("semiarido"):
            marcas["sa"] = 1
        if r.get("mma_prioritario_desmatamento"):
            marcas["mma"] = 1
        if r.get("mma_monitorado_sob_controle"):
            marcas["mmb"] = 1
        if marcas:
            fora.setdefault(codigo, {}).update(marcas)
    return dict(sorted(fora.items()))


def fontes_de(casa_civil: dict, enquadramento: dict) -> dict:
    """O instrumento e a data de consulta de cada família, para a fonte por linha. Função pura."""
    fontes_enq = (enquadramento or {}).get("fontes") or {}
    fora = {}
    if casa_civil:
        # A fonte e a nota tecnica que publica o anexo, e nao o decreto: quem nomeia municipio e
        # tipo de risco e a nota. Os dois PDFs vao como links, pela ordem em que foram lidos.
        documentos = casa_civil.get("documentos") or {}
        fora["chuva"] = {
            "instrumento": "Casa Civil, Nota Técnica nº 2/2025 e nº 1/2023",
            "prefixo": "Casa Civil",
            "url": documentos.get("nt2_2025") or casa_civil.get("fonte"),
            "urls": [["Nota Técnica nº 2/2025", documentos.get("nt2_2025")],
                     ["Nota Técnica nº 1/2023", documentos.get("nt1_2023")]],
            "consultado_em": casa_civil.get("coletado_em"),
        }
        fora["chuva"]["urls"] = [par for par in fora["chuva"]["urls"] if par[1]]
    for familia, chave in (("seca", "semiarido"), ("fogo", "mma_desmatamento")):
        origem = fontes_enq.get(chave)
        if origem:
            fora[familia] = {"instrumento": origem.get("instrumento"), "url": origem.get("url"),
                             "consultado_em": origem.get("consultado_em")}
    return fora


def autoteste() -> int:
    cc = {"fonte": "https://exemplo", "coletado_em": "2026-09-30", "municipios": [
        {"codigo_ibge": "1200054", "cadastro_casa_civil_2086": True,
         "tipos_de_risco": ["deslizamento", "enxurrada", "inundação"]},
        {"codigo_ibge": "1200055", "cadastro_casa_civil_2086": True,
         "tipos_de_risco": ["inundação"]},
        {"codigo_ibge": "3501152", "cadastro_casa_civil_2086": False,
         "prioritario_2095": True, "tipos_de_risco": ["deslizamento"]},
    ]}
    enq = {"fontes": {"semiarido": {"instrumento": "Sudene", "url": "u1",
                                    "consultado_em": "2026-09-30"},
                      "mma_desmatamento": {"instrumento": "MMA", "url": "u2",
                                           "consultado_em": "2026-09-30"}},
           "municipios": {"2900207": {"semiarido": True},
                          "1500602": {"mma_prioritario_desmatamento": True,
                                      "mma_monitorado_sob_controle": False},
                          "5100250": {"mma_monitorado_sob_controle": True},
                          "1200054": {"semiarido": False}}}
    r = registros(cc, enq)
    casos = [
        ("inundação e enxurrada viram 'ie'", r["1200054"]["ch"] == "ie"),
        ("só inundação vira 'i'", r["1200055"]["ch"] == "i"),
        ("só enxurrada vira 'e'", risco_de_chuva(["enxurrada"]) == "e"),
        ("deslizamento sozinho não nomeia risco de chuva", risco_de_chuva(["deslizamento"]) == ""),
        ("cadastrado sem tipo fica com complemento vazio", risco_de_chuva([]) == ""),
        ("tipos nulos não quebram", risco_de_chuva(None) == ""),
        ("a ordem é sempre inundação antes de enxurrada",
         risco_de_chuva(["enxurrada", "inundação"]) == "ie"),
        ("quem está fora do cadastro publicado não ganha linha de chuva",
         "ch" not in r.get("3501152", {})),
        ("só deslizamento fora do cadastro ganha a marca própria", r["3501152"] == {"geo": 1}),
        ("os tipos da nota técnica vão completos, deslizamento incluído",
         r["1200054"]["tp"] == "dei"),
        ("Semiárido marcado", r["2900207"]["sa"] == 1),
        ("prioritário do MMA marcado", r["1500602"]["mma"] == 1),
        ("prioritário do MMA não vira monitorado", "mmb" not in r["1500602"]),
        ("monitorado e sob controle marcado", r["5100250"]["mmb"] == 1),
        ("flag falso não entra", "sa" not in r["1200054"]),
        ("quem não consta de nada não está no arquivo",
         registros({"municipios": []}, {"municipios": {"1": {"semiarido": False}}}) == {}),
        ("um município em duas listas acumula marcas",
         registros(cc, {"municipios": {"1200054": {"semiarido": True}}})["1200054"] ==
         {"ch": "ie", "tp": "dei", "sa": 1}),
        ("chaves em ordem de código", list(r) == sorted(r)),
        ("código curto é preenchido com zeros",
         "0123456" in registros({"municipios": [{"codigo_ibge": "123456",
                                                 "cadastro_casa_civil_2086": True}]}, {})),
        ("código que não é número é descartado",
         registros({"municipios": [{"codigo_ibge": "abc", "cadastro_casa_civil_2086": True}]},
                   {}) == {}),
        ("bases vazias devolvem vazio", registros({}, {}) == {}),
        ("bases nulas não quebram", registros(None, None) == {}),
    ]
    f = fontes_de(cc, enq)
    casos += [
        ("três famílias com fonte", sorted(f) == ["chuva", "fogo", "seca"]),
        ("a fonte de chuva vem do arquivo da Casa Civil", f["chuva"]["consultado_em"] == "2026-09-30"),
        ("a fonte de seca vem do instrumento gravado", f["seca"]["instrumento"] == "Sudene"),
        ("família sem coletor não inventa fonte", "fogo" not in fontes_de(cc, {"fontes": {}})),
        ("sem base da Casa Civil não há fonte de chuva", "chuva" not in fontes_de({}, enq)),
    ]

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem escrita em data/.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()

    from coletores_base import gravar_em
    if not CASA_CIVIL.exists() or not ENQUADRAMENTO.exists():
        faltando = [p.name for p in (CASA_CIVIL, ENQUADRAMENTO) if not p.exists()]
        print(f"X faltam as bases de origem: {', '.join(faltando)}")
        return 1
    casa_civil = json.loads(CASA_CIVIL.read_text(encoding="utf-8"))
    enquadramento = json.loads(ENQUADRAMENTO.read_text(encoding="utf-8"))
    municipios = registros(casa_civil, enquadramento)
    if not municipios:
        print("X nenhum município consta de nenhuma lista — não gravo arquivo vazio")
        return 1
    gravar_em(SAIDA, {"_governanca": GOVERNANCA,
                      "fontes": fontes_de(casa_civil, enquadramento),
                      "municipios": municipios}, compacto=True)      # §229
    print(f"{SAIDA.relative_to(RAIZ)} gravado · {len(municipios)} municípios em alguma lista "
          f"· {SAIDA.stat().st_size // 1024} kB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
