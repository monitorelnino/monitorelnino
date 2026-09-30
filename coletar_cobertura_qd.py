#!/usr/bin/env python3
"""Cobertura do Querido Diário por município — pelo DIRETÓRIO do projeto, não por busca de edição.

Item 6 da fila viva (decisão da editoria, 30/09/2026), achado pelo exemplo de Abatiá/PR.

A PERGUNTA QUE ESTE ARQUIVO RESPONDE, E A QUE ELE NÃO RESPONDE
-------------------------------------------------------------
Responde uma só, binária: **o município tem diário municipal coletado pelo Querido Diário?** Não
responde se há plano, nem se houve menção, nem se alguém leu. "Indexado" é a existência do canal;
"pesquisado e sem menção" é leitura. Confundir os dois transforma ausência de fonte em ausência de
fato, que é o erro que o §4.1.2 existe para impedir.

O QUE MEDE A COBERTURA: EXISTÊNCIA DE EDIÇÃO — E O QUE O DIRETÓRIO NÃO MEDE
---------------------------------------------------------------------------
Até 30/09/2026 a cobertura era inferida de uma busca de edições numa janela: se a consulta não
devolvesse gazeta, o município ia a `false`. Isso mistura duas coisas — município sem diário no
Querido Diário e município com diário que não publicou na janela — e envelhece, porque o carimbo
fica preso ao dia do teste. Em 30/09/2026 o arquivo tinha 1.859 municípios testados em 09/09 e 2.362
em 12/09, e a editoria pediu a checagem de Abatiá justamente por isso.

A primeira versão desta rotina usou o **nível** do diretório oficial (`/api/cities/`) como veredito:
nível 3 (com `availability_date`) seria coberto, níveis 0 e 1 não. A conferência derrubou a ideia
antes de ela virar dado publicado. Dos 17 municípios que o nível rebaixaria, **16 têm edição
indexada de fato** — Areal/RJ com 3.426 edições em nível 1, Comendador Levy Gasparian/RJ com 3.471
em nível **0**, São Paulo com 20 em nível 1. O nível descreve o estágio do projeto de raspagem, não
a existência do acervo, e publicar a queda teria apagado cobertura real de dezesseis municípios.

O veredito, então, é a pergunta direta ao acervo: **`/api/gazettes?territory_ids=<ibge>&size=1`
devolve alguma edição?** Sem janela de data — é justamente a janela que envelhecia o retrato antigo,
misturando "não tem diário no Querido Diário" com "não publicou naqueles dias". Uma requisição por
município, 5.571 no total, o que só se faz porque a resposta **não precisa ser refeita para quem já
está coberto**: edição indexada não desaparece. A rotina semanal reconsulta só os `false`, que é
onde o acervo cresce — e é essa a razão de ela existir.

O nível do diretório continua gravado, como `nivel_qd`, por ser informação útil sobre o estágio da
raspagem. **Ele não decide nada.**

O HOST DA API TEM DOIS CAMINHOS, E UM DELES FALHA
-------------------------------------------------
`api.queridodiario.ok.org.br` recusa o handshake TLS (`SSLV3_ALERT_HANDSHAKE_FAILURE`) em parte dos
clientes — inclusive no ambiente em que esta rotina foi escrita. O mesmo serviço responde por
`queridodiario.ok.org.br/api/...`. Os dois entram, nesta ordem, e o que responder vale; se nenhum
responder, a rotina **não escreve nada** e sai com erro. Reescrever o retrato do país a partir de uma
falha de rede seria apagar cobertura por indisponibilidade — exatamente o contrário do que ela faz.

USO
  python3 coletar_cobertura_qd.py --autoteste
  python3 coletar_cobertura_qd.py            # reescreve data/cobertura_qd.json
  python3 coletar_cobertura_qd.py --relatorio  # o que mudaria, sem escrever
"""
import datetime
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

DIRETORIOS = ("https://queridodiario.ok.org.br/api/cities/",
              "https://api.queridodiario.ok.org.br/cities/")
SAIDA = RAIZ / "data" / "cobertura_qd.json"
# A lista dos 5.571 vive em `verificacao_municipal.json`. `municipios.json` são os 267
# registros pontuáveis — usá-lo como universo do país varreria 267 municípios e
# declararia os outros 5.304 ausentes do diretório. Aconteceu na primeira execução.
MUNICIPIOS = RAIZ / "data" / "verificacao_municipal.json"
NIVEL_COM_EDICAO = "3"
MINIMO_PLAUSIVEL = 5000     # o diretório cobre o país; resposta curta é resposta quebrada
GAZETAS = "https://queridodiario.ok.org.br/api/gazettes?territory_ids={ibge}&size=1"
GAZETAS_ALT = "https://api.queridodiario.ok.org.br/gazettes?territory_ids={ibge}&size=1"

