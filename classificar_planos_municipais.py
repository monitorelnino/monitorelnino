#!/usr/bin/env python3
"""
classificar_planos_municipais.py
================================
Lê o TEXTO PRESERVADO de cada plano municipal e PROPÕE a classificação na escada do §202
(`plano_novo` · `plano_readaptado` · `plano_recorrente`), com a citação que justifica cada proposta.

O QUE ELE NÃO FAZ, e é o mais importante: não altera `data/municipios.json`, não recalcula o
índice, não decide nada. Ele escreve `data/escada_municipal_revisar.json`, arquivo de revisão para
leitura humana — a promoção é R7, como toda classificação neste projeto.

A RÉGUA, herdada de §30 e levada ao município pelo §202:
  · `plano_novo`        instrumento criado PARA o ciclo / dedicado ao El Niño
  · `plano_readaptado`  instrumento preexistente reativado ou readaptado para o ciclo, por ato datado
  · `plano_recorrente`  rotina sazonal que roda todo ano, com ou sem El Niño

REGRA DE ABSTENÇÃO (§6 da governança editorial): sinal ausente, ou sinais de classes diferentes com
força parecida, devolvem `indeterminado` — que mantém o registro onde está, valendo 1,00. O robô não
classifica no escuro, e "não sei" nunca vira nota. Cada proposta carrega o trecho que a sustenta,
para que a leitura humana confira a evidência e não a conclusão.

LIMITE CONHECIDO: o sinal vem do texto extraído do PDF, que é cópia legível — não é o juízo. Um
documento cujo título diz "verão" e cujo corpo institui resposta ao El Niño existe, e é por isso que
a proposta vem com citação e com a classe concorrente declarada quando há empate.

Uso:
  python3 classificar_planos_municipais.py            # escreve o arquivo de revisão
  python3 classificar_planos_municipais.py --autoteste
"""
import json
import pathlib
import re
import sys
import unicodedata
from coletores_base import gravar_em  # noqa: E402  (§229: escrita atômica de data/)

RAIZ = pathlib.Path(__file__).parent
SAIDA = "escada_municipal_revisar.json"

# Cada sinal é um par (expressão, peso). Os pesos são pequenos e inteiros de propósito: a soma
# decide, e a diferença entre a melhor e a segunda classe é o que separa proposta de abstenção.
SINAIS = {
    "plano_novo": [
        # §203: TODO sinal leva limite de palavra dos DOIS lados. A primeira versão escreveu `enos\b`
        # sem o limite à esquerda, e ele casou dentro de "mENOS favorecida" — dando três pontos de
        # "dedicado ao El Niño" a um parágrafo sobre ocupação de moradia. Sigla curta sem âncora
        # pega pedaço de palavra comum, e o erro só apareceu porque a proposta é obrigada a citar.
        (r"\bel\s*ni[nñ]o\b", 3),
        (r"\benos\b|\boscila[çc][ãa]o sul\b", 3),
        # §203: o ANO do ciclo sozinho é ambíguo — aparece tanto em plano criado para ele quanto em
        # plano atualizado para ele. Quem distingue é o VERBO, então o ano vale pouco e "El Niño" ou
        # "ENOS" valem muito. Com peso 2, "atualização ... para 2026/2027" empatava consigo mesma.
        (r"2026\s*[/-]\s*2027", 1),
        (r"estiagem (?:severa|extrema|prolongada)", 1),
    ],
    # §203: readaptação só conta quando o documento diz que foi refeito PARA ESTE CICLO. "2ª edição"
    # sozinho indica versionamento, não readaptação — e "edição 2025" é anterior ao ciclo. Por isso
    # os sinais de versão valem 1 (pista), e só somam o bastante quando acompanhados de referência
    # ao ciclo, que vale 2. Verbo de readaptação com data de 2026 vale 2 sozinho.
    "plano_readaptado": [
        (r"(?:atualiza[çc][ãa]o|revis[ãa]o|atualizado|revisado)[^.]{0,60}(?:2026|2027)", 3),
        (r"\b[2-9]ª?\s*(?:atualiza[çc][ãa]o|edi[çc][ãa]o|vers[ãa]o)\b", 1),
        (r"substitui o plano|em substitui[çc][ãa]o ao", 2),
        (r"(?:atualiza[çc][ãa]o|revis[ãa]o)[^.]{0,40}el\s*ni[nñ]o", 3),
    ],
    "plano_recorrente": [
        (r"opera[çc][ãa]o (?:ver[ãa]o|chuva|chuvas|inverno)", 3),
        (r"plano (?:preventivo )?de (?:chuvas de )?ver[ãa]o", 3),
        (r"per[íi]odo chuvoso|quadra chuvosa", 2),
        (r"\banualmente\b|\btodos os anos\b|\ba cada ano\b", 2),
        (r"ver[ãa]o 20\d\d\s*[/-]\s*20\d\d", 2),
    ],
}
MARGEM = 2   # a melhor classe precisa superar a segunda por isto; empate técnico = indeterminado


