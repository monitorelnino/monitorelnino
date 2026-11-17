#!/usr/bin/env python3
"""Bateria negativa de FINANCIAMENTO PREVENTIVO estadual (construída em 27/08/2026).

Objeto: instrumento normativo de transferência fundo a fundo condicionada a
preparação (o tipo Prepara RS/Resolução 008-FUNDEC-2026). Vocabulário de status
em data/financiamento_uf.json: "localizado" (norma citada + fonte),
"nao_verificado" (default; a NOTA não pode tratar como ausência) e
"ausente_verificado" (SOMENTE após bateria completa registrada em log).

Quem verifica é a máquina (editoria, 08/10/2026: nenhuma etapa humana). Desde 27/08 a bateria
existia só como texto para uma sessão rodar à mão, e 26 das 27 UFs ficaram em "nao_verificado" por
dois meses e meio (achado do recorte do Ceará, 16/11/2026). `--rodar` executa as quatro consultas
pela porta do metabuscador, lê o documento oficial do estado e decide pela regra abaixo, no elo da
noite que já faz a busca estadual (`noturno_descoberta`).

Regra (na dúvida, não classifica):
  - "localizado": documento em domínio oficial da UF cujo texto traz, no mesmo trecho, ato normativo
    numerado, "fundo a fundo", finalidade preventiva (prevenção, preparação, preventivo) e "plano de
    contingência" como condição. Norma, condição e fonte saem do próprio texto; cópia preservada.
  - "ausente_verificado": as quatro consultas responderam e nenhum resultado em domínio oficial da UF
    fala de repasse fundo a fundo. Teto público: "não localizamos até o corte".
  - qualquer outro caso (motor sem resposta, documento que fala de fundo a fundo sem os quatro
    critérios): fica como está, com o motivo.

Uso: --check valida estrutura e imprime o placar; --rodar executa a bateria; --autoteste sem rede.
"""
import json, pathlib, re, sys

RAIZ = pathlib.Path(__file__).parent
NOMES = {"AC":"Acre","AL":"Alagoas","AP":"Amapá","AM":"Amazonas","BA":"Bahia","CE":"Ceará","DF":"Distrito Federal","ES":"Espírito Santo","GO":"Goiás","MA":"Maranhão","MT":"Mato Grosso","MS":"Mato Grosso do Sul","MG":"Minas Gerais","PA":"Pará","PB":"Paraíba","PR":"Paraná","PE":"Pernambuco","PI":"Piauí","RJ":"Rio de Janeiro","RN":"Rio Grande do Norte","RS":"Rio Grande do Sul","RO":"Rondônia","RR":"Roraima","SC":"Santa Catarina","SE":"Sergipe","SP":"São Paulo","TO":"Tocantins"}
VALIDOS = {"localizado", "nao_verificado", "ausente_verificado"}

DIAS_PARA_REVER = 30
CONSULTAS = (
    "fundo estadual de proteção e defesa civil {nome} resolução transferência fundo a fundo municípios",
    "fundo defesa civil {nome} repasse municípios plano de contingência prevenção {ano}",
    "defesa civil {nome} programa estadual preparação repasse preventivo municípios",
    "site:{sigla}.gov.br defesa civil transferência fundo a fundo municípios",
)
RE_NORMA = re.compile(r"(Resolu[çc][ãa]o|Lei|Decreto|Portaria)(?: Estadual| Complementar)?\s+n[º°o.]*\s*[\d][\d./-]*"
                      r"(?:[^\n]{0,40}?de\s+\d{1,2}\s+de\s+\w+\s+de\s+\d{4})?", re.I)
RE_PREVENTIVO = re.compile(r"preven[çc][ãa]o|preventiv|prepara[çc][ãa]o", re.I)


def oficial_da_uf(url: str, uf: str) -> bool:
    """Endereço em domínio do governo da UF (`<uf>.gov.br` e subdomínios). Função pura."""
    host = re.sub(r"^https?://", "", str(url or "")).split("/")[0].split(":")[0].lower()
    return host == f"{uf.lower()}.gov.br" or host.endswith(f".{uf.lower()}.gov.br")