GOVERNANCA = (
    "Cobertura do Querido Diário por município. `cobertura_qd: true` = o Querido Diário COLETA o "
    "diário do município (nível 3 do diretório oficial, com data de disponibilidade). `false` = não "
    "coleta — e `nivel_qd` diz se é porque o município está fora do projeto (nível 0) ou porque o "
    "diário está cadastrado sem coleta (nível 1). Isto é existência de canal, NÃO leitura: não "
    "confundir com \"pesquisado e sem menção\". Fonte: diretório oficial do Querido Diário, uma "
    "requisição para o país inteiro. Atualizado pela rotina semanal (decisão da editoria, "
    "30/09/2026, item 6 da fila viva)."
)


def cobertura_do_nivel(nivel) -> bool:
    """O que o NÍVEL do diretório diria. Função pura — e **não é o veredito de cobertura**.

    Fica no arquivo porque é o sinal que a primeira versão usou e a conferência derrubou: dos 17
    municípios que ele rebaixaria, 16 têm edição indexada. Serve para enriquecer o registro e para o
    canário que prova que nível e cobertura são coisas diferentes; quem decide é `tem_edicao()`."""
    return str(nivel) == NIVEL_COM_EDICAO


def tem_edicao(resposta) -> bool:
    """True quando o acervo do Querido Diário tem ao menos uma edição do município. Função pura.

    Resposta ilegível não é `false`: quem chama trata a exceção e **preserva** o valor anterior, para
    que indisponibilidade da API nunca vire perda de cobertura."""
    if not isinstance(resposta, dict):
        raise ValueError("resposta do acervo não é um documento JSON")
    if "total_gazettes" not in resposta:
        raise ValueError("resposta do acervo sem `total_gazettes`")
    try:
        return int(resposta["total_gazettes"]) > 0
    except (TypeError, ValueError) as e:
        raise ValueError(f"`total_gazettes` ilegível: {resposta['total_gazettes']!r}") from e


def retrato(cidades: list, hoje: datetime.date) -> dict:
    """{ibge: {cobertura_qd, nivel_qd, data_teste}} a partir da lista do diretório. Função pura."""
    out = {}
    for c in cidades or []:
        ibge = str((c or {}).get("territory_id") or "").strip()
        if len(ibge) != 7 or not ibge.isdigit():
            continue
        nivel = str(c.get("level") or "").strip()
        out[ibge] = {"cobertura_qd": cobertura_do_nivel(nivel),
                     "nivel_qd": nivel,
                     "data_teste": hoje.isoformat()}
    return out


def mudancas(antes: dict, depois: dict) -> dict:
    """O que mudou de status, em cada direção, e quem o diretório não menciona.

    `passaram_a_indexado` é o que a editoria quer ver crescer: o Querido Diário adiciona cidades ao
    longo do tempo, e é essa a razão da rotina semanal."""
    a = {k: bool((v or {}).get("cobertura_qd")) for k, v in (antes or {}).items()}
    d = {k: bool((v or {}).get("cobertura_qd")) for k, v in (depois or {}).items()}
    return {
        "passaram_a_indexado": sorted(k for k in d if d[k] and not a.get(k, False)),
        "deixaram_de_ser_indexado": sorted(k for k in d if not d[k] and a.get(k, False)),
        "novos_no_diretorio": sorted(set(d) - set(a)),
        "ausentes_do_diretorio": sorted(set(a) - set(d)),
        "indexados_antes": sum(1 for v in a.values() if v),
        "indexados_depois": sum(1 for v in d.values() if v),
    }


def juntar(antes: dict, novo: dict) -> dict:
    """O retrato novo, preservando o registro de quem o diretório deixou de mencionar.

    Município que sai da resposta não é município que perdeu cobertura: pode ser mudança de formato
    da API. Ele fica com o valor anterior e um carimbo dizendo que o diretório não o mencionou —
    apagar o registro seria perder o histórico, e virá-lo para `false` seria inventar a perda."""
    out = dict(novo)
    for ibge, v in (antes or {}).items():
        if ibge in out:
            continue
        out[ibge] = {**(v or {}), "ausente_do_diretorio_em": novo and next(
            iter(novo.values()), {}).get("data_teste")}
    return out


