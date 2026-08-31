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

RAIZ = pathlib.Path(__file__).parent
DESTINO = RAIZ / "data" / "pistas_querido_diario.json"
API = "https://api.queridodiario.ok.org.br/gazettes"
TERMOS = ["plano de contingência", "PLANCON", "PLACON", "plano de enfrentamento",
          "protocolo de alerta e enfrentamento", "plano preventivo", "operação estiagem"]
JANELA_DESDE = "2026-01-01"  # ciclo 2026/2027; atos antigos vigentes ficam p/ busca dirigida
CAPITAIS = {"Rio Branco":"AC","Maceió":"AL","Manaus":"AM","Macapá":"AP","Salvador":"BA",
 "Fortaleza":"CE","Brasília":"DF","Vitória":"ES","Goiânia":"GO","São Luís":"MA","Cuiabá":"MT",
 "Campo Grande":"MS","Belo Horizonte":"MG","Belém":"PA","João Pessoa":"PB","Curitiba":"PR",
 "Recife":"PE","Teresina":"PI","Rio de Janeiro":"RJ","Natal":"RN","Porto Alegre":"RS",
 "Porto Velho":"RO","Boa Vista":"RR","Florianópolis":"SC","São Paulo":"SP","Aracaju":"SE","Palmas":"TO"}


def _get(params):
    """Requisição HTTP à API do Querido Diário com User-Agent identificado e tratamento de timeout."""
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "MonitorElNino/1.0 (monitorelnino.com.br)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


UFS_LAC = ["AL", "AP", "DF", "PA", "PB", "RN", "SE"]  # estados sem plano estadual nominal


def _lote(territorios, termo):
    """Consulta em lote: todos os códigos de uma UF numa chamada só."""
    return _get({"territory_ids": ",".join(territorios), "querystring": f'"{termo}"',
                 "published_since": JANELA_DESDE, "size": 20,
                 "excerpt_size": 300, "number_of_excerpts": 1})


def varrer_uf(uf, ref, pistas):
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
        r = _lote(terr, termo)
        time.sleep(1.1)
        for g in r.get("gazettes", []):
            t = g.get("territory_id")
            pistas.append({"nome": nomes.get(t, g.get("territory_name")), "uf": uf,
                           "codigo_ibge": t, "cobertura_qd": True, "escopo": "uf_completa",
                           "termo": termo, "data_diario": g.get("date"),
                           "edicao": g.get("edition"), "url_pdf": g.get("url"),
                           "excerto": (g.get("excerpts") or [""])[0][:400],
                           "status_triagem": "pendente_julgamento_humano"})


def rodar(alvos=None, ufs=None):
    """Varre as UFs (ou o modo --descobrir-termos, nacional) respeitando o intervalo de 1,1s entre requisições, e grava as pistas encontradas para revisão humana; nunca escreve no banco público."""
    ref = json.load(open(RAIZ / "data" / "municipios_ibge_referencia.json", encoding="utf-8"))
    cod = {(m["nome"], m["uf"]): f"{m['codigo_ibge']:07d}" for m in ref}
    alvos = alvos or [(n, u) for n, u in CAPITAIS.items()]
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
                pistas.append({"nome": nome, "uf": uf, "codigo_ibge": t, "cobertura_qd": True,
                               "termo": termo, "data_diario": g.get("date"),
                               "edicao": g.get("edition"), "url_pdf": g.get("url"),
                               "excerto": (g.get("excerpts") or [""])[0][:400],
                               "status_triagem": "pendente_julgamento_humano"})
    for uf in (ufs if ufs is not None else UFS_LAC):
        varrer_uf(uf, ref, pistas)
    execucao["ufs_varridas"] = ufs if ufs is not None else UFS_LAC
    json.dump({"execucao": execucao, "pistas": pistas},
              open(DESTINO, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n_cob = sum(1 for p in pistas if p.get("cobertura_qd"))
    print(f"✓ {len(pistas)} entradas ({n_cob} com cobertura) → {DESTINO.name} — triagem humana pendente")
    return 0


def main():
    """Interface de linha de comando: roda a varredura por UF(s) informada(s) ou, com --descobrir-termos, o modo de descoberta nacional de vocabulário."""
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
        json.dump({"execucao": time.strftime("%Y-%m-%d"), "sementes": sementes, "achados": achados},
                  open(RAIZ / "data" / "termos_candidatos_qd.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"OK {len(achados)} excertos nacionais colhidos -> termos_candidatos_qd.json (triagem humana)")
        return 0
    if "--uf" in sys.argv:
        uf = sys.argv[sys.argv.index("--uf") + 1].upper()
        return rodar(alvos=[], ufs=[uf])
    if "--check" in sys.argv:
        if not DESTINO.exists():
            print("(sem arquivo de pistas ainda — ok; roda na primeira execução em produção)")
            return 0
        d = json.load(open(DESTINO, encoding="utf-8"))
        assert "execucao" in d and "pistas" in d
        print(f"✓ pistas válidas — execução de {d['execucao']['data']}, {len(d['pistas'])} entradas")
        return 0
    return rodar()


if __name__ == "__main__":
    sys.exit(main())