def normalizar(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t)


# ZONA DE IDENTIDADE (§203, corrigido na primeira rodada real). A primeira versão procurava sinal no
# TEXTO INTEIRO do documento, e a citação obrigatória denunciou o preço: Vitória virou "recorrente"
# por uma frase de corpo sobre óbitos "computados todos os anos, no período chuvoso", e três PLANCONs
# capixabas viraram "readaptado" por "manter registro ATUALIZADO sobre danos humanos" — uma instrução
# DENTRO do plano, não prova de que o plano foi atualizado. O tipo de um instrumento se declara no
# título e na abertura, não numa linha da página 40. É a régua do §182 (texto declarativo) e a do
# §180 (o ato tem de se apresentar como tal), aplicadas aqui.
IDENTIDADE_CARACTERES = 1200


def zona_de_identidade(texto: str, documento: str = "") -> str:
    """Abertura do DOCUMENTO. O `documento` do banco é descrição NOSSA e não entra (§203).

    Segundo defeito da mesma rodada: a primeira correção incluiu aqui o campo `documento` do banco, e
    71 de 82 planos viraram "readaptado" porque esse campo diz "PLANCON edição 2025" — rótulo que o
    Monitor escreveu, não palavra do documento. Classificar a própria descrição é circular: o robô
    concordava consigo mesmo e chamava isso de evidência. O parâmetro continua na assinatura porque
    o arquivo de revisão o exibe como contexto para o humano, mas ele NÃO é pontuado.
    """
    corpo = re.sub(r"=== p[áa]gina \d+ ===", " ", texto or "")
    return corpo[:IDENTIDADE_CARACTERES]


def classificar(texto: str, documento: str = "") -> dict:
    """Devolve {classe, pontos, concorrente, citacao, motivo}. Função pura — o autoteste vive dela.

    Só olha a ZONA DE IDENTIDADE, que é a abertura do PRÓPRIO documento — o rótulo que o Monitor
    escreveu no banco fica de fora, porque pontuar a própria descrição é circular (§203)."""
    plano = normalizar(zona_de_identidade(texto, documento))
    pontos, citacoes = {}, {}
    for classe, regras in SINAIS.items():
        total, melhor_peso = 0, 0
        for expressao, peso in regras:
            m = re.search(normalizar(expressao) if "\\" not in expressao else expressao, plano)
            if m:
                total += peso
                # §203: a citação mostra o sinal MAIS FORTE, não o primeiro que casou. A primeira
                # versão guardava o primeiro, e Afonso Cláudio saiu proposto como "novo" exibindo um
                # trecho sobre ocupação do solo — enquanto o ponto vinha de outro sinal. Citação que
                # não corresponde ao que pesou é pior do que citação nenhuma: ela faz o revisor
                # conferir a frase errada e concordar com uma conclusão que ninguém verificou.
                if peso > melhor_peso:
                    melhor_peso = peso
                    citacoes[classe] = plano[max(0, m.start() - 60):m.start() + 90].strip()
        pontos[classe] = total
    ordem = sorted(pontos.items(), key=lambda x: -x[1])
    melhor, p1 = ordem[0]
    segundo, p2 = ordem[1]
    if p1 == 0:
        return {"classe": "indeterminado", "pontos": pontos, "concorrente": None, "citacao": None,
                "motivo": "nenhum sinal das três classes no texto preservado"}
    if p1 - p2 < MARGEM:
        return {"classe": "indeterminado", "pontos": pontos, "concorrente": segundo,
                "citacao": citacoes.get(melhor),
                "motivo": f"empate técnico entre {melhor} ({p1}) e {segundo} ({p2}) — "
                          f"a margem exigida é {MARGEM}; leitura humana decide"}
    return {"classe": melhor, "pontos": pontos, "concorrente": segundo if p2 else None,
            "citacao": citacoes.get(melhor),
            "motivo": f"{melhor} por {p1} contra {p2} da segunda classe"}


def ler_banco():
    mun = json.loads((RAIZ / "data" / "municipios.json").read_text(encoding="utf-8"))
    ev = json.loads((RAIZ / "data" / "evidencias.json").read_text(encoding="utf-8"))["itens"]
    por_url = {it.get("url"): it for it in ev.values() if it.get("url")}
    return mun, por_url