def buscar_diretorio(abrir=None) -> list:
    """A lista de cidades do diretório. Os dois hosts, nesta ordem; erro se nenhum responder."""
    if abrir is None:
        from coletores_base import buscar

        def abrir(u):
            return buscar(u, timeout=90, origem="coletar_cobertura_qd")
    erros = []
    for url in DIRETORIOS:
        try:
            doc = json.loads(abrir(url))
        except Exception as e:  # noqa: BLE001
            erros.append(f"{url}: {type(e).__name__}")
            continue
        cidades = doc.get("cities") if isinstance(doc, dict) else doc
        if isinstance(cidades, list) and len(cidades) >= MINIMO_PLAUSIVEL:
            return cidades
        erros.append(f"{url}: resposta com {len(cidades or [])} cidades, abaixo do mínimo "
                     f"plausível de {MINIMO_PLAUSIVEL}")
    raise RuntimeError("o diretório do Querido Diário não respondeu: " + " · ".join(erros))


def varrer_acervo(ibges: list, antes: dict, hoje, abrir=None, niveis: dict = None,
                  ao_progredir=None, ao_salvar=None, lote: int = 100) -> tuple:
    """(retrato, falhas). Uma consulta ao acervo por município; `true` anterior não se reconsulta.

    Duas regras que valem mais que a velocidade. **Quem já está coberto fica coberto sem nova
    consulta** — edição indexada não desaparece, e reconsultar 500 municípios por semana para
    confirmar o que não muda gastaria a fonte de graça. **Falha não vira `false`**: o município
    mantém o valor anterior e entra na lista de falhas, com o carimbo antigo preservado, porque API
    fora do ar não é ausência de diário."""
    if abrir is None:
        from coletores_base import buscar

        def abrir(u):
            return buscar(u, timeout=20, origem="coletar_cobertura_qd")
    niveis = niveis or {}
    retrato_novo, falhas = {}, {}
    for i, ibge in enumerate(ibges):
        anterior = (antes or {}).get(ibge) or {}
        nivel = niveis.get(ibge, anterior.get("nivel_qd"))
        if anterior.get("cobertura_qd") is True:
            retrato_novo[ibge] = {**anterior, "nivel_qd": nivel}
            continue
        erro = None
        for molde in (GAZETAS, GAZETAS_ALT):
            try:
                coberto = tem_edicao(json.loads(abrir(molde.format(ibge=ibge))))
                retrato_novo[ibge] = {"cobertura_qd": coberto, "nivel_qd": nivel,
                                      "data_teste": hoje.isoformat()}
                erro = None
                break
            except Exception as e:  # noqa: BLE001
                erro = f"{type(e).__name__}"
        if erro:
            falhas[ibge] = erro
            retrato_novo[ibge] = {**anterior, "nivel_qd": nivel,
                                  "ultima_falha_em": hoje.isoformat(), "ultima_falha": erro}
        if (i + 1) % lote == 0:
            # Salva o que já se sabe. A primeira varredura rodou horas e travou sem escrever nada:
            # uma requisição pendurada apagou o trabalho de milhares de consultas. Progresso que só
            # existe na memória do processo não é progresso — é aposta.
            if ao_salvar:
                ao_salvar(retrato_novo, falhas)
            if ao_progredir:
                ao_progredir(i + 1, len(ibges), len(falhas))
    return retrato_novo, falhas


