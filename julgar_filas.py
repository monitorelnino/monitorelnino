#!/usr/bin/env python3
"""
julgar_filas.py
===============
Roda o juiz automático (`juiz.py`) sobre as filas de pistas e aplica o que passa, com rede de
proteção. É a Etapa 7 do codebook.

Decisão editorial de 27/09/2026, handover `HANDOVER_juiz_automatico_e_busca_web_27-09-2026.md`
(PR 2), repositório privado. A regra R7 passa a ser: promover é decisão do juiz quando TODOS os
critérios passam no documento primário; falhou um, fica pista, com o motivo visível; a editoria
audita amostra semanal e reverte por errata.

O QUE ESTE SCRIPT NÃO FAZ
-------------------------
- Não promove com base em título, notícia ou resumo: o texto julgado é o do documento primário,
  baixado da fonte oficial e preservado com hash.
- Não usa modelo de linguagem: `juiz.py` é regra versionada.
- Não apaga pista: recusa fica na fila, com `juiz` preenchido e o motivo à vista.
- Não muda peso, régua, escada de créditos nem categoria — isso exige a editoria (§12).
- Não reescreve os coletores: consome as filas que já existem.

REDE DE PROTEÇÃO (reusada de `julgar_e_aplicar_descobertas.py`, testada desde 31/08/2026)
-----------------------------------------------------------------------------------------
backup em disco → aplica → `recalcular_mare.py --write` → suíte de portões → se algum portão
reprovar, **restaura o disco** e devolve a pista com o erro. O rótulo "revertida" sem reverter de
verdade foi um defeito real de 31/08/2026; a restauração é de arquivo, não de rótulo.

USO
  python3 julgar_filas.py --relatorio           # julga e conta, NÃO aplica e NÃO escreve
  python3 julgar_filas.py --relatorio --limite 50
  python3 julgar_filas.py --aplicar             # julga e aplica o que passa
  python3 julgar_filas.py --aplicar --dominio-oficial          # só o que está em domínio oficial
  python3 julgar_filas.py --relatorio --urls-de alvos.txt      # aponta a um conjunto nomeado
  python3 julgar_filas.py --relatorio --ids 2b4ceec828,8bfdd5f2e7
  python3 julgar_filas.py --autoteste
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

# 28/09/2026 (decisão da editoria, item 1): `pistas_querido_diario.json` entra na lista. A suspensão de
# 06/09 caiu, e a regra que a substitui é explícita: toda pista do QD passa pelas etapas 0 a 7 do juiz e
# NUNCA entra direto no banco. A fila começa pelos 169 municípios com excerto reconhecido no diário e sem
# registro nem pista, montada por `scripts/fila_do_juiz_querido_diario.py`.
# 09/10/2026 (lote 2.9): `pistas_revisao.json` saiu — era a fila de revisão humana, derivada, e deixou
# de ser gerada.
FILAS = ("pistas_imprensa.json", "pistas_descobertas.json", "pistas_doe.json",
         "pistas_querido_diario.json")
PROMOCOES = "promocoes_automaticas.json"

# Motivos de recusa do codebook, na ordem das etapas — a ordem do relatório segue esta.
MOTIVOS = ("sem_documento_primario", "documento_inacessivel", "texto_nao_extraivel",
           "ente_nao_confirmado",
           "citacao_incompleta", "executivo_pendente", "autoridade_nao_confirmada",
           # 03/10/2026 (decisão da editoria, plano sem ato de aprovação localizado): os dois
           # motivos do caminho novo do codebook 1.2. Sem eles aqui, o relatório os imprimia como
           # "fora da lista de motivos do codebook" — e motivo que o relatório não reconhece é
           # motivo que ninguém agrupa nem acompanha.
           "plano_sem_identificacao", "minuta_ou_rascunho",
           "noticia_institucional_nao_e_o_plano",
           "natureza_duvidosa", "fora_do_objeto", "familia_de_risco_nao_identificada",
           "resposta")


def pistas_da_fila(doc: dict) -> list:
    """As filas não têm o mesmo nome de lista: `pistas`, `itens` ou `grupos`."""
    for chave in ("pistas", "itens"):
        if isinstance(doc.get(chave), list):
            return doc[chave]
    return []


# 03/10/2026 (garimpo da central): dois FILTROS, para que o juiz possa ser apontado a um conjunto
# em vez de varrer a fila inteira.
#
# A razão é de ordem, não de preguiça: a central garimpou a fila e achou 88 pistas cujo documento
# está em DOMÍNIO OFICIAL do próprio ente — muitas sendo o próprio PDF do plano no sítio da
# prefeitura — paradas como "a confirmar". Varrer 6.456 pendentes para alcançar essas 88 gastaria a
# rodada em busca dirigida de notícia de veículo privado, que é a parte caraa. Com o filtro, o
# documento que já está em domínio oficial vai ao juiz primeiro, que é a prioridade que a editoria
# deu — e a regra nova que ela escreveu: documento em domínio oficial vai direto ao juiz, na mesma
# rodada; notícia de veículo privado é que fica à espera de busca dirigida.

def url_em_dominio_oficial(url: str) -> bool:
    """A URL está em domínio oficial do ente? Função pura.

    Reusa `_dominio_publico` de `coletores_base`, que é quem já sabe distinguir sítio de ente
    (.gov.br, .leg.br, .jus.br, .mp.br, "prefeitura" no host) de API de dado e de armazenamento
    genérico. Uma definição só: duas respostas diferentes para "isto é oficial?" no mesmo
    repositório é como se promove o que não devia.
    """
    if not url:
        return False
    from coletores_base import _dominio_publico
    return _dominio_publico(str(url))


def selecionar(pistas: list, ids=None, so_oficial: bool = False, urls=None) -> list:
    """As pistas que esta rodada julga. Função pura.

    `ids` e `urls` são para apontar o juiz a um conjunto nomeado (o garimpo da central);
    `so_oficial` é o recorte da regra nova. Sem filtro, devolve tudo o que entrou.
    """
    fora = []
    for p in pistas:
        if ids and not any(str(p.get("id") or "").startswith(x) for x in ids):
            continue
        if urls and not any(x in str(p.get("url") or "") for x in urls):
            continue
        if so_oficial and not url_em_dominio_oficial(p.get("url")):
            continue
        fora.append(p)
    return fora


PREFIXO_FECHADA_POR_PRAZO = "fechada — sem documento oficial localizado"


def pendente(p: dict, hoje=None) -> bool:
    """Pista que ainda espera decisão. Já resolvida, não se mexe.

    28/09/2026: o comentário aqui dizia "já julgada por ESTA versão do codebook" e o código não
    olhava a versão nenhuma — qualquer julgamento anterior tirava a pista da fila para sempre.
    Ficava sem efeito o único mecanismo que faz um critério novo alcançar o que o critério velho já
    decidiu: subir a versão. A regra que promoveu quatro registros falsos não teria sido reaplicada
    sobre eles. Agora a comparação é com a versão em vigor, que é o que o comentário sempre disse.

    28/09/2026 (item 2): a pista adiada por causa técnica volta, mas **na data do back-off** — 1, 3
    e depois 7 dias. Sem essa espera, a mesma fonte fora do ar seria consultada toda noite, o teto
    da rodada seria gasto com ela, e as pistas nunca tentadas ficariam para trás. Esgotadas as
    tentativas, a pista fica `inacessivel_persistente`: sai da fila e **continua no registro**, com
    o histórico do que se tentou."""
    from juiz import CODEBOOK_VERSAO
    status = str(p.get("status") or "")
    if (p.get("juiz") or {}).get("codebook") == CODEBOOK_VERSAO:
        return False    # já julgada por esta versão do codebook
    if "inacessivel_persistente" in status:
        return False
    prox = p.get("proxima_tentativa_em")
    if prox and str(prox) > (hoje or _hoje_data()).isoformat():
        return False    # ainda dentro do back-off
    # 09/10/2026 (lote 2.5, A1-16): fechada por prazo DEPOIS de uma leitura do juiz volta quando o
    # codebook muda. O prazo fechava documento oficial lido-e-recusado com o motivo "sem documento
    # oficial localizado" — e a correção do juiz nunca alcançava o que o prazo tinha fechado (38 das
    # 46 eram edições do Querido Diário recusadas por um recorte que não funcionava, A1-03).
    if status.startswith(PREFIXO_FECHADA_POR_PRAZO) and (p.get("juiz") or {}).get("leu_documento"):
        return True
    return status.startswith("pista") or status.startswith("rebaixado") or status.startswith("revertida")


def julgar_uma(p: dict, buscar, preservar=None) -> dict:
    """Julga uma pista e devolve o veredito, sem aplicar nada.

    `buscar(url) -> texto|None` e `preservar(url, texto) -> hash|None` são injetados: é o que
    permite ao autoteste rodar sem rede e sem escrever em `evidencias/`."""
    from juiz import julgar

    from juiz import PADROES_FONTE_PROVAVEL_OFICIAL
    url = p.get("url")
    # 09/10/2026 (lote 2.5, A1-19): a URL fora do padrão de fonte oficial é recusada pela etapa 0
    # sem precisar do texto. Baixá-la antes custava 3.245 downloads de imprensa por versão de
    # codebook — o runner do GitHub lendo página de jornal para descartá-la.
    oficial = bool(url) and any(pad in str(url).lower() for pad in PADROES_FONTE_PROVAVEL_OFICIAL)
    texto = buscar(url) if oficial else None
    # 28/09/2026 (item 1): o `trecho` da pista é o que permite recortar o ATO de dentro da edição do
    # diário. Sem ele, o juiz lê vinte mil caracteres com dezenas de atos e cai em dúvida, corretamente.
    veredito = julgar(texto, nome=p.get("municipio") or "", uf=p.get("uf") or "",
                      ibge=p.get("ibge"), url=url, trecho=p.get("trecho"))
    veredito["pista_id"] = p.get("id")
    veredito["origem"] = p.get("origem")
    # 28/09/2026: separar "não pudemos ler" de "lemos e não serve". Sem esta marca, `--aplicar`
    # gravava recusa PERMANENTE numa pista cujo documento apenas não respondeu naquela noite —
    # uma falha de rede, um 403 de uma hora, um portal fora do ar apagariam a pista para sempre,
    # e `pendente()` nunca mais a devolveria à fila. É a mesma distinção de sempre, um nível
    # abaixo: entre "a fonte não tem" e "não conseguimos ler o que a fonte tem".
    veredito["leu_documento"] = bool(texto)
    # O hash só se grava quando há documento de verdade: preservar um erro servido com 200 (§186)
    # criaria prova falsa.
    if preservar and texto and veredito["criterios"].get("0_documento_primario", {}).get("ok"):
        veredito["hash_evidencia"] = preservar(url, texto)
    return veredito


# 28/09/2026 (item 2 do bloco das 19:50): recusa nunca é permanente por causa técnica.
#
# Duas coisas diferentes vinham com o mesmo nome. **Técnica** é não ter conseguido ler: 403, 429,
# timeout, portal fora do ar, texto que não se extrai do PDF. **Por critério** é ter lido e o
# documento não servir. A primeira fala do nosso lado da linha; a segunda, do documento. Tratá-las
# igual apaga pista por causa de uma noite ruim de rede — foi o que o desenho de `leu_documento`
# evitou na primeira passada real, poupando 32 pistas.
MOTIVOS_TECNICOS = ("documento_inacessivel", "texto_nao_extraivel")
# Back-off entre tentativas. Cinco tentativas, e então `inacessivel_persistente` — que continua
# VISÍVEL no arquivo: pista que ninguém consegue ler é um fato sobre a fonte, e some do processo,
# não do registro.
BACKOFF_DIAS = (1, 3, 7)
TENTATIVAS_ATE_PERSISTENTE = 5


def classe_da_recusa(v: dict) -> str:
    """'tecnica' | 'criterio' | '' (quando promove). A classe decide o destino, não o motivo."""
    if v.get("promove"):
        return ""
    if v.get("motivo") in MOTIVOS_TECNICOS or not v.get("leu_documento", True):
        return "tecnica"
    return "criterio"


def proxima_tentativa(n_feitas: int, hoje):
    """A data da próxima leitura, depois de `n_feitas` tentativas técnicas. None quando esgotou.

    1, 3 e depois 7 dias; na quinta tentativa não há próxima, e a pista vira
    `inacessivel_persistente`. O primeiro retorno é a espera **depois da primeira** tentativa — a
    versão anterior indexava pelo número de tentativas e pulava o 1 dia inteiro."""
    import datetime
    if n_feitas >= TENTATIVAS_ATE_PERSISTENTE:
        return None
    return hoje + datetime.timedelta(days=BACKOFF_DIAS[min(max(n_feitas, 1) - 1,
                                                           len(BACKOFF_DIAS) - 1)])


# Recusas que a busca dirigida ataca: as duas em que o problema é o DOCUMENTO, não o conteúdo dele.
MOTIVOS_QUE_PEDEM_BUSCA_DIRIGIDA = ("sem_documento_primario", "citacao_incompleta")


def tentar_busca_dirigida(p: dict, v: dict, buscar_texto, preservar) -> dict:
    """Procura o ato nas três rotas e, achando, rejulga sobre ele. Devolve o veredito que vale.

    Achou → o juiz percorre as etapas 1 a 7 sobre o documento encontrado, com as mesmas regras: a
    busca dirigida não afrouxa critério nenhum, ela só entrega um documento melhor para julgar.
    Não achou → a recusa original fica, e a pista passa a dizer onde se procurou e quando."""
    import importlib
    import sys as _sys
    _sys.path.insert(0, str(RAIZ / "scripts"))
    bd = importlib.import_module("busca_dirigida_do_ato")
    from coletores_base import hoje_editorial

    ident = bd.identificadores(p)
    url, fontes = bd.procurar(ident, consultar_qd=_qd_para_busca_dirigida,
                              buscar_web=_web_para_busca_dirigida, esperar=_ritmo)
    bd.registrar_busca(p, fontes, hoje_editorial(), achou_url=url)
    if not url:
        v["busca_dirigida"] = {"fontes": fontes, "encontrou": None}
        return v

    # 09/10/2026 (lote 2.5, A1-24): a edição achada no Querido Diário vem com o excerto que a casou,
    # e o excerto vai como `trecho` — sem ele o juiz lê a edição inteira (dezenas de atos) e recusa.
    excerto = _EXCERTOS_DO_QD.get(url)
    novo = julgar_uma({**p, "url": url, **({"trecho": excerto} if excerto else {})},
                      buscar_texto, preservar)
    novo["busca_dirigida"] = {"fontes": fontes, "encontrou": url,
                              "recusa_original": v.get("motivo")}
    return novo


def _ritmo():
    from monitorar_busca_web import espera_do_ritmo
    import time
    time.sleep(espera_do_ritmo())


def _qd_para_busca_dirigida(ibge, ident):
    """Rota 1: o diário do território, pelos termos do plano. Devolve a URL do TEXTO da edição."""
    try:
        from consultar_querido_diario import _por_territorio
    except Exception:  # noqa: BLE001
        return None
    termo = ident.get("nome_do_plano") or "plano de contingência"
    try:
        dados = _por_territorio([ibge], termo)
    except Exception:  # noqa: BLE001
        return None
    for g in (dados or {}).get("gazettes", []) or []:
        url = g.get("txt_url") or g.get("url")
        excertos = [e for e in (g.get("excerpts") or []) if str(e).strip()]
        if url and excertos:
            _EXCERTOS_DO_QD[url] = excertos[0]
            return url
    # Edição sem excerto não se recorta: o juiz leria dezenas de atos e recusaria. Não é candidata.
    return None


# url -> excerto da edição achada pela rota 1 (só vive durante a rodada).
_EXCERTOS_DO_QD = {}


def _web_para_busca_dirigida(consulta):
    """Rotas 2 e 3: o metabuscador da rodada, com o mesmo disjuntor por motor de origem."""
    try:
        import motores_busca
        from monitorar_busca_web import buscar_searxng
        motores = motores_busca.ativos(motores_busca.ler_estado(), motores_busca.agora_iso())
    except Exception:  # noqa: BLE001
        return []
    try:
        return (buscar_searxng(consulta, motores=motores) or {}).get("results", [])
    except Exception:  # noqa: BLE001
        # Motor mudo não é ausência de ato: é ausência de resposta. A recusa original fica, e a
        # pista volta pela fila de reprocessamento — nunca vira "não existe".
        return []


def aplicar_no_objeto(p: dict, v: dict) -> str:
    """Escreve o veredito na pista e diz o que foi feito: promovida, recusada ou adiada.

    Função pura sobre o dicionário da pista — é o que permite ao autoteste provar, sem rede e sem
    escrita, que documento não lido NÃO queima a pista. Adiada não recebe `juiz`: se recebesse,
    `pendente()` a consideraria julgada e ela nunca voltaria.

    28/09/2026 (item 2 do bloco das 19:50): toda tentativa fica registrada em `juiz_tentativas`,
    com data, classe e motivo. Nada se apaga — a pista guarda o que já se tentou, e é por esse
    histórico que se sabe se uma fonte está fora do ar há uma noite ou há um mês."""
    import datetime
    hoje = _hoje_data()
    classe = classe_da_recusa(v)
    tentativas = p.setdefault("juiz_tentativas", [])
    tentativas.append({"em": hoje.isoformat(), "classe": classe or "promocao",
                       "motivo": v.get("motivo"), "codebook": v.get("codebook")})

    if classe == "tecnica":
        # Não escreve `juiz`: a pista continua pendente, e volta na data do back-off.
        tecnicas = sum(1 for t in tentativas if t.get("classe") == "tecnica")
        prox = proxima_tentativa(tecnicas, hoje)
        if prox is None:
            p["status"] = (f"pista — inacessivel_persistente: {tecnicas} tentativas sem leitura do "
                           f"documento; continua no registro, fora da fila")
            p.pop("proxima_tentativa_em", None)
            return "inacessivel"
        p["proxima_tentativa_em"] = prox.isoformat()
        return "adiada"

    p.pop("proxima_tentativa_em", None)
    p["juiz"] = {"codebook": v["codebook"], "promove": v["promove"], "motivo": v["motivo"],
                 "criterios": v["criterios"], "categoria": v["categoria"],
                 "data": v["data"], "julgado_em": hoje.isoformat(),
                 "hash_evidencia": v.get("hash_evidencia")}
    if v["promove"]:
        return "promovida"
    p["status"] = f"pista — recusada pelo juiz: {v['motivo']}"
    return "recusada"


def _hoje_data():
    from coletores_base import hoje_editorial
    return hoje_editorial()


def _hoje_iso() -> str:
    from coletores_base import hoje_editorial
    return hoje_editorial().isoformat()


def contar(vereditos: list) -> dict:
    """Contagens do relatório: promovidas, recusadas por critério, resposta, fora do objeto."""
    c = {"pistas": len(vereditos), "com_documento": 0, "promovidas": 0,
         "por_motivo": {m: 0 for m in MOTIVOS}, "outros_motivos": {}}
    for v in vereditos:
        if v["criterios"].get("0_documento_primario", {}).get("ok"):
            c["com_documento"] += 1
        if v["promove"]:
            c["promovidas"] += 1
            continue
        m = v.get("motivo") or "sem_motivo"
        if m in c["por_motivo"]:
            c["por_motivo"][m] += 1
        else:
            c["outros_motivos"][m] = c["outros_motivos"].get(m, 0) + 1
    return c


def imprimir_relatorio(c: dict, por_categoria: dict = None) -> None:
    print(f"\n{c['pistas']} pista(s) julgada(s); {c['com_documento']} com documento primário "
          f"em fonte oficial; {c['promovidas']} promovida(s)")
    if por_categoria:
        for cat, n in sorted(por_categoria.items()):
            print(f"    {cat}: {n}")
    print("  recusas por critério:")
    for m in MOTIVOS:
        if c["por_motivo"][m]:
            print(f"    {m}: {c['por_motivo'][m]}")
    for m, n in sorted(c["outros_motivos"].items(), key=lambda kv: -kv[1]):
        print(f"    {m}: {n}  (fora da lista de motivos do codebook)")


# =============================================================================================
def autoteste() -> int:
    """Offline: sem rede, sem escrita em data/ nem em evidencias/."""
    from juiz import CANARIOS, CODEBOOK_VERSAO
    casos = []

    textos = {c["url"]: c["texto"] for c in CANARIOS.values()}
    buscar = lambda u: textos.get(u)                                      # noqa: E731
    preservados = []
    preservar = lambda u, t: (preservados.append(u), "hash" + str(len(preservados)))[1]   # noqa: E731

    pistas = [{"id": nome, "municipio": c["nome"], "uf": c["uf"], "url": c["url"],
               "origem": "teste", "status": "pista — promover a registro exige documento primário"}
              for nome, c in CANARIOS.items()]
    # o pdf_ilegivel e o plano_novo compartilham a URL; o dicionário de textos guarda um só.
    # Isso é fiel ao mundo: a mesma URL devolve um texto só.
    vereditos = [julgar_uma(p, buscar, preservar) for p in pistas]

    # 09/10/2026 (lote 2.5, A1-19): URL fora do padrão não é baixada.
    def _nao_baixe(u):
        raise AssertionError(f"baixou {u}")
    v_imprensa = julgar_uma({"id": "x", "municipio": "Bonito", "uf": "MS",
                             "url": "https://g1.globo.com/ms/plano.html"}, _nao_baixe)
    casos.append(("URL de imprensa é recusada sem download",
                  v_imprensa["motivo"] == "sem_documento_primario"))
    # 09/10/2026 (lote 2.5, A1-16): fechada por prazo depois de leitura volta com codebook novo.
    fechada_lida = {"status": "fechada — sem documento oficial localizado no prazo da fila",
                    "juiz": {"codebook": "1.3 (03/10/2026)", "leu_documento": True,
                             "motivo": "natureza_duvidosa"}}
    casos.append(("fechada por prazo depois de leitura volta com codebook novo",
                  pendente(fechada_lida)))
    casos.append(("fechada por prazo e já julgada por este codebook não volta",
                  not pendente({**fechada_lida, "juiz": {**fechada_lida["juiz"],
                                                         "codebook": CODEBOOK_VERSAO}})))
    casos.append(("fechada por prazo sem leitura não volta pelo codebook",
                  not pendente({"status": fechada_lida["status"],
                                "juiz": {"codebook": "1.3 (03/10/2026)", "leu_documento": False}})))
    casos.append(("fechada por outro motivo não volta",
                  not pendente({"status": "fechada — notícia genérica",
                                "juiz": {"codebook": "1.3", "leu_documento": True}})))
    casos.append(("todo veredito carrega a versão do codebook",
                  all(v["codebook"] == CODEBOOK_VERSAO for v in vereditos)))
    casos.append(("todo veredito carrega o id da pista",
                  all(v["pista_id"] for v in vereditos)))
    c = contar(vereditos)
    casos.append(("o relatório conta uma linha por pista", c["pistas"] == len(pistas)))
    casos.append(("promovidas nunca passa de com_documento", c["promovidas"] <= c["com_documento"]))
    casos.append(("notícia não é preservada como evidência",
                  all("g1.globo.com" not in u for u in preservados)))
    casos.append(("recusa por fonte não oficial não tem hash",
                  all("hash_evidencia" not in v for v in vereditos
                      if v.get("motivo") == "sem_documento_primario")))

    # pista já julgada por este codebook não volta à fila
    p_julgada = {"status": "pista — …", "juiz": {"codebook": CODEBOOK_VERSAO}}
    casos.append(("pista já julgada por este codebook não é rejulgada", not pendente(p_julgada)))
    casos.append(("pista julgada por codebook ANTERIOR volta à fila",
                  pendente({"status": "pista — promover a registro exige documento primário",
                            "juiz": {"codebook": "0.9 (ontem)"}})))
    casos.append(("pista pendente é reconhecida",
                  pendente({"status": "pista — promover a registro exige documento primário"})))
    casos.append(("pista rebaixada pelo C10 volta ao juiz",
                  pendente({"status": "rebaixado_c10 — volta a registro só com documento"})))
    casos.append(("pista revertida por portão volta ao juiz",
                  pendente({"status": "revertida_erro_portao"})))
    casos.append(("pista aplicada não volta ao juiz",
                  not pendente({"status": "aplicada", "juiz": {"codebook": CODEBOOK_VERSAO}})))

    # documento ausente: a pista fica, com motivo, e nada é preservado
    v = julgar_uma({"id": "x", "municipio": "Bonito", "uf": "MS", "url": "https://bonito.ms.gov.br/x.pdf"},
                   lambda u: None, preservar)
    casos.append(("documento não obtido devolve documento_inacessivel, não sem_documento_primario",
                  v["motivo"] == "documento_inacessivel" and not v["promove"]))
    casos.append(("documento não lido é marcado como tal no veredito", v["leu_documento"] is False))
    casos.append(("documento lido é marcado como tal",
                  all(x["leu_documento"] for x in vereditos if x.get("hash_evidencia"))))

    # 28/09/2026: a trava que impede a pista de ser queimada por uma falha de rede. Sem ela,
    # `--aplicar` gravava recusa permanente e `pendente()` nunca mais devolvia a pista à fila.
    p_adiada = {"id": "y", "status": "pista — promover a registro exige documento primário"}
    casos.append(("documento não lido ADIA: não escreve juiz nem muda status",
                  aplicar_no_objeto(p_adiada, v) == "adiada"
                  and "juiz" not in p_adiada
                  and p_adiada["status"].startswith("pista — promover")))
    import datetime as _dt
    _hoje = _dt.date(2026, 9, 28)
    casos.append(("pista adiada NÃO volta hoje: espera o back-off",
                  not pendente(p_adiada, _hoje)))
    casos.append(("a data da próxima tentativa fica escrita na pista",
                  p_adiada.get("proxima_tentativa_em") is not None))
    casos.append(("pista adiada volta depois do back-off",
                  pendente(p_adiada, _dt.date(2026, 10, 30))))
    casos.append(("a tentativa fica no histórico, com classe e motivo",
                  p_adiada["juiz_tentativas"][-1]["classe"] == "tecnica"
                  and p_adiada["juiz_tentativas"][-1]["motivo"] == "documento_inacessivel"))

    # A classe da recusa: é ela que decide o destino, não o motivo.
    casos.append(("documento inacessível é recusa TÉCNICA",
                  classe_da_recusa({"promove": False, "motivo": "documento_inacessivel",
                                    "leu_documento": False}) == "tecnica"))
    casos.append(("texto não extraível é recusa TÉCNICA",
                  classe_da_recusa({"promove": False, "motivo": "texto_nao_extraivel",
                                    "leu_documento": True}) == "tecnica"))
    casos.append(("documento lido e reprovado é recusa POR CRITÉRIO",
                  classe_da_recusa({"promove": False, "motivo": "fora_do_objeto",
                                    "leu_documento": True}) == "criterio"))
    casos.append(("url que não é fonte oficial é recusa POR CRITÉRIO (a url é o que é)",
                  classe_da_recusa({"promove": False, "motivo": "sem_documento_primario",
                                    "leu_documento": True}) == "criterio"))
    casos.append(("promoção não tem classe de recusa",
                  classe_da_recusa({"promove": True}) == ""))

    # O back-off e o fim dele.
    casos.append(("o back-off é 1, 3 e depois 7 dias",
                  [(proxima_tentativa(n, _hoje) - _hoje).days for n in (1, 2, 3, 4)] == [1, 3, 7, 7]))
    casos.append(("esgotadas as cinco tentativas, não há próxima data",
                  proxima_tentativa(5, _hoje) is None))

    p_teimosa = {"status": "pista — promover a registro exige documento primário"}
    v_tec = dict(v, leu_documento=False, motivo="documento_inacessivel", promove=False)
    saidas = [aplicar_no_objeto(p_teimosa, v_tec) for _ in range(5)]
    casos.append(("quatro tentativas adiam; a quinta vira inacessivel_persistente",
                  saidas == ["adiada"] * 4 + ["inacessivel"]))
    casos.append(("a pista inacessível sai da fila", not pendente(p_teimosa, _dt.date(2027, 1, 1))))
    casos.append(("e continua no registro, com o histórico inteiro",
                  "inacessivel_persistente" in p_teimosa["status"]
                  and len(p_teimosa["juiz_tentativas"]) == 5))
    casos.append(("nada foi apagado: a pista não recebeu veredito de recusa",
                  "juiz" not in p_teimosa))

    v_recusa = dict(v, leu_documento=True, motivo="fora_do_objeto", promove=False)
    p_recusa = {"id": "z", "status": "pista — promover a registro exige documento primário"}
    casos.append(("documento lido e recusado marca a recusa com o motivo",
                  aplicar_no_objeto(p_recusa, v_recusa) == "recusada"
                  and p_recusa["status"] == "pista — recusada pelo juiz: fora_do_objeto"))
    casos.append(("pista recusada não volta ao juiz", not pendente(p_recusa)))

    v_promove = dict(v, leu_documento=True, promove=True, motivo=None)
    p_promove = {"id": "w", "status": "pista — promover a registro exige documento primário"}
    casos.append(("promovida recebe juiz e NÃO é marcada como recusada",
                  aplicar_no_objeto(p_promove, v_promove) == "promovida"
                  and p_promove["juiz"]["promove"] is True
                  and "recusada" not in p_promove["status"]))

    # as filas: leitura tolerante ao nome da lista
    casos.append(("lê fila com 'pistas'", len(pistas_da_fila({"pistas": [1, 2]})) == 2))
    casos.append(("lê fila com 'itens'", len(pistas_da_fila({"itens": [1]})) == 1))
    casos.append(("fila sem lista conhecida devolve vazio", pistas_da_fila({"grupos": {}}) == []))

    # o modo relatório não escreve: nem evidência, nem arquivo de fila, nem índice. A trava é
    # sobre o CÓDIGO de main(), porque exercitar main() de verdade tocaria o banco real.
    import inspect
    import re as _re
    fonte = inspect.getsource(main)
    # a docstring de `hash_do_texto` CITA preservar_evidencia para explicar por que não a usa;
    # a trava tem de procurar a CHAMADA, não a palavra.
    nao_preserva = not _re.search(r"preservar_evidencia\s*\(", fonte)
    guarda_pista = _re.search(r"if not aplicar:\s+continue", fonte)
    grava_fila_sob_guarda = _re.search(r"if aplicar:\s+gravar_em\(DATA / nome_fila", fonte)
    casos.append(("o juiz não preserva evidência: a porta canônica é preservar_evidencias.py --ler",
                  nao_preserva))
    casos.append(("o modo relatório não marca a pista em memória", bool(guarda_pista)))
    casos.append(("a fila só é gravada sob --aplicar", bool(grava_fila_sob_guarda)))

    # os filtros do garimpo (03/10/2026)
    amostra = [{"id": "aaa111", "url": "https://franca.sp.gov.br/plano.pdf"},
               {"id": "bbb222", "url": "https://g1.globo.com/noticia.html"},
               {"id": "ccc333", "url": "https://camara.leme.sp.leg.br/ato.pdf"},
               {"id": "ddd444", "url": "https://api.queridodiario.ok.org.br/x"}]
    casos.append(("sem filtro, tudo entra", len(selecionar(amostra)) == 4))
    casos.append(("--dominio-oficial pega .gov.br e .leg.br",
                  [p["id"] for p in selecionar(amostra, so_oficial=True)] == ["aaa111", "ccc333"]))
    casos.append(("--dominio-oficial descarta veículo privado",
                  all(p["id"] != "bbb222" for p in selecionar(amostra, so_oficial=True))))
    casos.append(("--dominio-oficial descarta API de dado",
                  all(p["id"] != "ddd444" for p in selecionar(amostra, so_oficial=True))))
    casos.append(("--ids aponta pelo começo do id",
                  [p["id"] for p in selecionar(amostra, ids=["aaa"])] == ["aaa111"]))
    casos.append(("--urls aponta por trecho da URL",
                  [p["id"] for p in selecionar(amostra, urls=["franca.sp.gov.br"])] == ["aaa111"]))
    casos.append(("os filtros se combinam",
                  selecionar(amostra, ids=["bbb"], so_oficial=True) == []))
    casos.append(("url vazia não é domínio oficial", not url_em_dominio_oficial("")))
    # e o caminho sem preservador devolve veredito sem hash
    v_sem = julgar_uma({"id": "z", "municipio": "Bonito", "uf": "MS",
                        "url": CANARIOS["plano_novo"]["url"]}, buscar, None)
    casos.append(("sem função de hash, o veredito não inventa hash", "hash_evidencia" not in v_sem))

    # todo motivo que o juiz produz está na lista do relatório
    motivos_vistos = {v.get("motivo") for v in vereditos if not v["promove"]}
    casos.append(("todo motivo produzido pelos canários está no codebook do relatório",
                  motivos_vistos <= set(MOTIVOS)))

    # A busca dirigida, ligada ao juiz: achou documento, rejulga; não achou, a recusa fica.
    import types as _types
    _bd = _types.SimpleNamespace(
        identificadores=lambda p: {"municipio": "Bonito", "uf": "MS", "ibge": "5002209",
                                   "nome_do_plano": "Plano de Contingência"},
        procurar=lambda ident, **kw: ("https://bonito.ms.gov.br/achado.pdf", ["querido_diario"]),
        registrar_busca=lambda p, f, h, achou_url=None: p.setdefault("busca_dirigida", []).append(
            {"fontes": f, "encontrou": achou_url}))
    _mod = sys.modules.get("busca_dirigida_do_ato")
    sys.modules["busca_dirigida_do_ato"] = _bd
    try:
        p_busca = {"id": "b1", "status": "pista — promover", "url": "https://g1.globo.com/x"}
        v_recusa = {"motivo": "sem_documento_primario", "promove": False, "leu_documento": False,
                    "codebook": CODEBOOK_VERSAO, "criterios": {}, "categoria": None, "data": None}
        textos_achado = {"https://bonito.ms.gov.br/achado.pdf": CANARIOS["plano_novo"]["texto"]}
        v2 = tentar_busca_dirigida(p_busca, v_recusa, lambda u: textos_achado.get(u), None)
        casos.append(("busca dirigida que acha documento faz o juiz rejulgar sobre ele",
                      v2.get("busca_dirigida", {}).get("encontrou", "").endswith("achado.pdf")))
        casos.append(("o veredito novo guarda qual era a recusa original",
                      v2["busca_dirigida"]["recusa_original"] == "sem_documento_primario"))
        casos.append(("a pista registra onde se procurou",
                      p_busca["busca_dirigida"][0]["fontes"] == ["querido_diario"]))

        _bd.procurar = lambda ident, **kw: (None, ["querido_diario", "sitio_oficial", "busca_web"])
        p2 = {"id": "b2", "status": "pista — promover"}
        v3 = tentar_busca_dirigida(p2, dict(v_recusa), lambda u: None, None)
        casos.append(("busca sem achado mantém a recusa original",
                      v3["motivo"] == "sem_documento_primario" and not v3["promove"]))
        casos.append(("e escreve as três rotas tentadas",
                      v3["busca_dirigida"]["fontes"] == ["querido_diario", "sitio_oficial",
                                                         "busca_web"]
                      and v3["busca_dirigida"]["encontrou"] is None))
        casos.append(("só recusa por falta de documento aciona a busca",
                      MOTIVOS_QUE_PEDEM_BUSCA_DIRIGIDA == ("sem_documento_primario",
                                                           "citacao_incompleta")))
    finally:
        if _mod is None:
            sys.modules.pop("busca_dirigida_do_ato", None)
        else:
            sys.modules["busca_dirigida_do_ato"] = _mod

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    imprimir_relatorio(c)
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 0


# =============================================================================================
def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()

    aplicar = "--aplicar" in sys.argv
    # A busca dirigida custa rede e tempo; fica ligada por padrão (é o que a decisão das 17:20
    # pede) e sai com `--sem-busca-dirigida` para uma passada puramente local.
    dirigida = "--sem-busca-dirigida" not in sys.argv
    limite = int(sys.argv[sys.argv.index("--limite") + 1]) if "--limite" in sys.argv else None
    ids = (sys.argv[sys.argv.index("--ids") + 1].split(",") if "--ids" in sys.argv else None)
    urls = (sys.argv[sys.argv.index("--urls") + 1].split(",") if "--urls" in sys.argv else None)
    so_oficial = "--dominio-oficial" in sys.argv
    if "--urls-de" in sys.argv:
        alvo = pathlib.Path(sys.argv[sys.argv.index("--urls-de") + 1])
        urls = [l.strip() for l in alvo.read_text(encoding="utf-8").splitlines() if l.strip()]

    import funil
    from coletores_base import DATA, gravar_em, ler, log_busca, hoje_editorial
    from julgar_e_aplicar_descobertas import buscar_texto

    def hash_do_texto(url, texto):
        """O hash do texto julgado, para o registro da decisão — NÃO preserva evidência.

        27/09/2026: a primeira versão chamava `preservar_evidencia` com o texto extraído e extensão
        `txt`. O portão 26 (`verificar_evidencias.py`) reprovou com razão: evidência de texto cuja
        URL termina em `.pdf` e sem `texto_manual: true` seria SOBRESCRITA por
        `preservar_evidencias.py --ler`, que é a porta canônica de preservação e guarda o binário.
        Duas portas gravando a mesma chave é como se perde prova. O juiz precisa do hash para
        identificar o que julgou; preservar o documento é trabalho de quem já o faz."""
        from coletores_base import sha256
        return sha256(texto.encode("utf-8")) if texto else None

    vereditos, por_fila = [], {}
    feitos = {"promovida": 0, "recusada": 0, "adiada": 0, "inacessivel": 0}
    for nome_fila in FILAS:
        doc = ler(nome_fila)
        if not doc:
            continue
        lista = pistas_da_fila(doc)
        alvo = selecionar([p for p in lista if pendente(p)], ids=ids, so_oficial=so_oficial,
                          urls=urls)
        if limite is not None:
            alvo = alvo[:max(0, limite - len(vereditos))]
        por_fila[nome_fila] = len(alvo)
        print(f"{nome_fila}: {len(alvo)} pendente(s) de {len(lista)}")
        for p in alvo:
            v = julgar_uma(p, buscar_texto, hash_do_texto)
            # 28/09/2026 (bloco das 17:20): a recusa por falta de documento primário não encerra a
            # pista antes de PROCURAR o ato. 176 das 250 primeiras recusas foram esta: a pista
            # aponta a notícia, e a notícia não é o ato — mas diz que ele existe e onde procurar.
            if dirigida and v.get("motivo") in MOTIVOS_QUE_PEDEM_BUSCA_DIRIGIDA:
                v = tentar_busca_dirigida(p, v, buscar_texto, hash_do_texto)
            vereditos.append(v)
            if not aplicar:
                continue   # relatório não escreve nem no objeto em memória que será gravado
            feitos[aplicar_no_objeto(p, v)] += 1
        if aplicar:
            gravar_em(DATA / nome_fila, doc)

    c = contar(vereditos)
    por_categoria = {}
    for v in vereditos:
        if v["promove"]:
            por_categoria[v["categoria"]] = por_categoria.get(v["categoria"], 0) + 1
    imprimir_relatorio(c, por_categoria)
    if aplicar:
        print(f"aplicado na fila: {feitos['promovida']} promovida(s), "
              f"{feitos['recusada']} recusada(s) por critério, {feitos['adiada']} adiada(s) por "
              f"causa técnica (voltam pelo back-off de 1, 3 e 7 dias), "
              f"{feitos['inacessivel']} inacessivel_persistente (cinco tentativas sem leitura; "
              f"saem da fila e ficam no registro)")

    if aplicar:
        funil.registrar("juiz", pistas_recebidas=c["pistas"], com_documento=c["com_documento"],
                        promovidas=c["promovidas"],
                        **{f"recusa_{m}": n for m, n in c["por_motivo"].items() if n})
        registro = ler(PROMOCOES) or {"_governanca": (
            "Registro de toda decisão do juiz automático (§ do CHANGELOG de 27/09/2026). Uma linha "
            "por pista julgada, com os critérios 1-6 e o trecho que satisfez cada um. Errata humana "
            "reverte com uma linha. Este arquivo é o que alimenta a auditoria amostral semanal."),
            "decisoes": []}
        registro["decisoes"] = (registro.get("decisoes") or []) + vereditos
        gravar_em(DATA / PROMOCOES, registro)
        for v in vereditos:
            log_busca("juiz", 5, [f"pista {v.get('pista_id')}"],
                      "registro" if v["promove"] else "pista",
                      uf=v.get("uf"), municipio=v.get("municipio"), ibge=v.get("ibge"),
                      resultados=f"juiz {v['codebook']}: {v['motivo'] or v['categoria']}",
                      hash_evidencia=v.get("hash_evidencia"))
        print(f"\n{len(vereditos)} decisão(ões) gravada(s) em data/{PROMOCOES} e no log")
        print("A APLICAÇÃO em municipios.json/estados.json continua em julgar_e_aplicar_descobertas.py,")
        print("que tem a rede de proteção (backup, portões, rollback em disco) testada desde 31/08/2026.")
    else:
        print("\nrelatório apenas; nada escrito (use --aplicar)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
