#!/usr/bin/env python3
"""Camada 2 automatizada: consulta a API pública do Querido Diário (OKBR) e gera
PISTAS para a fila humana — nunca escreve em municipios.json (R7).

Decisão editorial de 27/08/2026 (METODOLOGIA §4.1.1(d)(i)): integrada como
geradora de pistas. O conteúdo do QD é o texto integral dos diários oficiais
municipais (fonte primária, camada 2), chaveado por código IBGE e com URL
permanente do arquivo armazenado — mas a COBERTURA É PARCIAL (~centenas de
municípios, não 5.570): por isso o script testa a cobertura de cada município
ANTES de qualquer interpretação, e municípios sem cobertura são gravados como
`cobertura_qd: false` — ausência de resultado NUNCA é evidência negativa.

Regras herdadas: pista reativa as camadas 1-4; plano/capital exigem julgamento
humano; categoria de documento publicado cita edição e data do diário.

Uso:
  python3 consultar_querido_diario.py            # rotina completa: capitais + UFs LAC (padrão da Action)
  python3 consultar_querido_diario.py --uf PB    # varredura municipal de uma UF (lote por chamada)
  python3 consultar_querido_diario.py --check    # valida o arquivo de pistas existente
  python3 consultar_querido_diario.py --descobrir-termos   # mineração NACIONAL de denominações
      (sem filtro de território = corpus inteiro): sementes do ciclo -> excertos em
      data/termos_candidatos_qd.json p/ triagem humana do dicionário (§4.1.3-iii).

Rotina automatizada da bateria (decisão editorial de 27/08/2026): a cada
execução, além das capitais, varre TODOS os municípios das UFs sem plano
estadual (LAC) com consultas EM LOTE (territory_ids aceita lista separada por
vírgula → 1 chamada por UF×termo). A perna de busca aberta em motor (§4.1.2)
permanece agente-executada por sessão, com registro no Livro-Razão.

Cortesia de taxa: 60 req/min (referência da documentação) → pausa de 1,1s.
Contrato da API validado ao vivo em 27/08/2026 (schema: total_gazettes,
gazettes[{territory_id,date,url,territory_name,state_code,excerpts,edition,txt_url}]).
"""
import json, pathlib, sys, time, urllib.parse, urllib.request
import ssl

import funil
from coletores_base import preservar_evidencia, preservar_texto_integral, ua_de, gravar_em, hoje_editorial

RAIZ = pathlib.Path(__file__).parent
DESTINO = RAIZ / "data" / "pistas_querido_diario.json"
# 30/09/2026 (certificação dos coletores): `api.queridodiario.ok.org.br` recusa o handshake TLS
# (`SSLV3_ALERT_HANDSHAKE_FAILURE`) em parte das saídas, e era a única porta deste coletor — por
# isso ele falhava noite após noite. O mesmo acervo responde por `queridodiario.ok.org.br/api/...`,
# e `coletar_cobertura_qd.py` já usava as duas nesta ordem desde 30/09. Aqui vai a mesma ordem: a
# que responde vale; se nenhuma responder, o erro é real e sobe.
# 09/10/2026 (lote 2, A1-12): o host atual vem primeiro — `api.queridodiario.org.br`, o mesmo de
# `coletar_diarios_municipais.py` (o antigo responde 302 para ele). Os dois antigos ficam de reserva.
APIS = ("https://api.queridodiario.org.br/gazettes",
        "https://queridodiario.ok.org.br/api/gazettes",
        "https://api.queridodiario.ok.org.br/gazettes")
STATUS_DA_PISTA = "pista — na fila, aguardando busca dirigida e juiz"


