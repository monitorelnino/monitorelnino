#!/usr/bin/env python3
"""
julgar_saude.py — o juiz sobre a fila de saúde estadual
========================================================
Item 3 do handover "fechar os 27 e trocar para a v0.4" (editoria, 01/10/2026).

`julgar_filas.py` roda o juiz sobre as filas do MARÉ Legal e escreve em `municipios.json`. A fila
de saúde é outra (`pistas_imprensa_saude.json`), a pergunta é outra (plano ESTADUAL de saúde, e
agora também a COORDENAÇÃO em saúde) e o destino é outro (`saude_uf.json`). Juntar as duas num
script só exigiria um `if` em cada etapa; separadas, cada uma diz o que julga.

O QUE ELE FAZ
-------------
Para cada pista de domínio oficial: baixa o documento, extrai o texto (PDF ou HTML), e roda
`juiz.julgar(..., eh_estadual=True)` — as mesmas sete etapas do Legal, porque a pergunta "isto é um
ato oficial, identificado, citável, do Executivo, com objeto ex-ante?" não muda por ser saúde.

O que ele acrescenta é UMA classificação, e ela é regra lida no texto, não inferência: o ato que
**institui sala de situação ou centro de operações de emergência** é COORDENAÇÃO; o ato que
institui ou aprova **plano** é INSTRUMENTO. Quando o mesmo ato faz as duas coisas — e a 0195/2026 de
MT faz —, ele conta nas duas, porque são dois componentes e o documento sustenta os dois.

O QUE ELE NÃO FAZ
-----------------
- Não promove por título, notícia ou resumo: julga o texto do documento primário, preservado com
  hash. Pista de domínio que não é oficial nem é baixada — fica na fila para a triagem humana.
- Não decide escala nem peso. O degrau da v0.4 sai de `gerar_monitor_saude.instrumento_v04` e da
  classificação de coordenação abaixo, que são regra versionada.
- Não marca "não localizado". Essa decisão é do item 4 do handover e exige bateria completa por UF:
  ela vive em `marcar_nao_localizado.py`, não aqui.
- Não apaga pista: a recusa fica na fila com o motivo à vista.

USO
  python3 julgar_saude.py --autoteste
  python3 julgar_saude.py --relatorio          # julga e conta, não escreve
  python3 julgar_saude.py --aplicar            # julga e escreve em saude_uf.json
  python3 julgar_saude.py --relatorio --uf MA
"""
import io
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import juiz
from coletores_base import buscar, gravar, hoje_editorial, ler, preservar_evidencia, rodar_autoteste

FILA = "pistas_imprensa_saude.json"
ALVO = "saude_uf.json"

# A classificação do que o ato INSTITUI. Literal, lida no texto do próprio ato.
RE_COORDENACAO = re.compile(
    r"(sala\s+de\s+situa[çc][ãa]o|centro\s+de\s+opera[çc][õo]es\s+de\s+emerg[êe]ncia|\bCOES?\b"
    r"|gabinete\s+de\s+crise|comit[êe]\s+(?:gestor|de\s+crise|de\s+enfrentamento))", re.I)
RE_PLANO = re.compile(r"(plano\s+(?:estadual\s+)?(?:de\s+)?(?:conting[êe]ncia|prepara[çc][ãa]o|"
                      r"a[çc][ãa]o|enfrentamento|resposta))", re.I)
# Menção NOMINAL ao ciclo: é o que separa "criado para o ciclo" de "permanente".
RE_CICLO = re.compile(r"El\s*Ni[ñn]o", re.I)
RE_REATIVA = re.compile(r"(reativa|reinstitui|prorroga|renova|reconduz)", re.I)


def texto_do_documento(corpo: bytes, url: str) -> str:
    """O texto corrido do documento, de PDF ou de HTML. Função pura (não busca nada).

    PDF sem texto extraível devolve string vazia, e o juiz reprova na etapa 0 — que é o certo: um
    PDF digitalizado sem OCR não é documento lido, e tratar vazio como "sem objeto ex-ante" seria
    reprovar o ato pelo defeito do arquivo. O motivo fica visível na fila."""
    if (url or "").lower().split("?")[0].endswith(".pdf") or corpo[:5] == b"%PDF-":
        try:
            from pdfminer.high_level import extract_text
            return re.sub(r"\s+", " ", extract_text(io.BytesIO(corpo)) or "")
        except Exception:  # noqa: BLE001
            return ""
    bruto = corpo.decode("utf-8", "replace") if isinstance(corpo, bytes) else str(corpo)
    bruto = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", bruto, flags=re.S | re.I)
    import html as _html
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", bruto)))


