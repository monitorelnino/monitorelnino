#!/usr/bin/env python3
"""
scripts/incorporar_respostas_lai.py — o que um órgão respondeu entra no site como o que é
==========================================================================================
Handover `HANDOVER_incorporar_respostas_LAI_03-10-2026.md`, item 1 (regra de incorporação) e item 4
(textos aprovados pela editoria em 03/10/2026).

A REGRA, QUE É DE PROVA E NÃO DE ESTILO
---------------------------------------
Resposta de órgão a pedido de acesso à informação chega em três formas, e cada uma tem um destino
diferente:

1. **documento anexado ou vinculado** → vai ao juiz, como qualquer documento oficial, e pontua no
   degrau da leitura. Não é este script: é `julgar_filas.py`.
2. **afirmação do órgão sem documento** ("o município X tem plano"; "não existe plano estadual";
   "em elaboração até outubro") → **não pontua**. Vira texto na ficha, com órgão e data, e uma pista
   de nível A para a busca dirigida. É isto que este script grava.
3. **decreto informado com número e data** → entra em `data/atos_resposta.json` como ato de resposta
   informado pelo órgão estadual, com a ressalva de que o documento ainda não foi localizado.

A distinção importa porque a afirmação de um órgão é prova de que o órgão afirma, não de que o
documento existe e diz o que se espera dele. O teto público de ausência continua sendo "não
localizamos até o corte" — e agora com uma linha a mais: quem afirmou, e quando.

ESTE SCRIPT NÃO INVENTA TEXTO. Os cinco modelos abaixo são literais aprovados pela editoria; o
script só preenche {uf}, {data}, {mes}, {n} e o título.

USO
  python3 scripts/incorporar_respostas_lai.py --autoteste
  python3 scripts/incorporar_respostas_lai.py --dry-run
  python3 scripts/incorporar_respostas_lai.py
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

# ---------------------------------------------------------------- os textos aprovados (item 4)
TEXTO_PLANO_INFORMADO = (
    "A Defesa Civil de {uf} informou ao MARÉ, em resposta a pedido de acesso à informação de "
    "{data}, que o município tem plano de contingência. O documento ainda não foi localizado em "
    "fonte pública e, por isso, não entra no índice.")
TEXTO_EM_ELABORACAO = (
    "A Defesa Civil de {uf} informou, em {data}, que o plano do município está em elaboração, com "
    "previsão para {mes}.")
TEXTO_ESTADO_SEM_PLANO = (
    "A Defesa Civil de {uf} informou ao MARÉ, em {data}, que não há plano estadual de contingência "
    "em vigor{preparacao}.")
TEXTO_DECRETO_INFORMADO = (
    "Decreto nº {n}, de {data_ato}, informado pela Defesa Civil de {uf} em {data}; documento "
    "{situacao}.")

PREPARACAO = "; um plano estadual está em preparação, sem data prevista"
NAO_LOCALIZADO = "ainda não localizado"

# ---------------------------------------------------------------- o que chegou (itens 0 e 2)
# MT, resposta de 23/09/2026 (COP). Seis municípios com plano, sem endereço eletrônico: o órgão
# respondeu que "o endereço deve ser pedido ao município".
MT_COM_PLANO = ("Tangará da Serra", "Campo Verde", "Nova Xavantina", "Itiquira",
                "São Pedro da Cipa", "Cáceres")
# Oito em elaboração, com mês previsto declarado pelo próprio órgão.
MT_EM_ELABORACAO = {"Primavera do Leste": "dezembro de 2026", "Água Boa": "outubro de 2026",
                    "Cláudia": "outubro de 2026", "Colíder": "novembro de 2026",
                    "Sorriso": "dezembro de 2026", "Juína": "outubro de 2026",
                    "Aripuanã": "novembro de 2026", "Alto Paraguai": "dezembro de 2026"}
# Três decretos com número e data, informados pelo estado.
MT_DECRETOS = (("Itaúba", "2.205", "20/07/2026"), ("Colniza", "2.234", "28/08/2026"),
               ("Várzea Grande", "2.233", "27/08/2026"))
DATA_MT = "23/09/2026"
# RN, resposta de 17/09/2026: sem plano estadual e sem lista consolidada de municípios.
DATA_RN = "17/09/2026"
# MT declarou que não existe plano estadual, e que um está em preparação, sem data.
ESTADOS_SEM_PLANO = (("MT", DATA_MT, True), ("RN", DATA_RN, False))

FONTE_LAI = ("Defesa Civil de {uf}, resposta a pedido de acesso à informação de {data} "
             "(pedido do MARÉ)")


# ---------------------------------------------------------------- funções puras
def nota_de_plano_informado(uf: str, data: str) -> str:
    return TEXTO_PLANO_INFORMADO.format(uf=uf, data=data)


def nota_de_elaboracao(uf: str, data: str, mes: str) -> str:
    return TEXTO_EM_ELABORACAO.format(uf=uf, data=data, mes=mes)


def nota_de_estado_sem_plano(uf: str, data: str, em_preparacao: bool) -> str:
    return TEXTO_ESTADO_SEM_PLANO.format(uf=uf, data=data,
                                         preparacao=PREPARACAO if em_preparacao else "")


def ato_informado(nome: str, uf: str, numero: str, data_ato: str, data_resposta: str,
                  coordenadas: dict = None) -> dict:
    """O evento de ato de resposta informado por órgão estadual, sem documento localizado.

    `decreto` carrega o texto aprovado inteiro, e não só o número, porque é nele que fica declarado
    que o documento não foi localizado — um número solto no cartão afirmaria mais do que se sabe.
    """
    evento = {
        "nome": nome, "uf": uf, "data": data_ato,
        "causa": "informado pelo órgão estadual em resposta a pedido de acesso à informação",
        "decreto": TEXTO_DECRETO_INFORMADO.format(n=numero, data_ato=data_ato, uf=uf,
                                                  data=data_resposta, situacao=NAO_LOCALIZADO),
        "danos": None,
        "fonte": FONTE_LAI.format(uf=uf, data=data_resposta),
        "url": None,
        # Lacuna declarada no campo, não no comentário: o portão de resposta exige proveniência, e
        # é esta marca que diz que a proveniência é a resposta do órgão, sem documento localizado.
        "documento_nao_localizado": True,
        "canal": "orgao_estadual",
    }
    if coordenadas:
        evento["lat"] = coordenadas.get("lat")
        evento["lon"] = coordenadas.get("lon")
    return evento


def ja_registrado(eventos: list, nome: str, uf: str, numero: str) -> bool:
    """Idempotência: o mesmo decreto do mesmo município não entra duas vezes. Função pura."""
    return any(e.get("nome") == nome and e.get("uf") == uf
               and numero in str(e.get("decreto") or "") for e in eventos)


def busca_dirigida(nome: str, uf: str, data: str, assunto: str) -> dict:
    """A tarefa de procurar o documento no sítio do município, por afirmação do estado.

    Não é uma pista da fila, e a razão é da própria fila: `coletores_base.validar_pista` exige
    `url_final` resolvida, porque pista sem endereço não pode ser conferida nem deduplicada. Uma
    afirmação de órgão não tem endereço — é exatamente o que falta nela. Então ela fica aqui, em
    `data/notas_lai.json`, como tarefa de busca dirigida, e entra na fila no dia em que a busca
    achar o documento, com o endereço dele. Função pura.
    """
    return {"municipio": nome, "uf": uf, "assunto": assunto, "nivel": "A",
            "origem": "resposta_lai", "fonte": FONTE_LAI.format(uf=uf, data=data),
            "url": None, "registrado_em": "2026-10-04"}


def coordenadas_de(nome: str, uf: str, referencia: list) -> dict:
    """Coordenadas do município na referência do IBGE, ou {} quando não há. Função pura."""
    for m in referencia:
        if m.get("nome") == nome and m.get("uf") == uf:
            return {"lat": m.get("lat"), "lon": m.get("lon")}
    return {}


# ---------------------------------------------------------------- escrita
def aplicar(dry_run: bool = False) -> int:
    from coletores_base import gravar, ler
    referencia = json.loads((RAIZ / "data" / "municipios_ibge_referencia.json")
                            .read_text(encoding="utf-8"))

    atos = ler("atos_resposta.json", {"eventos": []})
    novos = []
    for nome, numero, data_ato in MT_DECRETOS:
        if ja_registrado(atos["eventos"], nome, "MT", numero):
            continue
        novos.append(ato_informado(nome, "MT", numero, data_ato, DATA_MT,
                                   coordenadas_de(nome, "MT", referencia)))

    notas = {"gerado_em": "2026-10-04",
             "_governanca": ("Afirmações de órgão público recebidas por resposta a pedido de acesso "
                             "à informação. NÃO PONTUAM no índice: são prova de que o órgão afirma, "
                             "não de que o documento existe e diz o que se espera dele. Os textos "
                             "são literais aprovados pela editoria em 03/10/2026; ver "
                             "scripts/incorporar_respostas_lai.py."),
             "municipios": [], "estados": [], "buscas_dirigidas": []}
    for nome in MT_COM_PLANO:
        notas["municipios"].append({"nome": nome, "uf": "MT", "situacao": "plano_informado",
                                    "nota": nota_de_plano_informado("MT", DATA_MT)})
    for nome, mes in MT_EM_ELABORACAO.items():
        notas["municipios"].append({"nome": nome, "uf": "MT", "situacao": "em_elaboracao",
                                    "nota": nota_de_elaboracao("MT", DATA_MT, mes)})
    for nome in MT_COM_PLANO:
        notas["buscas_dirigidas"].append(
            busca_dirigida(nome, "MT", DATA_MT, "plano de contingência"))
    for uf, data, preparo in ESTADOS_SEM_PLANO:
        notas["estados"].append({"uf": uf, "situacao": "sem_plano_estadual",
                                 "nota": nota_de_estado_sem_plano(uf, data, preparo)})

    print(f"  atos de resposta informados: {len(novos)} novo(s)")
    print(f"  buscas dirigidas: {len(notas['buscas_dirigidas'])}")
    print(f"  notas de município: {len(notas['municipios'])} · de estado: {len(notas['estados'])}")
    if dry_run:
        print("(dry-run) nada gravado")
        return 0
    if novos:
        atos["eventos"].extend(novos)
        gravar("atos_resposta.json", atos)
    gravar("notas_lai.json", notas)

    # A nota do ESTADO tem onde aparecer: o detalhe da UF, na home. A do MUNICÍPIO não tem — a
    # ficha municipal saiu do site em 01/10, por decisão da editoria, e inventar uma superfície
    # nova para ela seria decidir o que é dela. Fica em notas_lai.json e na fila de busca dirigida.
    estados = ler("estados.json", {"ufs": []})
    for uf, data, preparo in ESTADOS_SEM_PLANO:
        for registro in estados.get("ufs", []):
            if registro.get("uf") == uf:
                registro["nota_lai"] = nota_de_estado_sem_plano(uf, data, preparo)
    gravar("estados.json", estados)
    return 0
    return 0


def _autoteste() -> int:
    falhas = []
    # O total era um literal e envelhecia calado: dizia cobrir mais casos do que
    # cobre, ou menos. Agora e contado.
    _casos_contados = []

    def ok(nome, cond):
        _casos_contados.append(nome)
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    t = nota_de_plano_informado("MT", "23/09/2026")
    ok("o texto do plano informado é o literal aprovado",
       t.startswith("A Defesa Civil de MT informou ao MARÉ") and "não entra no índice" in t)
    ok("a nota diz que o documento não foi localizado, nunca que não existe",
       "ainda não foi localizado" in t and "não existe" not in t)
    ok("a elaboração carrega o mês que o órgão declarou",
       "previsão para outubro de 2026" in nota_de_elaboracao("MT", "23/09/2026", "outubro de 2026"))
    ok("estado em preparação ganha a oração; o outro não",
       nota_de_estado_sem_plano("MT", "23/09/2026", True).endswith("sem data prevista.")
       and nota_de_estado_sem_plano("RN", "17/09/2026", False).endswith("em vigor."))

    ev = ato_informado("Itaúba", "MT", "2.205", "20/07/2026", "23/09/2026",
                       {"lat": -11.0, "lon": -55.3})
    ok("o ato informado declara que o documento não foi localizado",
       "ainda não localizado" in ev["decreto"])
    ok("a fonte do ato é a resposta ao pedido, com data",
       "resposta a pedido de acesso à informação de 23/09/2026" in ev["fonte"])
    ok("o ato não inventa URL nem danos", ev["url"] is None and ev["danos"] is None)
    ok("a ausência do documento fica declarada no campo", ev["documento_nao_localizado"] is True)
    ok("as coordenadas entram quando existem", ev["lat"] == -11.0)
    ok("sem coordenadas o evento não ganha campo vazio",
       "lat" not in ato_informado("X", "MT", "1", "01/01/2026", "23/09/2026"))

    base = [ev]
    ok("o mesmo decreto não entra duas vezes", ja_registrado(base, "Itaúba", "MT", "2.205"))
    ok("decreto diferente do mesmo município entra",
       not ja_registrado(base, "Itaúba", "MT", "9.999"))
    ok("mesmo número em outro município entra",
       not ja_registrado(base, "Colniza", "MT", "2.205"))

    p = busca_dirigida("Cáceres", "MT", "23/09/2026", "plano de contingência")
    ok("a busca dirigida é de nível A, porque a origem é o próprio estado", p["nivel"] == "A")
    ok("a busca dirigida não finge ter documento", p["url"] is None)
    from coletores_base import validar_pista
    ok("ela NÃO passa pela porta da fila, e é por isso que não é pista",
       validar_pista(dict(p, tipo="plano", excerto=p["fonte"]))[0] is False)

    ref = [{"nome": "Colniza", "uf": "MT", "lat": -9.3, "lon": -59.2}]
    ok("as coordenadas vêm da referência do IBGE",
       coordenadas_de("Colniza", "MT", ref)["lat"] == -9.3)
    ok("município fora da referência não gera coordenada adivinhada",
       coordenadas_de("Inexistente", "MT", ref) == {})
    ok("UF errada não casa por nome", coordenadas_de("Colniza", "RO", ref) == {})

    ok("são 6 com plano, 8 em elaboração e 3 decretos, como a resposta diz",
       len(MT_COM_PLANO) == 6 and len(MT_EM_ELABORACAO) == 8 and len(MT_DECRETOS) == 3)

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "aplicar", "main"):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não escrevem",
       not ({"gravar", "gravar_pista", "write_text"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv[1:]:
        return _autoteste()
    return aplicar(dry_run="--dry-run" in sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