def gerar() -> int:
    mun, por_url = ler_banco()
    propostas, sem_texto, indet = [], 0, 0
    for m in mun:
        if m.get("categoria") not in ("plano", "plano_antigo"):
            continue
        it = por_url.get(m.get("url") or "")
        arq = (it or {}).get("texto_arquivo")
        if not arq or not (RAIZ / arq).exists():
            sem_texto += 1
            continue
        texto = (RAIZ / arq).read_text(encoding="utf-8")
        r = classificar(texto, str(m.get("documento") or ""))
        if r["classe"] == "indeterminado":
            indet += 1
        propostas.append({
            "nome": m["nome"], "uf": m["uf"], "categoria_hoje": m["categoria"],
            "documento": str(m.get("documento") or "")[:120],
            "proposta": r["classe"], "motivo": r["motivo"], "pontos": r["pontos"],
            "classe_concorrente": r["concorrente"],
            "citacao_que_sustenta": (r["citacao"] or "")[:220] or None,
            "evidencia": arq, "url": m.get("url"),
        })
    doc = {
        "_governanca": (
            "ARQUIVO DE REVISÃO (§203) — proposta de classificação dos planos municipais na escada do "
            "§202, feita a partir do TEXTO PRESERVADO de cada documento. NADA AQUI ESTÁ APLICADO: "
            "promoção é R7. Cada proposta traz o trecho que a sustenta, para a leitura humana "
            "conferir a EVIDÊNCIA e não a conclusão. `indeterminado` mantém o registro onde está, "
            "valendo 1,00 — o robô não classifica no escuro, e 'não sei' nunca vira nota."),
        "regua": "plano_novo 1,00 · plano_readaptado 0,65 · plano_recorrente 0,45 (§202)",
        "margem_exigida": MARGEM,
        "resumo": {"com_texto": len(propostas), "sem_texto_preservado": sem_texto,
                   "indeterminados": indet, "propostos": len(propostas) - indet},
        "propostas": sorted(propostas, key=lambda x: (x["proposta"], x["uf"], x["nome"])),
    }
    destino = RAIZ / "data" / SAIDA
    gravar_em(destino, doc)   # §229
    print(f"{len(propostas)} plano(s) com texto lido · {len(propostas) - indet} proposta(s) · "
          f"{indet} indeterminado(s) · {sem_texto} sem texto preservado")
    print(f"→ data/{SAIDA} (revisão humana; nada aplicado)")
    return 0


def autoteste() -> int:
    casos = [
        ("dedicado ao ciclo", "Plano de Contingência para o El Niño 2026/2027 do município", "plano_novo"),
        ("rotina sazonal", "Operação Verão 2025/2026 — plano preventivo de chuvas de verão", "plano_recorrente"),
        # §203: readaptação exige referência AO CICLO. Versão sem ciclo é versionamento, não resposta.
        ("readaptação sem ciclo é versionamento", "Atualização e revisão do plano, 2ª edição", "indeterminado"),
        ("readaptação para o ciclo", "Atualização do plano de contingência para 2026/2027", "plano_readaptado"),
        ("texto sem sinal", "Documento administrativo sobre pessoal e contratos", "indeterminado"),
        ("vazio", "", "indeterminado"),
    ]
    falhou = False
    for rotulo, texto, esperado in casos:
        r = classificar(texto)
        ok = r["classe"] == esperado
        print(f"  {'✓' if ok else '✗'} {rotulo}: {r['classe']}")
        falhou = falhou or not ok

    # o caso que a régua existe para acertar: sinais das DUAS classes, sem folga → abstém
    empate = classificar("Operação Verão 2026, atualizada para o período de El Niño")
    ok = empate["classe"] == "indeterminado" and empate["concorrente"] is not None
    print(f"  {'✓' if ok else '✗'} sinais de classes diferentes sem folga → indeterminado, com concorrente nomeado")
    falhou = falhou or not ok

    # §203: o defeito da primeira rodada — sinal em prosa de corpo não classifica
    corpo_longe = ("Plano municipal de proteção e defesa civil. " + ("texto. " * 200) +
                   "os obitos sao computados todos os anos, no periodo chuvoso")
    longe = classificar(corpo_longe)
    ok = longe["classe"] == "indeterminado"
    print(f"  {'✓' if ok else '✗'} sinal em prosa de corpo, longe da abertura, não classifica")
    falhou = falhou or not ok

    # e o mesmo sinal NO TÍTULO classifica
    # §203, segundo defeito: o campo documento é descrição NOSSA e não pontua
    nosso = classificar("conteúdo neutro do documento", documento="PLANCON edição 2025 (repositório estadual)")
    ok = nosso["classe"] == "indeterminado"
    print(f"  {'✓' if ok else '✗'} rótulo do banco não classifica (não se pontua a própria descrição)")
    falhou = falhou or not ok

    # §203: sigla curta sem limite de palavra pegava pedaço de palavra comum
    falso = classificar("leva grande parte da populacao menos favorecida a ocupar areas improprias")
    ok = falso["classe"] == "indeterminado"
    print(f"  {'✓' if ok else '✗'} 'menos' não casa com a sigla ENOS")
    falhou = falhou or not ok

    # abstenção nunca inventa citação
    vazio = classificar("")
    ok = vazio["citacao"] is None
    print(f"  {'✓' if ok else '✗'} abstenção não inventa citação")
    falhou = falhou or not ok

    print("✗ AUTOTESTE: falhou" if falhou else "✓ AUTOTESTE OK")
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else gerar())