def autoteste() -> int:
    casos = []
    hoje = datetime.date(2026, 9, 30)

    casos.append(("nível 3 é coberto", cobertura_do_nivel("3") is True))
    casos.append(("nível 1 NÃO é coberto — diário cadastrado sem coleta não tem edição para ler",
                  cobertura_do_nivel("1") is False))
    casos.append(("nível 0 não é coberto", cobertura_do_nivel("0") is False))
    casos.append(("nível vazio não é coberto", cobertura_do_nivel("") is False))
    casos.append(("nível ausente não é coberto", cobertura_do_nivel(None) is False))

    cidades = [{"territory_id": "4100103", "territory_name": "Abatiá", "level": "0"},
               {"territory_id": "3205002", "territory_name": "Serra", "level": "3",
                "availability_date": "2023-01-01"},
               {"territory_id": "1100023", "territory_name": "Ariquemes", "level": "1"},
               {"territory_id": "abc", "level": "3"},
               {"territory_id": "123", "level": "3"},
               {}]
    r = retrato(cidades, hoje)
    casos.append(("o retrato tem um registro por município válido", len(r) == 3))
    casos.append(("código que não é IBGE de 7 dígitos fica de fora",
                  "abc" not in r and "123" not in r))
    casos.append(("Abatiá entra como não coberta, com o nível dito",
                  r["4100103"] == {"cobertura_qd": False, "nivel_qd": "0",
                                   "data_teste": "2026-09-30"}))
    casos.append(("o nível 1 fica gravado como 1, não achatado em 0",
                  r["1100023"]["nivel_qd"] == "1" and r["1100023"]["cobertura_qd"] is False))
    casos.append(("o município coletado entra como coberto",
                  r["3205002"]["cobertura_qd"] is True))
    casos.append(("todo registro leva a data da verificação",
                  all(v["data_teste"] == "2026-09-30" for v in r.values())))

    antes = {"4100103": {"cobertura_qd": False}, "3205002": {"cobertura_qd": True},
             "1100023": {"cobertura_qd": True}, "9999999": {"cobertura_qd": True}}
    m = mudancas(antes, r)
    casos.append(("quem perdeu o nível aparece como tal",
                  m["deixaram_de_ser_indexado"] == ["1100023"]))
    casos.append(("quem não mudou não aparece em nenhuma das listas",
                  "3205002" not in m["passaram_a_indexado"]
                  and "3205002" not in m["deixaram_de_ser_indexado"]))
    casos.append(("município fora da resposta vira 'ausente do diretório', não perda de cobertura",
                  m["ausentes_do_diretorio"] == ["9999999"]))
    m2 = mudancas({"3205002": {"cobertura_qd": False}}, r)
    casos.append(("quem passou a ser indexado aparece — é o que a rotina semanal existe para ver",
                  m2["passaram_a_indexado"] == ["3205002"]))
    casos.append(("a contagem de antes e depois sai junto",
                  (m["indexados_antes"], m["indexados_depois"]) == (3, 1)))

    j = juntar(antes, r)
    casos.append(("a união preserva quem o diretório não mencionou", "9999999" in j))
    casos.append(("e o marca como ausente, em vez de virá-lo para false",
                  j["9999999"]["cobertura_qd"] is True
                  and j["9999999"]["ausente_do_diretorio_em"] == "2026-09-30"))
    casos.append(("a união não perde nenhum município", len(j) == 4))

    # Trava: resposta curta ou quebrada não reescreve o país.
    for resposta, nome in (({"cities": []}, "lista vazia"),
                           ({"cities": [{"territory_id": "3205002", "level": "3"}]}, "uma cidade"),
                           ({}, "documento sem cidades")):
        try:
            buscar_diretorio(abrir=lambda u, r=resposta: json.dumps(r).encode())
            ok = False
        except RuntimeError:
            ok = True
        casos.append((f"resposta com {nome} NÃO reescreve a cobertura do país", ok))
    try:
        buscar_diretorio(abrir=lambda u: (_ for _ in ()).throw(OSError("sem rede")))
        ok = False
    except RuntimeError:
        ok = True
    casos.append(("falha de rede nos dois hosts levanta erro em vez de escrever retrato vazio", ok))
    grande = {"cities": [{"territory_id": str(4100103 + i), "level": "0"}
                         for i in range(MINIMO_PLAUSIVEL)]}
    casos.append(("resposta do tamanho do país é aceita",
                  len(buscar_diretorio(abrir=lambda u: json.dumps(grande).encode()))
                  == MINIMO_PLAUSIVEL))
    casos.append(("o segundo host entra quando o primeiro falha",
                  len(buscar_diretorio(abrir=lambda u: (json.dumps(grande).encode()
                                                        if "api.querido" in u
                                                        else (_ for _ in ()).throw(OSError()))))
                  == MINIMO_PLAUSIVEL))

    # --- o veredito é a edição, não o nível: foi isso que a conferência mostrou -------------------
    casos.append(("acervo com edição é cobertura", tem_edicao({"total_gazettes": 3426}) is True))
    casos.append(("acervo sem edição é ausência", tem_edicao({"total_gazettes": 0}) is False))
    for ruim in ({}, {"total_gazettes": "muitas"}, None, [], {"gazettes": []}):
        try:
            tem_edicao(ruim)
            ok = False
        except (ValueError, TypeError):
            ok = True
        casos.append((f"resposta ilegível ({ruim!r}) levanta erro em vez de virar ausência", ok))
    casos.append(("nível e cobertura são coisas diferentes: nível 0 com edição é COBERTO",
                  cobertura_do_nivel("0") is False and tem_edicao({"total_gazettes": 3471}) is True))

    hoje2 = datetime.date(2026, 9, 30)
    antes2 = {"1": {"cobertura_qd": True, "data_teste": "2026-09-09"},
              "2": {"cobertura_qd": False, "data_teste": "2026-09-09"},
              "3": {"cobertura_qd": False, "data_teste": "2026-09-09"}}
    pedidos = []

    def falso_abrir(u):
        pedidos.append(u)
        ibge = u.split("territory_ids=")[1].split("&")[0]
        return json.dumps({"total_gazettes": 7 if ibge == "2" else 0}).encode()

    r2, f2 = varrer_acervo(["1", "2", "3"], antes2, hoje2, abrir=falso_abrir)
    casos.append(("quem já está coberto NÃO é reconsultado",
                  not any("territory_ids=1&" in u for u in pedidos)))
    casos.append(("e continua coberto, com o carimbo antigo preservado",
                  r2["1"]["cobertura_qd"] is True and r2["1"]["data_teste"] == "2026-09-09"))
    casos.append(("quem passou a ter edição vira coberto, com o carimbo novo",
                  r2["2"]["cobertura_qd"] is True and r2["2"]["data_teste"] == "2026-09-30"))
    casos.append(("quem segue sem edição é reconsultado e recarimbado",
                  r2["3"]["cobertura_qd"] is False and r2["3"]["data_teste"] == "2026-09-30"))
    casos.append(("sem falhas, a lista de falhas é vazia", f2 == {}))

    r3, f3 = varrer_acervo(["2"], antes2, hoje2,
                           abrir=lambda u: (_ for _ in ()).throw(OSError("sem rede")))
    casos.append(("falha de consulta NÃO vira ausência: o valor anterior fica",
                  r3["2"]["cobertura_qd"] is False and r3["2"]["data_teste"] == "2026-09-09"))
    casos.append(("e a falha é registrada, com data", f3 == {"2": "OSError"}
                  and r3["2"]["ultima_falha_em"] == "2026-09-30"))
    r4, _ = varrer_acervo(["1"], {"1": {"cobertura_qd": True, "data_teste": "2026-09-09"}}, hoje2,
                          abrir=lambda u: (_ for _ in ()).throw(OSError()))
    casos.append(("coberto não se perde nem quando a API está fora do ar",
                  r4["1"]["cobertura_qd"] is True))
    casos.append(("o nível do diretório entra no registro sem decidir nada",
                  varrer_acervo(["3"], antes2, hoje2, abrir=falso_abrir,
                                niveis={"3": "1"})[0]["3"]["nivel_qd"] == "1"))

    casos.append(("o universo do país vem do arquivo com os 5.571, não dos 267 pontuáveis",
                  MUNICIPIOS.name == "verificacao_municipal.json"))
    casos.append((f"e o país real tem mais de {MINIMO_PLAUSIVEL} municípios no arquivo",
                  len(ibges_do_pais()) >= MINIMO_PLAUSIVEL))

    casos.append(("a governança diz que isto é existência de canal, não leitura",
                  "NÃO leitura" in GOVERNANCA and "sem menção" in GOVERNANCA))

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 0


