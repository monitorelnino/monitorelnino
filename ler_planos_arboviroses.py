#!/usr/bin/env python3
"""Leitura do texto integral dos diários onde `coletar_planos_arboviroses.py` localizou menção a plano.

Ordem da central, 23/10/2026 12:15 (E1: leitor de documento com hash para as menções localizadas).
Menção não é plano lido: cada achado já tem o diário preservado por hash em `evidencias/<hash>.txt`; esta
peça abre esse texto, acha as passagens que falam do plano e diz, em vocabulário fechado, O QUE a edição
contém. Leitura automática por regra, sempre com o trecho citado; nunca confirma plano nem promove pista.

LEITURA (vocabulário fechado, do mais forte ao mais fraco):
  texto do plano na edição        passagem sem ato antes dela e com ao menos 4 seções típicas de plano em
                                  até 8.000 caracteres depois (objetivos, níveis de alerta, vigilância...)
  ato ou ata que cita o plano     a passagem vem de aprova/institui/considerando/§, ou de ata e pauta
  citação sem ato identificado    há passagem, nenhum dos dois sinais acima
  passagem não reencontrada       o excerto da API não aparece no texto preservado
  texto integral indisponível     sem arquivo em evidencias/ (lacuna declarada, nunca "sem plano")
`texto do plano` é indício forte, não confirmação: quem confirma é o juiz, pela porta única.

TRAVAS (as mesmas de `coletar_planos_arboviroses.py`):
  1. ESTRUTURAL: escreve só `data/planos_arboviroses_leitura.json`; lê `planos_arboviroses.json` e evidencias/.
  2. DE CAMPO: nenhuma leitura produz pista, confirma documento nem muda estatuto do município.
  3. DE PROCESSO: sem rede; peso zero; nenhum juiz do índice lê o arquivo.

Uso: python3 ler_planos_arboviroses.py
     python3 ler_planos_arboviroses.py --autoteste        (offline, não escreve em data/)
"""
import re
import sys
import unicodedata

from coletores_base import EVID, ler, gravar, hoje_editorial, rodar_autoteste

ARQUIVO = "planos_arboviroses_leitura.json"
FONTE = "planos_arboviroses.json"
TEXTO, ATO, CITACAO, SEM_PASSAGEM, INDISPONIVEL = (
    "texto do plano na edição", "ato ou ata que cita o plano", "citação sem ato identificado",
    "passagem não reencontrada", "texto integral indisponível")
PASSAGEM = re.compile(r"plano[^.]{0,80}(conting|enfrentamento|resposta)[^.]{0,120}(dengue|arbovir|chikungunya|zika)"
                      r"|plano[^.]{0,40}(dengue|arbovir|chikungunya|zika)")
ATOS = re.compile(r"\b(aprova|institu|publica|estabelec|atualiz|considerando|convoc|dispoe|nos termos|conforme"
                  r"|de acordo|referente|previsto)|\b(art|artigo)\b|§")
ATAS = re.compile(r"\b(ata|pauta|reuniao|sessao|conselho|apresentacao do plano)\b")
COMENTARIO = re.compile(r"\b(sobre|diz|disse|comentou|discutiu|relatou) (o |um |este )?$")   # fala sobre o plano, não é o plano
SECOES = ("objetivo", r"niveis? de (alerta|ativacao)|cenarios? (de|epidemiol)", "vigilancia epidemiologica",
          r"manejo clinico|assistencia ao paciente|classificacao de risco", r"controle (vetorial|do vetor)",
          "comunicacao", r"introducao|apresentacao|justificativa", r"responsabilidades|atribuicoes|competencias",
          r"sumario|indice")
MINIMO_DE_SECOES = 4


def limpar(texto: str) -> tuple:
    """(original com espaços colapsados, versão sem acento e minúscula do MESMO comprimento)."""
    orig = re.sub(r"\s+", " ", texto)
    return orig, "".join(unicodedata.normalize("NFD", c)[0].lower() for c in orig)


def classificar(texto: str) -> tuple:
    """(leitura, trecho de até 300 caracteres, seções achadas) para o texto integral de uma edição. Pura."""
    orig, t = limpar(texto)
    achados = list(PASSAGEM.finditer(t))
    if not achados:
        return SEM_PASSAGEM, "", 0
    melhor = None
    for m in achados:
        antes = t[max(0, m.start() - 250):m.start()]
        mais = t[max(0, m.start() - 400):m.start()]
        if ATOS.search(antes) or ATAS.search(mais) or COMENTARIO.search(t[:m.start()]):
            continue
        n = sum(1 for s in SECOES if re.search(s, t[m.end():m.end() + 8000]))
        if melhor is None or n > melhor[0]:
            melhor = (n, m.start())
    if melhor and melhor[0] >= MINIMO_DE_SECOES:
        return TEXTO, orig[max(0, melhor[1] - 60):melhor[1] + 240], melhor[0]
    ini = achados[0].start()
    leitura = CITACAO if melhor else ATO
    return leitura, orig[max(0, ini - 60):ini + 240], melhor[0] if melhor else 0