def o_que_institui(texto: str) -> set:
    """{'coordenacao'} | {'instrumento'} | os dois | conjunto vazio. Função pura.

    Um ato pode instituir as duas coisas, e nesse caso conta nas duas: são dois componentes do
    índice, e o mesmo documento sustenta os dois. A Portaria 0195/2026 de MT é exatamente esse
    caso — institui o processo de elaboração do plano E a sala de situação permanente."""
    achados = set()
    if RE_COORDENACAO.search(texto or ""):
        achados.add("coordenacao")
    if RE_PLANO.search(texto or ""):
        achados.add("instrumento")
    return achados


def degrau_coordenacao(texto: str, data: str) -> tuple:
    """(degrau, motivo) na escala aprovada da v0.4. Função pura.

    CRIADO_CICLO exige que o ato NOMEIE o ciclo e seja de 2026 — as duas coisas: um ato de 2026 que
    não nomeia o ciclo é estrutura permanente que por acaso é recente, e afirmar criação para o
    ciclo seria ler intenção no calendário. REATIVADO_CICLO exige o verbo de reativação mais a
    menção ao ciclo. Sem menção, PERMANENTE — a estrutura existe, e é o que se pode afirmar."""
    t = texto or ""
    cita_ciclo = bool(RE_CICLO.search(t))
    ano = None
    m = re.search(r"/(\d{4})$", (data or "").strip())
    if m:
        ano = int(m.group(1))
    if cita_ciclo and ano == 2026 and RE_REATIVA.search(t):
        return "REATIVADO_CICLO", "ato de 2026 que reativa estrutura e nomeia o ciclo"
    if cita_ciclo and ano == 2026:
        return "CRIADO_CICLO", "ato de 2026 que institui a estrutura e nomeia o ciclo"
    if cita_ciclo:
        return "REATIVADO_CICLO", "ato que nomeia o ciclo, sem data de 2026 confirmada"
    return "PERMANENTE", "ato institui a estrutura e não nomeia o ciclo"


def status_instrumento(categoria: str) -> str:
    """A categoria do juiz → o vocabulário de `saude_uf.json`. Função pura.

    `plano_elaboracao` → ELAB; `plano` (ato a partir do Boletim nº 1) → NOVO; `plano_antigo` (ato
    anterior) → VIG, porque plano de ciclo anterior que segue vigente é recorrente, não novo. A
    divisão do VIG em revisado/outro risco é da v0.4 e acontece em `instrumento_v04`, com o
    `consist` da UF — não aqui."""
    return {"plano_elaboracao": "ELAB", "plano": "NOVO", "plano_antigo": "VIG"}.get(categoria)


def julgar_pista(p: dict, buscar_fn=None) -> dict:
    """Baixa, lê e julga uma pista. Devolve o veredito com o que o ato institui."""
    url = p.get("url")
    uf = p.get("uf")
    try:
        corpo = (buscar_fn or buscar)(url, timeout=150, origem="julgar_saude")
    except Exception as e:  # noqa: BLE001
        return {"promove": False, "motivo": f"documento não baixado: {type(e).__name__}", "uf": uf}
    texto = texto_do_documento(corpo, url)
    if not texto.strip():
        return {"promove": False, "motivo": "documento sem texto extraível (PDF sem OCR?)", "uf": uf}
    institui = o_que_institui(texto)
    # O plano de contingência estadual de saúde é, na maioria dos estados, um DOCUMENTO TÉCNICO:
    # ele traz título, ano e órgão, e o ato que o aprova é outro papel. O juiz tem exceção
    # declarada para esse caso (`eh_plano_tecnico`), e a regra para ligá-la é a que o próprio
    # handover do juiz fixou: ligar quando o documento é plano E não traz tipo e número de ato no
    # texto. A data continua obrigatória — sem data não há como situar o ato no ciclo.
    plano_tecnico = ("instrumento" in institui
                     and juiz.RE_TIPO_E_NUMERO.search(texto) is None)
    v = juiz.julgar(texto, uf, uf, url=url, eh_estadual=True, eh_plano_tecnico=plano_tecnico)
    v["institui"] = sorted(institui)
    v["uf"] = uf
    if v.get("promove"):
        v["hash_evidencia"] = preservar_evidencia(
            corpo, url, "pdf" if (url or "").lower().endswith(".pdf") else "html", "julgar_saude")
        if "coordenacao" in v["institui"]:
            v["coordenacao"] = dict(zip(("degrau", "motivo"), degrau_coordenacao(texto, v.get("data"))))
        if "instrumento" in v["institui"]:
            v["status_instrumento"] = status_instrumento(v.get("categoria"))
    return v