def pista_da_gazeta(g: dict, nome: str, uf: str, ibge: str, termo: str, hash_evidencia=None,
                    hoje: str = None):
    """A pista que vai à porta da fila (`scripts/pistas.gravar_lote`), ou None. Função pura.

    09/10/2026 (lote 2, A1-12): o arquivo próprio do QD gravava `url_pdf`, `excerto`,
    `codigo_ibge` e `status_triagem` — chaves que o juiz não lê (`julgar_uma` usa `url`, `trecho` e
    `status`). A "primeira fila do juiz" nunca chegou ao juiz. Agora a gazeta vira pista no esquema,
    com o EXCERTO como `trecho`: é ele que recorta o ato de dentro da edição. Sem excerto ou sem URL,
    não há pista (a edição inteira não se julga)."""
    url = g.get("url") or g.get("txt_url")
    excertos = [e for e in (g.get("excerpts") or []) if str(e or "").strip()]
    if not url or not excertos:
        return None
    return {"municipio": nome, "uf": uf, "ibge": str(ibge).zfill(7), "url": url,
            "trecho": " ".join(str(excertos[0]).split())[:500],
            "titulo": f"Diário oficial de {nome}/{uf}, {g.get('date') or ''} — {termo}",
            "data_publicacao": g.get("date"), "origem": "querido_diario",
            "hash_evidencia": hash_evidencia, "status": STATUS_DA_PISTA,
            "data": hoje or hoje_editorial().isoformat(),
            "registrado_em": hoje or hoje_editorial().isoformat()}
TERMOS = ["plano de contingência", "PLANCON", "PLACON", "plano de enfrentamento",
          "protocolo de alerta e enfrentamento", "plano preventivo", "operação estiagem"]
JANELA_DESDE = "2026-01-01"  # ciclo 2026/2027; atos antigos vigentes ficam p/ busca dirigida
CAPITAIS = {"Rio Branco":"AC","Maceió":"AL","Manaus":"AM","Macapá":"AP","Salvador":"BA",
 "Fortaleza":"CE","Brasília":"DF","Vitória":"ES","Goiânia":"GO","São Luís":"MA","Cuiabá":"MT",
 "Campo Grande":"MS","Belo Horizonte":"MG","Belém":"PA","João Pessoa":"PB","Curitiba":"PR",
 "Recife":"PE","Teresina":"PI","Rio de Janeiro":"RJ","Natal":"RN","Porto Alegre":"RS",
 "Porto Velho":"RO","Boa Vista":"RR","Florianópolis":"SC","São Paulo":"SP","Aracaju":"SE","Palmas":"TO"}


def _get(params, apis=None):
    """Requisição à API do Querido Diário, tentando as portas conhecidas na ordem.

    Uma recusa de TLS numa das portas não é ausência de acervo: é uma porta fechada. Só quando
    todas fecham o erro sobe — e aí ele é real."""
    ultimo = None
    for base in (apis or APIS):
        url = base + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url,
                                     headers={"User-Agent": ua_de("consulta ao Querido Diário")})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except (urllib.error.URLError, ssl.SSLError, TimeoutError) as e:
            ultimo = e
            continue
    raise ultimo


UFS_LAC = ["AL", "AP", "DF", "PA", "PB", "RN", "SE"]  # estados sem plano estadual nominal



def _preservar_achado(g):
    """Evidência por achado (10/09/2026): grava o registro da edição retornado pela API
    (.json) e o texto integral (.txt) sob um hash próprio; devolve o hash para a pista.
    Best-effort: falha vira None e a pista segue valendo pelo excerto."""
    try:
        bruto = json.dumps(g, ensure_ascii=False, sort_keys=True).encode("utf-8")
        h = preservar_evidencia(bruto, g.get("url") or g.get("txt_url") or "", "json", "consultar_querido_diario")
        preservar_texto_integral(h, [g], "consultar_querido_diario")
        return h
    except Exception:  # noqa: BLE001
        return None