def relatorio(m: dict, novo: dict, antes: dict) -> str:
    L = [f"Diretório do Querido Diário · {len(novo)} municípios no diretório",
         f"indexados antes: {m['indexados_antes']} · depois: {m['indexados_depois']}",
         f"passaram a indexado: {len(m['passaram_a_indexado'])}",
         f"deixaram de ser indexado: {len(m['deixaram_de_ser_indexado'])}",
         f"novos no diretório: {len(m['novos_no_diretorio'])}",
         f"ausentes do diretório: {len(m['ausentes_do_diretorio'])}"]
    ab = novo.get("4100103") or {}
    L.append(f"Abatiá/PR (4100103), conferida nominalmente: nível {ab.get('nivel_qd')!r}, "
             f"cobertura {ab.get('cobertura_qd')}, verificada em {ab.get('data_teste')}")
    return "\n".join(L)


def ibges_do_pais() -> list:
    """Os códigos dos 5.571 municípios, do arquivo canônico do próprio site."""
    d = json.loads(MUNICIPIOS.read_text(encoding="utf-8"))
    lista = d.get("municipios") if isinstance(d, dict) else d
    codigos = sorted({str(m["ibge"]).zfill(7) for m in lista if isinstance(m, dict) and m.get("ibge")})
    if len(codigos) < MINIMO_PLAUSIVEL:
        # Trava contra o erro que já aconteceu: com o arquivo errado como universo, a varredura
        # cobriu 267 municípios e declarou 5.304 ausentes do diretório. Universo curto não escreve.
        raise RuntimeError(f"{MUNICIPIOS.name} devolveu {len(codigos)} municípios, abaixo do mínimo "
                           f"plausível de {MINIMO_PLAUSIVEL} — universo errado, nada foi escrito")
    return codigos


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()

    from coletores_base import gravar_em, hoje_editorial
    hoje = hoje_editorial()
    doc = json.loads(SAIDA.read_text(encoding="utf-8")) if SAIDA.exists() else {}
    antes = doc.get("municipios") or {}

    # O diretório entra só para enriquecer o registro com o nível. Ele NÃO decide cobertura.
    niveis = {}
    try:
        niveis = {k: v.get("nivel_qd") for k, v in retrato(buscar_diretorio(), hoje).items()}
        print(f"diretório: {len(niveis)} municípios, usado só para o nível")
    except Exception as e:  # noqa: BLE001
        print(f"diretório indisponível ({type(e).__name__}); segue sem o nível")

    ibges = ibges_do_pais()
    reconsultar = [c for c in ibges if not ((antes.get(c) or {}).get("cobertura_qd") is True)]
    print(f"{len(ibges)} municípios · {len(ibges) - len(reconsultar)} já cobertos, não se "
          f"reconsultam · {len(reconsultar)} a consultar no acervo")

    def progresso(feitos, total, falhas):
        print(f"  {feitos}/{total} · falhas até aqui: {falhas}", flush=True)

    def salvar(parcial, falhas_ate_agora):
        """Grava o retrato parcial. Retomar é reler este arquivo: quem já está `true` não volta à
        fila, e quem não foi consultado ainda tem o valor antigo, com o carimbo antigo."""
        doc_p = dict(doc)
        doc_p["_governanca"] = GOVERNANCA
        doc_p["fonte"] = GAZETAS.format(ibge="<ibge>")
        doc_p["verificado_em"] = hoje.isoformat()
        doc_p["varredura_em_curso"] = True
        doc_p["municipios"] = juntar(antes, parcial)
        gravar_em(SAIDA, doc_p)          # §229

    limite = None
    if "--limite" in sys.argv:
        limite = int(sys.argv[sys.argv.index("--limite") + 1])
        ibges = [c for c in ibges if not ((antes.get(c) or {}).get("cobertura_qd") is True)][:limite]
        print(f"--limite {limite}: consultando {len(ibges)} municípios nesta rodada")

    novo, falhas = varrer_acervo(ibges, antes, hoje, niveis=niveis, ao_progredir=progresso,
                                 ao_salvar=salvar)
    m = mudancas(antes, novo)
    print(relatorio(m, novo, antes))
    print(f"falhas de consulta (valor anterior preservado): {len(falhas)}")

    if "--relatorio" in sys.argv:
        print("(--relatorio: nada foi escrito)")
        return 0

    doc["_governanca"] = GOVERNANCA
    doc["fonte"] = GAZETAS.format(ibge="<ibge>")
    doc["fonte_do_nivel"] = DIRETORIOS[0]
    doc["verificado_em"] = hoje.isoformat()
    doc["municipios"] = juntar(antes, novo)
    doc["varredura_em_curso"] = False
    doc["mudancas_na_ultima_verificacao"] = {
        "passaram_a_indexado": m["passaram_a_indexado"],
        "deixaram_de_ser_indexado": m["deixaram_de_ser_indexado"],
        "novos_no_diretorio": m["novos_no_diretorio"],
        "ausentes_do_diretorio": m["ausentes_do_diretorio"],
        "falhas_de_consulta": sorted(falhas)}
    gravar_em(SAIDA, doc)          # §229
    print(f"{SAIDA.relative_to(RAIZ)} regravado · {len(doc['municipios'])} municípios")
    return 0


if __name__ == "__main__":
    sys.exit(main())