def aplicar(su: dict, v: dict, titulo: str, url: str) -> list:
    """Escreve o veredito em `saude_uf.json`. Devolve o que mudou. Não apaga o que já existia.

    O instrumento entra como item NOVO em `instrumentos[]` — a lista é a fonte de verdade desde
    18/09/2026 e o campo de topo é recalculado do melhor item a cada geração. A coordenação é um
    campo único por UF: quando já existe uma com degrau igual ou maior, a nova não rebaixa."""
    uf = v["uf"]
    u = (su.setdefault("uf", {})).setdefault(uf, {})
    mudou = []
    hoje = hoje_editorial().strftime("%d/%m/%Y")
    if v.get("status_instrumento"):
        item = {"status": v["status_instrumento"], "orgao": f"SES-{uf}", "doc": titulo,
                "numero": v.get("numero"), "data": v.get("data"), "url": url,
                "natureza_doc": v.get("natureza"), "tipo": "saude_do_ciclo",
                "hash_evidencia": v.get("hash_evidencia"),
                "justificativa_ex_ante": (f"promovido por julgar_saude.py em {hoje}, codebook "
                                          f"{v.get('codebook')}: documento primário baixado e lido, "
                                          f"sete etapas aprovadas")}
        u.setdefault("instrumentos", []).append(item)
        u["data_verificacao"] = hoje
        u["log_ref"] = f"julgar_saude_{hoje.replace('/', '-')}"
        mudou.append(f"instrumento {v['status_instrumento']}")
    if v.get("coordenacao"):
        ordem = ["LAC", "ANUNCIADO", "PERMANENTE", "REATIVADO_CICLO", "CRIADO_CICLO"]
        atual = (u.get("coordenacao") or {}).get("status")
        novo = v["coordenacao"]["degrau"]
        if atual is None or ordem.index(novo) > ordem.index(atual):
            u["coordenacao"] = {"status": novo, "orgao": f"SES-{uf}", "doc": titulo,
                                "numero": v.get("numero"), "data": v.get("data"), "url": url,
                                "hash_evidencia": v.get("hash_evidencia"),
                                "justificativa_degrau": v["coordenacao"]["motivo"],
                                "data_verificacao": hoje,
                                "log_ref": f"julgar_saude_{hoje.replace('/', '-')}"}
            mudou.append(f"coordenação {novo}")
    return mudou


def autoteste() -> int:
    t_sala = ("PORTARIA Nº 0666/2024 — Dispõe sobre a instituição da Sala de Situação em Saúde para "
              "o enfrentamento das Mudanças Climáticas. O SECRETÁRIO DE ESTADO DE SAÚDE resolve:")
    t_plano = ("RESOLUÇÃO Nº 10 — Aprova o Plano Estadual de Contingência das Arboviroses. "
               "O SECRETÁRIO resolve:")
    t_dois = ("PORTARIA Nº 0195/2026 — Institui o processo de elaboração do Plano Estadual de "
              "Preparação e Resposta a Emergências em Saúde Pública, a sala de situação permanente "
              "e o centro de operações de emergência temporário.")
    t_ciclo = ("PORTARIA Nº 9/2026 — Institui o Centro de Operações de Emergência para o "
               "enfrentamento do El Niño 2026/2027.")
    fonte = pathlib.Path(__file__).read_text(encoding="utf-8")

    def grava_em(nome):
        return ("grav" + "ar(\"" + nome) in fonte

    casos = {
        "ato de sala de situação é coordenação":
            lambda: o_que_institui(t_sala) == {"coordenacao"},
        "ato de plano é instrumento":
            lambda: o_que_institui(t_plano) == {"instrumento"},
        "ato que institui os dois conta nos dois":
            lambda: o_que_institui(t_dois) == {"coordenacao", "instrumento"},
        "texto sem nenhum dos dois não institui nada":
            lambda: o_que_institui("Portaria de nomeação de servidor") == set(),
        # A trava do degrau: ato de 2026 que NÃO nomeia o ciclo é permanente, não criado para ele.
        "ato de 2026 sem menção ao ciclo é PERMANENTE":
            lambda: degrau_coordenacao(t_dois, "30/03/2026")[0] == "PERMANENTE",
        "ato de 2026 que nomeia o ciclo é CRIADO_CICLO":
            lambda: degrau_coordenacao(t_ciclo, "15/07/2026")[0] == "CRIADO_CICLO",
        "ato que reativa e nomeia o ciclo é REATIVADO_CICLO":
            lambda: degrau_coordenacao("Reativa o COE para o El Niño", "10/08/2026")[0] == "REATIVADO_CICLO",
        "ato antigo sem menção ao ciclo é PERMANENTE":
            lambda: degrau_coordenacao(t_sala, "03/10/2024")[0] == "PERMANENTE",
        "categoria do juiz vira vocabulário da saúde":
            lambda: (status_instrumento("plano") == "NOVO"
                     and status_instrumento("plano_elaboracao") == "ELAB"
                     and status_instrumento("plano_antigo") == "VIG"
                     and status_instrumento("decreto") is None),
        "PDF sem texto não vira reprovação de mérito":
            lambda: texto_do_documento(b"%PDF-1.4 lixo", "x.pdf") == "",
        "HTML perde script e tag, e sobra o texto":
            lambda: ("ola" in texto_do_documento(b"<p>ola</p><script>x=1</script>", "a.html")
                     and "x=1" not in texto_do_documento(b"<p>ola</p><script>x=1</script>", "a.html")),
        # A coordenação não rebaixa: UF que já tem ato do ciclo não volta a permanente.
        "coordenação já verificada não é rebaixada":
            lambda: (aplicar({"uf": {"AC": {"coordenacao": {"status": "CRIADO_CICLO"}}}},
                             {"uf": "AC", "coordenacao": {"degrau": "PERMANENTE", "motivo": "x"}},
                             "t", "u") == []),
        "coordenação ausente é escrita":
            lambda: (aplicar({"uf": {"AC": {}}},
                             {"uf": "AC", "coordenacao": {"degrau": "PERMANENTE", "motivo": "x"}},
                             "t", "u") == ["coordenação PERMANENTE"]),
        "instrumento entra como item novo, sem apagar a lista":
            lambda: (len(aplicar({"uf": {"AC": {"instrumentos": [{"status": "VIG"}]}}},
                                 {"uf": "AC", "status_instrumento": "NOVO"}, "t", "u")) == 1),
        # TRAVA ESTRUTURAL: este juiz não escreve no índice do Legal nem marca não localizado.
        "o fonte grava só na camada estadual de saúde e na fila":
            lambda: not any(grava_em(n) for n in ("indice", "municipios", "estados", "pontos_mapa")),
        # A trava certa é de COMPORTAMENTO, não de texto: este juiz só vê documentos que existem,
        # e por isso nunca pode concluir ausência. Marcar ausência exige bateria completa por UF, e
        # essa decisão é de outro passo. (A primeira versão desta trava procurava a palavra no
        # fonte e reprovava por encontrá-la na lista de ordenação — texto não é comportamento.)
        "o degrau de coordenação nunca conclui ausência":
            lambda: all(degrau_coordenacao(t, d)[0] != "LAC" for t, d in (
                (t_sala, "03/10/2024"), (t_dois, "30/03/2026"), (t_ciclo, "15/07/2026"),
                ("", ""), ("texto qualquer", "01/01/2020"))),
    }
    return rodar_autoteste(casos)