def criterios(texto: str):
    """{norma, condicionalidade, trecho} quando um trecho de até 1.500 caracteres reúne os quatro
    critérios; None senão. Função pura."""
    t = re.sub(r"\s+", " ", texto or "")
    for m in re.finditer(r"fundo a fundo", t, re.I):
        trecho = t[max(0, m.start() - 750):m.end() + 750]
        norma = RE_NORMA.search(trecho)
        if norma and RE_PREVENTIVO.search(trecho) and re.search(r"plano de conting[êe]ncia", trecho, re.I):
            return {"norma": norma.group(0).strip(), "condicionalidade": "plano de contingência", "trecho": trecho}
    return None


def decidir(uf: str, respostas: list, ler_documento) -> dict:
    """Veredito da bateria para a UF. `respostas`: uma lista de resultados por consulta, ou None se a
    consulta falhou. `ler_documento(url) -> texto`. Função pura dado `ler_documento`."""
    if any(r is None for r in respostas):
        return {"mudou": False, "motivo": "metabuscador sem resposta em alguma consulta"}
    oficiais = []
    for r in respostas:
        for x in r:
            u = x.get("url") or ""
            if oficial_da_uf(u, uf) and u not in oficiais:
                oficiais.append(u)
    falam = []
    for u in oficiais[:12]:
        try:
            texto = ler_documento(u)
        except Exception:  # noqa: BLE001 — documento que não abre não decide nada
            continue
        if not re.search(r"fundo a fundo", texto or "", re.I):
            continue
        falam.append(u)
        c = criterios(texto)
        if c:
            return {"mudou": True, "status": "localizado", "instrumento": c["norma"], "norma": c["norma"],
                    "condicionalidade": c["condicionalidade"], "fonte": u, "trecho": c["trecho"][:600]}
    if falam:
        return {"mudou": False, "motivo": f"{len(falam)} documento(s) oficial(is) falam de fundo a fundo sem os quatro critérios"}
    return {"mudou": True, "status": "ausente_verificado"}


def a_rodar(fin: dict, hoje) -> list:
    """UFs sem veredito, ou com ausência verificada há mais de DIAS_PARA_REVER dias. Função pura."""
    import datetime as dt
    fora = []
    for uf, r in sorted(fin.items()):
        if r.get("status") == "nao_verificado":
            fora.append(uf)
        elif r.get("status") == "ausente_verificado":
            try:
                quando = dt.datetime.strptime(r.get("verificado_em") or "", "%d/%m/%Y").date()
            except ValueError:
                quando = None
            if not quando or (hoje - quando).days > DIAS_PARA_REVER:
                fora.append(uf)
    return fora


def rodar() -> int:
    import time
    import coletores_base as cb
    from monitorar_busca_web import buscar_searxng, espera_do_ritmo
    import motores_busca
    hoje = cb.hoje_editorial()
    fin = cb.ler("financiamento_uf.json", {})
    motores = list(motores_busca.MOTORES)

    def ler_documento(url):
        bruto = cb.buscar(url, timeout=60, origem="buscar_financiamento_preventivo")
        if bruto[:5] == b"%PDF-":
            from preservar_evidencias import extrair_texto_por_pagina
            return "\n".join(extrair_texto_por_pagina(bruto))
        return cb.texto_declarativo(cb.decodificar_pagina(bruto)[0])

    placar = {}
    for uf in a_rodar(fin, hoje):
        qs = [q.format(nome=NOMES[uf], sigla=uf.lower(), ano=hoje.year) for q in CONSULTAS]
        respostas = []
        for q in qs:
            time.sleep(espera_do_ritmo(0))
            try:
                respostas.append(buscar_searxng(q, motores=motores).get("results") or [])
            except Exception:  # noqa: BLE001
                respostas.append(None)
        v = decidir(uf, respostas, ler_documento)
        if v["mudou"]:
            novo = {k: v[k] for k in ("status", "instrumento", "norma", "condicionalidade", "fonte") if k in v}
            novo["verificado_em"] = hoje.strftime("%d/%m/%Y")
            if v["status"] == "localizado":
                novo["hash_evidencia"] = cb.preservar_evidencia(cb.buscar(v["fonte"], timeout=60), v["fonte"],
                                                                "pdf" if v["fonte"].lower().endswith(".pdf") else "html",
                                                                "buscar_financiamento_preventivo")
            fin[uf] = novo
        placar[v.get("status", "sem veredito")] = placar.get(v.get("status", "sem veredito"), 0) + 1
        cb.log_busca("busca_web", 4, qs, "registro" if v.get("status") == "localizado" else
                     ("consultado sem achado" if v.get("status") == "ausente_verificado" else "erro"),
                     uf=uf, nivel="estadual", resultados=f"financiamento preventivo: {v.get('status') or v.get('motivo')}")
    cb.gravar("financiamento_uf.json", fin)
    print(f"bateria de financiamento preventivo: {placar}")
    return 0