def ler_achado(achado: dict, caminho_de=None) -> dict:
    """A leitura de um achado: lê o texto preservado pelo hash; sem arquivo, lacuna declarada."""
    caminho_de = caminho_de or (lambda h: EVID / f"{h}.txt")
    h = achado.get("hash_evidencia")
    base = {"hash_evidencia": h, "data_publicacao": achado.get("data_publicacao"), "url": achado.get("url"),
            "documento_oficial_confirmado": None, "promovivel": False}   # trava de campo
    p = caminho_de(h) if h else None
    if not p or not p.exists():
        return {**base, "leitura": INDISPONIVEL, "trecho": "", "secoes": 0}
    leitura, trecho, secoes = classificar(p.read_text(encoding="utf-8", errors="replace"))
    return {**base, "leitura": leitura, "trecho": trecho, "secoes": secoes}


def rodar() -> int:
    fonte = ler(FONTE, {}) or {}
    if not fonte.get("municipios"):   # fonte ausente é lacuna: o arquivo anterior fica, nada é gravado
        print(f"{FONTE} ausente ou vazio: leitura não feita, arquivo anterior mantido")
        return 0
    saida = {}
    for ibge, m in sorted((fonte.get("municipios") or {}).items()):
        if m.get("achados"):
            saida[ibge] = {"nome": m.get("nome"), "uf": m.get("uf"),
                           "leituras": [ler_achado(a) for a in m["achados"]]}
    contagem = {}
    for m in saida.values():
        for x in m["leituras"]:
            contagem[x["leitura"]] = contagem.get(x["leitura"], 0) + 1
    gravar(ARQUIVO, {
        "_governanca": "Leitura automática por regra do texto integral preservado dos diários (METODOLOGIA §121). "
                       "Peso zero. 'texto do plano na edição' é indício, não confirmação; o juiz confirma.",
        "execucao": {"data": hoje_editorial().isoformat(), "achados": sum(contagem.values()), "leituras": contagem},
        "municipios": saida})
    print(f"{len(saida)} município(s) com menção; leituras {contagem}")
    return 0


def autoteste() -> int:
    plano = ("DIARIO OFICIAL 1 PLANO MUNICIPAL DE CONTINGÊNCIA DAS ARBOVIROSES (dengue, chikungunya e zika) "
             "Sumário 1. Introdução 2. Objetivos 3. Vigilância epidemiológica 4. Níveis de alerta "
             "5. Controle vetorial 6. Comunicação 7. Responsabilidades")
    ato = "Art. 1º Fica aprovado o Plano de Contingência da Dengue do município. " + plano[60:]
    ata = "Pauta da reunião do conselho: apresentação do plano de contingência da dengue. Sumário Objetivos"
    solto = "Texto qualquer. O plano de contingência da dengue foi comentado por um vereador na tribuna."
    fala = "Sobre o plano de ação contra a dengue diz que é um documento. Objetivos. Vigilância epidemiológica. Comunicação. Introdução."
    vazio = "Edição sem relação alguma com o tema."
    leitura = lambda t: classificar(t)[0]
    fonte = open(__file__, encoding="utf-8").read().split("def autoteste")[0].split('"""', 2)[2]
    proibidos = ("estados.json", "saude_uf.json", "municipios.json", "indice.json", "monitor_saude.json",
                 "pistas", "urllib", "requests")
    escritas = [l for l in fonte.splitlines() if "gravar(" in l]
    sem_arquivo = ler_achado({"hash_evidencia": "x" * 64}, caminho_de=lambda h: EVID / "inexistente.txt")
    norm = limpar("AÇÃO  Ñandú\n")
    return rodar_autoteste({
        "título, seções e nenhum ato antes: texto do plano na edição": lambda: leitura(plano) == TEXTO,
        "'fica aprovado o plano' é ato, mesmo com seções depois": lambda: leitura(ato) == ATO,
        "ata e pauta citam o plano, não o contêm": lambda: leitura(ata) == ATO,
        "fala sobre o plano ('sobre o plano... diz que') não é o texto do plano": lambda: leitura(fala) != TEXTO,
        "menção solta sem ato nem seções: citação sem ato identificado": lambda: leitura(solto) == CITACAO,
        "edição sem a passagem: passagem não reencontrada": lambda: leitura(vazio) == SEM_PASSAGEM,
        "trecho tem no máximo 300 caracteres e cita o plano": lambda: 0 < len(classificar(plano)[1]) <= 300
                                                                    and "CONTING" in classificar(plano)[1].upper(),
        "trava de campo: leitura nasce não confirmada e não promovível":
            lambda: all(x["documento_oficial_confirmado"] is None and x["promovivel"] is False for x in (sem_arquivo, ler_achado({"hash_evidencia": None}))),
        "sem arquivo preservado: texto integral indisponível, nunca 'sem plano'":
            lambda: sem_arquivo["leitura"] == INDISPONIVEL and sem_arquivo["trecho"] == "",
        "normalização mantém o comprimento (o trecho vem do original)":
            lambda: len(norm[0]) == len(norm[1]) and norm[1] == "acao nandu ",
        "trava estrutural: o fonte não cita arquivo do banco, fila de pista nem rede":
            lambda: not any(p in fonte for p in proibidos),
        "trava estrutural: uma só escrita, no arquivo próprio": lambda: len(escritas) == 1 and "ARQUIVO" in escritas[0],
    })


def main() -> int:
    return autoteste() if "--autoteste" in sys.argv else rodar()


if __name__ == "__main__":
    sys.exit(main())