def _por_territorio(territorios, termo):
    """Um território por chamada, acumulando as gazetas. Substitui a consulta em lote.

    28/09/2026 (reativação decidida pela editoria): a consulta em lote — `territory_ids` com vírgulas —
    é a causa documentada da suspensão de 06/09/2026: ela devolveu **8.165 zeros uniformes** em 03/09, e
    o diagnóstico de resultado conhecido mostrou que um território por chamada devolve 3 diários e 3
    excertos onde o lote devolvia 0 (caso Cerrito/RS). Reativar o coletor sem consertar isto
    reproduziria o defeito, então a função mudou de nome junto com o comportamento: não existe mais um
    `_lote` a ser chamado por engano.
    """
    gazetas = []
    for t in territorios:
        r = _get({"territory_ids": t, "querystring": f'"{termo}"',
                  "published_since": JANELA_DESDE, "size": 5,
                  "excerpt_size": 300, "number_of_excerpts": 1})
        time.sleep(1.1)
        gazetas.extend(r.get("gazettes", []))
    return {"gazettes": gazetas}


def varrer_uf(uf, ref, pistas, para_fila=None):
    """Consulta a API do Querido Diário para uma UF, dentro de uma janela de datas, retornando os excertos que mencionam os termos de busca fornecidos."""
    nomes = {f"{m['codigo_ibge']:07d}": m["nome"] for m in ref if m["uf"] == uf}
    terr = sorted(nomes)
    base = _get({"territory_ids": ",".join(terr), "size": 1})
    time.sleep(1.1)
    if base.get("total_gazettes", 0) == 0:
        pistas.append({"uf": uf, "escopo": "uf_completa", "cobertura_qd": False,
                       "nota": f"nenhum dos {len(terr)} municípios de {uf} coberto no QD — ausência NÃO é evidência negativa"})
        return
    for termo in TERMOS:
        r = _por_territorio(terr, termo)
        for g in r.get("gazettes", []):
            t = g.get("territory_id")
            if para_fila is not None:
                para_fila.append(pista_da_gazeta(g, nomes.get(t, g.get("territory_name")), uf, t, termo))
            pistas.append({"nome": nomes.get(t, g.get("territory_name")), "uf": uf,
                           "codigo_ibge": t, "cobertura_qd": True, "escopo": "uf_completa",
                           "termo": termo, "data_diario": g.get("date"),
                           "edicao": g.get("edition"), "url_pdf": g.get("url"),
                           "excerto": (g.get("excerpts") or [""])[0][:400],
                           "hash_evidencia": _preservar_achado(g),
                           "status_triagem": "pendente_julgamento_humano"})