def autoteste() -> int:
    doc = ("Resolução nº 008/FUNDEC, de 12 de junho de 2026. Transferência fundo a fundo aos municípios para ações "
           "de preparação e prevenção, condicionada ao plano de contingência atualizado.")
    casos = [
        ("oficial da UF", oficial_da_uf("https://defesacivil.rs.gov.br/x", "RS") and not oficial_da_uf("https://rs.gov.br.evil.com", "RS")
         and not oficial_da_uf("https://gauchazh.com.br/x", "RS")),
        ("quatro critérios no mesmo trecho", (criterios(doc) or {}).get("norma", "").startswith("Resolução nº 008")),
        ("sem finalidade preventiva não conta", criterios(doc.replace("preparação e prevenção", "resposta")) is None),
        ("sem ato numerado não conta", criterios(doc.replace("Resolução nº 008/FUNDEC, de 12 de junho de 2026.", "")) is None),
        ("consulta que falhou não decide", decidir("RS", [[], None, [], []], lambda u: "")["mudou"] is False),
        ("quatro consultas sem documento oficial: ausência verificada",
         decidir("RS", [[{"url": "https://gauchazh.com.br/a"}], [], [], []], lambda u: "")["status"] == "ausente_verificado"),
        ("fundo a fundo sem os critérios: fica como está",
         decidir("RS", [[{"url": "https://defesacivil.rs.gov.br/a"}], [], [], []], lambda u: "repasse fundo a fundo")["mudou"] is False),
        ("documento com os critérios: localizado com norma e fonte",
         decidir("RS", [[{"url": "https://defesacivil.rs.gov.br/a"}], [], [], []], lambda u: doc)["fonte"] == "https://defesacivil.rs.gov.br/a"),
    ]
    import datetime as dt
    casos.append(("roda a não verificada e a ausência com mais de 30 dias",
                  a_rodar({"AC": {"status": "nao_verificado"}, "RS": {"status": "localizado"},
                           "SP": {"status": "ausente_verificado", "verificado_em": "01/09/2026"},
                           "RJ": {"status": "ausente_verificado", "verificado_em": "10/11/2026"}}, dt.date(2026, 11, 16)) == ["AC", "SP"]))
    falhas = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(("  ✓ " if ok else "  ✗ ") + n)
    print("✓ AUTOTESTE OK" if not falhas else f"✗ AUTOTESTE: {len(falhas)} falha(s)")
    return 1 if falhas else 0


def main():
    """Valida a estrutura de data/financiamento_uf.json (as 27 UFs, vocabulário de status válido, norma+fonte obrigatórias quando localizado) e, com --gabaritos UF, imprime as quatro buscas padronizadas daquela UF."""
    fin = json.load(open(RAIZ / "data" / "financiamento_uf.json", encoding="utf-8"))
    assert set(fin) == set(NOMES), "as 27 UFs são obrigatórias"
    for uf, r in fin.items():
        assert r["status"] in VALIDOS, uf
        if r["status"] == "localizado":
            assert r.get("norma") and r.get("fonte"), f"{uf}: localizado exige norma e fonte"
    placar = {}
    for r in fin.values():
        placar[r["status"]] = placar.get(r["status"], 0) + 1
    print(f"OK bateria de financiamento: {placar}")
    return 0


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else rodar() if "--rodar" in sys.argv else main())
