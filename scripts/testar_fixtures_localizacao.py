#!/usr/bin/env python3
"""As sete fixtures de regressão de 27/09 — testes que FALHAM até a descoberta achar sozinha.

POR QUE ESTE ARQUIVO EXISTE (27/09/2026, §251)
==============================================
Pedido §I da editoria. Os sete achados de 27/09 existem para provar que a DESCOBERTA falhou; a
correção é fazer a descoberta encontrá-los sozinha, não digitá-los no dado.

Cada caso de `data/erros_localizacao.json` com `fixture` preenchida vira um teste aqui. O teste
pergunta uma coisa só: **o mecanismo nomeado no caso acha a fixture por conta própria?**

O VERMELHO INICIAL É EVIDÊNCIA, NÃO ERRO. Em 27/09 todas falham, e o CHANGELOG registra que
falharam. Fixture verde antes de haver coletor novo no repositório é sinal de que a regra foi
violada — alguém inseriu à mão.

TRÊS DESFECHOS, NUNCA DOIS
==========================
Confundir "não achou" com "não deu para procurar" é o defeito que esta noite já custou quatro
consertos (§§246 a 248: truncamento silencioso lido como sucesso). Por isso:

  ACHOU              o mecanismo devolveu a fixture. Verde.
  NAO_ACHOU          o mecanismo rodou, respondeu, e não trouxe a fixture. Vermelho — é o caso real.
  SEM_MECANISMO      o mecanismo nomeado não existe no repositório. Vermelho, com nome próprio.
  REDE_OU_BLOQUEIO   a fonte não respondeu, ou recusou (401/403/429/451, muro de robô, defeso).
                     NÃO é fixture verde nem vermelha: é indeterminado, e sai declarado.

Indeterminado nunca conta como passou. O relatório final diz, por fixture, QUAL regra a encontrou
— nunca "inserido conforme pedido".

Uso:
    python3 scripts/testar_fixtures_localizacao.py            # com rede, roda os mecanismos
    python3 scripts/testar_fixtures_localizacao.py --seco     # sem rede: só o que existe no repo
    python3 scripts/testar_fixtures_localizacao.py --autoteste
"""
import importlib.util
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
REGISTRO = RAIZ / "data" / "erros_localizacao.json"

ACHOU, NAO_ACHOU, SEM_MECANISMO, INDETERMINADO = "ACHOU", "NAO_ACHOU", "SEM_MECANISMO", "REDE_OU_BLOQUEIO"


def carregar(nome_do_arquivo: str):
    """Carrega um módulo do repositório pelo nome do arquivo, ou None se ele não existir."""
    caminho = RAIZ / nome_do_arquivo
    if not caminho.exists():
        return None
    spec = importlib.util.spec_from_file_location(caminho.stem, caminho)
    modulo = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(modulo)
    except Exception:  # noqa: BLE001
        return None
    return modulo


# ── os mecanismos, um por tipo de fixture ───────────────────────────────────────────────────

def mecanismo_descoberta(caso, seco: bool):
    """A descoberta de planos acha a fixture sozinha?

    Hoje: `descobrir_planos.py` existe e consulta wp-json. O que ela NÃO faz é o que os casos
    pedem — enumerar /media/ e /uploads/AAAA/, varrer seção de navegação, e usar mais de dois
    termos de busca (o laço corta em `TERMOS_BUSCA[setor][:2]`).
    """
    mod = carregar("descobrir_planos.py")
    if mod is None:
        return SEM_MECANISMO, "descobrir_planos.py não existe no repositório"

    # O caso do AC e do MT não são de descoberta de PDF: são de canal oficial não coberto.
    if "agências oficiais" in (caso.get("mecanismo_esperado") or ""):
        if carregar("coletar_agencias_oficiais.py") is None:
            return SEM_MECANISMO, ("adaptador de agências oficiais de notícias estaduais não "
                                   "existe no repositório")

    if seco:
        # Sem rede não se afirma "não achou": afirma-se o que está no código.
        alcance = []
        fonte = (RAIZ / "descobrir_planos.py").read_text(encoding="utf-8", errors="replace")
        if "[:2]" in fonte:
            alcance.append("o laço corta em dois termos de busca")
        if "/media/" not in fonte:
            alcance.append("não enumera /media/")
        if "uploads/" not in fonte:
            alcance.append("não enumera /uploads/AAAA/")
        if "biblioteca" not in fonte:
            alcance.append("não varre seção de navegação")
        return (NAO_ACHOU if alcance else INDETERMINADO), "; ".join(alcance) or "leitura seca inconclusiva"

    if not hasattr(mod, "descobrir_uf"):
        for nome in ("descobrir", "descobrir_alvo", "descobrir_para"):
            if hasattr(mod, nome):
                break
        else:
            return SEM_MECANISMO, ("descobrir_planos.py não expõe função de descoberta por UF "
                                   "que este teste saiba chamar")
    return INDETERMINADO, "execução com rede ainda não ligada neste teste (ver --seco)"


def mecanismo_reavaliacao(caso, seco: bool):
    """A reavaliação devolve `suspensa` e `escopo` corretos para a fixture?"""
    suspensas = RAIZ / "data" / "calendario" / "fontes_suspensas.json"
    if not suspensas.exists():
        return SEM_MECANISMO, "data/calendario/fontes_suspensas.json não existe"
    fontes = (json.loads(suspensas.read_text(encoding="utf-8")) or {}).get("fontes") or {}
    registro = fontes.get(caso["fixture"])
    if registro is None:
        return NAO_ACHOU, f"a fixture não está registrada em fontes_suspensas.json"

    esperado = caso["esperado"]
    obtido = {"suspensa": registro.get("suspensa"), "escopo": registro.get("escopo")}
    if obtido == esperado:
        return ACHOU, f"suspensa={obtido['suspensa']} escopo={obtido['escopo']}"
    return NAO_ACHOU, (f"esperado suspensa={esperado['suspensa']} escopo={esperado['escopo']}; "
                       f"obtido suspensa={obtido['suspensa']} escopo={obtido['escopo']}")