def rodar(alvos=None, ufs=None):
    """Varre as UFs (ou o modo --descobrir-termos, nacional) respeitando o intervalo de 1,1s entre requisições, e grava as pistas encontradas para revisão humana; nunca escreve no banco público."""
    ref = json.load(open(RAIZ / "data" / "municipios_ibge_referencia.json", encoding="utf-8"))
    cod = {(m["nome"], m["uf"]): f"{m['codigo_ibge']:07d}" for m in ref}
    alvos = alvos or [(n, u) for n, u in CAPITAIS.items()]
    para_fila = []
    pistas, execucao = [], {"data": time.strftime("%Y-%m-%d"), "janela_desde": JANELA_DESDE,
                            "termos": TERMOS, "alvos": len(alvos)}
    for nome, uf in alvos:
        t = cod[(nome, uf)]
        base = _get({"territory_ids": t, "size": 1})          # teste de cobertura
        time.sleep(1.1)
        coberto = base.get("total_gazettes", 0) > 0
        if not coberto:
            pistas.append({"nome": nome, "uf": uf, "codigo_ibge": t, "cobertura_qd": False,
                           "nota": "município sem cobertura no QD — ausência NÃO é evidência negativa"})
            continue
        for termo in TERMOS:
            r = _get({"territory_ids": t, "querystring": f'"{termo}"',
                      "published_since": JANELA_DESDE, "size": 5,
                      "excerpt_size": 300, "number_of_excerpts": 1})
            time.sleep(1.1)
            for g in r.get("gazettes", []):
                para_fila.append(pista_da_gazeta(g, nome, uf, t, termo))
                pistas.append({"nome": nome, "uf": uf, "codigo_ibge": t, "cobertura_qd": True,
                               "termo": termo, "data_diario": g.get("date"),
                               "edicao": g.get("edition"), "url_pdf": g.get("url"),
                               "excerto": (g.get("excerpts") or [""])[0][:400],
                               "hash_evidencia": _preservar_achado(g),
                               "status_triagem": "pendente_julgamento_humano"})
    for uf in (ufs if ufs is not None else UFS_LAC):
        varrer_uf(uf, ref, pistas, para_fila)
    execucao["ufs_varridas"] = ufs if ufs is not None else UFS_LAC
    gravar_em(DESTINO, {"execucao": execucao, "pistas": pistas})   # §229 — retrato da rodada
    # A fila do juiz recebe as pistas pela porta única, no esquema (A1-12).
    from scripts.pistas import gravar_lote
    balanco = gravar_lote([p for p in para_fila if p], origem="querido_diario")
    execucao["fila"] = {k: balanco.get(k) for k in ("gravadas", "recusadas")}
    print(f"  fila do juiz: {balanco.get('gravadas')} pista(s) gravada(s), "
          f"{balanco.get('recusadas')} recusada(s) pela porta {balanco.get('motivos') or ''}")
    n_cob = sum(1 for p in pistas if p.get("cobertura_qd"))
    # Item B do handover da auditoria do funil (27/09/2026): a rodada conta por etapa, para que
    # "está encontrando?" se responda sem abrir o código. Contagem não decide nada.
    funil.registrar("querido_diario", entradas=len(pistas), com_cobertura=n_cob,
                    ufs_varridas=len(execucao["ufs_varridas"]))
    print(f"✓ {len(pistas)} entradas ({n_cob} com cobertura) → {DESTINO.name} — triagem humana pendente")
    return 0


def fatia_do_cursor(alvos: list, inicio: int, limite: int) -> tuple:
    """(fatia, próximo início), dando a volta na lista. Função pura."""
    if not alvos or limite <= 0:
        return [], 0
    inicio %= len(alvos)
    fatia = [alvos[(inicio + i) % len(alvos)] for i in range(min(limite, len(alvos)))]
    return fatia, (inicio + len(fatia)) % len(alvos)