def main() -> int:
    args = sys.argv[1:]
    if "--autoteste" in args:
        return autoteste()
    alvo = args[args.index("--uf") + 1].upper() if "--uf" in args else None
    fila = ler(FILA, {}) or {}
    pistas = fila.get("pistas") or []
    candidatas = [p for p in pistas
                  if p.get("oficial") and p.get("url") and not p.get("juiz")
                  and (alvo is None or p.get("uf") == alvo)]
    if "--limite" in args:
        candidatas = candidatas[:int(args[args.index("--limite") + 1])]
    print(f"{len(candidatas)} pista(s) oficial(is) a julgar"
          + (f" em {alvo}" if alvo else "") + f", de {len(pistas)} na fila")
    su = ler(ALVO, {}) or {}
    promovidas, recusadas, mudancas = 0, {}, []
    for p in candidatas:
        v = julgar_pista(p)
        p["juiz"] = {k: v.get(k) for k in ("promove", "motivo", "codebook", "categoria", "data",
                                           "institui", "status_instrumento", "coordenacao")}
        if v.get("promove"):
            promovidas += 1
            m = aplicar(su, v, p.get("titulo") or "", p.get("url"))
            if m:
                mudancas.append(f"{v['uf']}: {', '.join(m)}")
                p["documento_oficial_confirmado"] = p.get("url")
                p["promovivel"] = True
                p["status"] = "promovido_pelo_juiz"
            print(f"  ✓ {v['uf']} · {v.get('categoria')} · institui {v['institui']} · {m or 'sem mudança'}")
        else:
            recusadas[v.get("motivo")] = recusadas.get(v.get("motivo"), 0) + 1
            print(f"  ✗ {p.get('uf')} · {v.get('motivo')}")
    print(f"\n{promovidas} promovida(s) · {len(candidatas) - promovidas} recusada(s)")
    for motivo, n in sorted(recusadas.items(), key=lambda x: -x[1]):
        print(f"   {n}× {motivo}")
    if mudancas:
        print("mudanças: " + " · ".join(mudancas))
    if "--aplicar" in args:
        gravar(ALVO, su)
        gravar(FILA, fila)
        print(f"data/{ALVO} e data/{FILA} gravados")
    else:
        print("(relatório: nada foi gravado)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