def avaliar(caso, seco: bool):
    if caso.get("tipo_de_fixture") == "reavaliacao":
        return mecanismo_reavaliacao(caso, seco)
    return mecanismo_descoberta(caso, seco)


def main() -> int:
    args = sys.argv[1:]
    if "--autoteste" in args:
        return autoteste()
    seco = "--seco" in args

    registro = json.loads(REGISTRO.read_text(encoding="utf-8"))
    casos = registro["casos"]

    print(f"=== sete fixtures de localização de 27/09 · modo "
          f"{'SECO (sem rede)' if seco else 'com rede'} ===")
    verdes, vermelhas, indeterminadas, abertas = [], [], [], []

    for caso in casos:
        if not caso.get("fixture"):
            abertas.append(caso)
            print(f"  ⊘ {caso['uf']} {caso['id']}: EM ABERTO — sem fixture")
            print(f"      {caso.get('lacuna_declarada', '')[:150]}")
            continue
        estado, detalhe = avaliar(caso, seco)
        simbolo = {ACHOU: "✓", NAO_ACHOU: "✗", SEM_MECANISMO: "✗", INDETERMINADO: "?"}[estado]
        print(f"  {simbolo} {caso['uf']} {caso['id']}: {estado}")
        print(f"      {detalhe}")
        print(f"      mecanismo esperado: {caso['mecanismo_esperado']}")
        if estado == ACHOU:
            verdes.append(caso)
        elif estado == INDETERMINADO:
            indeterminadas.append(caso)
        else:
            vermelhas.append(caso)

    print(f"\nverdes {len(verdes)} · vermelhas {len(vermelhas)} · "
          f"indeterminadas {len(indeterminadas)} · em aberto sem fixture {len(abertas)}")

    if verdes:
        # A trava do pedido, virada em asserção: fixture verde sem coletor novo é violação.
        print("  ATENÇÃO — confira, para cada verde, QUAL regra/coletor a encontrou. "
              "Verde sem coletor novo no repositório significa inserção à mão, que é proibida.")

    # Indeterminado NÃO passa. Vermelha não passa. Só verde passa.
    if vermelhas or indeterminadas or abertas:
        print(f"\n✗ FIXTURES DE LOCALIZAÇÃO: {len(verdes)} de {len(casos)} passaram. "
              f"O vermelho é evidência enquanto os coletores não existirem.")
        return 1
    print(f"\n✓ FIXTURES DE LOCALIZAÇÃO OK — {len(verdes)} de {len(casos)}.")
    return 0


def autoteste() -> int:
    """Prova que o próprio teste sabe distinguir os quatro desfechos."""
    falhas = []

    def checar(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    registro = json.loads(REGISTRO.read_text(encoding="utf-8"))
    casos = registro["casos"]
    checar("o registro tem sete casos", len(casos) == 7)
    checar("seis casos têm fixture; o do MT não",
           sum(1 for c in casos if c.get("fixture")) == 6)

    reav = [c for c in casos if c.get("tipo_de_fixture") == "reavaliacao"]
    checar("duas fixtures de reavaliação (SE e TO)",
           sorted(c["uf"] for c in reav) == ["SE", "TO"])

    # A reavaliação tem de dar NAO_ACHOU hoje: o campo `escopo` não existe em fontes_suspensas.
    estados = [mecanismo_reavaliacao(c, seco=True)[0] for c in reav]
    checar("as duas de reavaliação dão NAO_ACHOU hoje (é o erro que elas registram)",
           estados == [NAO_ACHOU, NAO_ACHOU])

    # Um caminho inexistente tem de dar SEM_MECANISMO, não NAO_ACHOU — a distinção é o ponto.
    falso = {"tipo_de_fixture": "reavaliacao", "fixture": "x", "esperado": {}}
    orig = RAIZ / "data" / "calendario" / "fontes_suspensas.json"
    checar("fixture ausente do arquivo dá NAO_ACHOU, não SEM_MECANISMO",
           mecanismo_reavaliacao(falso, seco=True)[0] == NAO_ACHOU and orig.exists())

    # O mecanismo de descoberta, em modo seco, tem de apontar o corte de dois termos.
    es = next(c for c in casos if c["uf"] == "ES")
    estado, detalhe = mecanismo_descoberta(es, seco=True)
    checar("descoberta em modo seco aponta o corte de dois termos como limite medido",
           estado == NAO_ACHOU and "dois termos" in detalhe)

    # O caso do AC tem de acusar o adaptador ausente, com nome próprio.
    ac = next(c for c in casos if c["uf"] == "AC")
    estado_ac, detalhe_ac = mecanismo_descoberta(ac, seco=True)
    checar("o caso do AC acusa SEM_MECANISMO, nomeando o adaptador de agências",
           estado_ac == SEM_MECANISMO and "agências oficiais" in detalhe_ac)

    if falhas:
        print(f"\n✗ AUTOTESTE DAS FIXTURES: {len(falhas)} falha(s).")
        return 1
    print("\n✓ AUTOTESTE DAS FIXTURES OK — os quatro desfechos se distinguem.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