def autoteste() -> int:
    """Sem rede e sem escrita: a gazeta vira pista válida pela porta, e o cursor anda."""
    import sys as _s
    _s.path.insert(0, str(RAIZ))
    from scripts.pistas import normalizar, motivo_de_recusa
    import julgar_filas
    g = {"url": "https://data.queridodiario.ok.org.br/4301602/2026-07-10/a.pdf", "date": "2026-07-10",
         "excerpts": ["Fica instituído o Plano de Contingência de Proteção e Defesa Civil de Bagé"]}
    p = pista_da_gazeta(g, "Bagé", "RS", "4301602", "plano de contingência", hoje="2026-10-09")
    n = normalizar(p, "querido_diario")
    casos = [
        ("gazeta com excerto vira pista com url e trecho", p["url"] == g["url"] and "Plano" in p["trecho"]),
        ("a pista passa na porta da fila", motivo_de_recusa(n, []) == ""),
        ("o juiz a vê como pendente", julgar_filas.pendente(n)),
        ("gazeta sem excerto não vira pista", pista_da_gazeta({**g, "excerpts": []}, "Bagé", "RS", "4301602", "x", hoje="2026-10-09") is None),
        ("o host atual vem primeiro", APIS[0].startswith("https://api.queridodiario.org.br")),
        ("cursor anda e dá a volta", fatia_do_cursor(list(range(5)), 3, 4) == ([3, 4, 0, 1], 2)),
        ("cursor com lista vazia", fatia_do_cursor([], 7, 4) == ([], 0)),
    ]
    for nome, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {nome}")
    falhas = [c for c, ok in casos if not ok]
    print(f"{'X' if falhas else 'OK'} AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main():
    """Interface de linha de comando: roda a varredura por UF(s) informada(s) ou, com --descobrir-termos, o modo de descoberta nacional de vocabulário."""
    if "--autoteste" in sys.argv:
        return autoteste()
    if "--descobrir-termos" in sys.argv:
        sementes = ["plano de contingência El Niño", "plano de enfrentamento", "operação estiagem",
                    "plano emergencial estiagem", "protocolo calor extremo", "plano de ação climática contingência"]
        achados = []
        for sem in sementes:
            r = _get({"querystring": chr(34) + sem + chr(34), "published_since": JANELA_DESDE,
                      "size": 30, "excerpt_size": 200, "number_of_excerpts": 1})
            time.sleep(1.1)
            for g in r.get("gazettes", []):
                achados.append({"semente": sem, "territorio": g.get("territory_name"),
                                "uf": g.get("state_code"), "data": g.get("date"),
                                "url_pdf": g.get("url"), "excerto": (g.get("excerpts") or [""])[0][:250]})
        # §229 e §227: atômico, e a data da redação — `time.strftime` usa o relógio do
        # processo, que no runner é UTC.
        gravar_em(RAIZ / "data" / "termos_candidatos_qd.json",
                  {"execucao": hoje_editorial().isoformat(), "sementes": sementes, "achados": achados})
        print(f"OK {len(achados)} excertos nacionais colhidos -> termos_candidatos_qd.json (triagem humana)")
        return 0
    if "--alvos" in sys.argv:
        # 28/09/2026 (decisão da editoria, item 1): a primeira fila do juiz é uma LISTA DE ALVOS —
        # os municípios em que a varredura do diário reconheceu excerto e que não estão no banco nem em
        # fila nenhuma. Consulta-se cada um por termo de plano, e a pista sai com o excerto CERTO, que é
        # o que permite ao juiz recortar o ato de dentro da edição.
        caminho = pathlib.Path(sys.argv[sys.argv.index("--alvos") + 1])
        doc = json.load(open(caminho, encoding="utf-8"))
        alvos = [(a["nome"], a["uf"]) for a in doc.get("alvos", []) if a.get("nome") and a.get("uf")]
        limite = int(sys.argv[sys.argv.index("--limite") + 1]) if "--limite" in sys.argv else None
        if limite:
            # 09/10/2026 (lote 2, A1-12): cursor. `--limite 40` era sempre os 40 primeiros de 169.
            alvos, proximo = fatia_do_cursor(alvos, int(doc.get("proximo") or 0), limite)
            doc["proximo"] = proximo
            gravar_em(caminho, doc)
        print(f"fila de alvos: {len(alvos)} município(s) de {caminho.name}")
        return rodar(alvos=alvos)
    if "--uf" in sys.argv:
        uf = sys.argv[sys.argv.index("--uf") + 1].upper()
        return rodar(alvos=[], ufs=[uf])
    if "--check" in sys.argv:
        if not DESTINO.exists():
            print("(sem arquivo de pistas ainda — ok; roda na primeira execução em produção)")
            return 0
        d = json.load(open(DESTINO, encoding="utf-8"))
        assert "pistas" in d, "o arquivo de pistas precisa ter a lista `pistas`"
        if "execucao" not in d:
            # 28/09/2026: a fila foi reativada e ainda não houve consulta. Arquivo sem `execucao` é
            # estado legítimo — a fila existe, com governança escrita, esperando a primeira varredura.
            print(f"✓ fila reativada, sem execução ainda — {len(d['pistas'])} pista(s)")
            return 0
        print(f"✓ pistas válidas — execução de {d['execucao']['data']}, {len(d['pistas'])} entradas")
        return 0
    return rodar()


if __name__ == "__main__":
    sys.exit(main())
