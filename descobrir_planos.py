#!/usr/bin/env python3
"""Descoberta automática de planos de contingência/enfrentamento, via API WordPress dos
sítios oficiais — fonte 1 de 6 especificadas em INSTRUCOES_diarios_defeso_LAI_06-09-2026.md
§11 ("achar o plano de SC e todos os demais, sem verificação humana"), a primeira a
implementar. Estendido desde o início a saúde (handover "ponto cego saúde", 18/09/2026,
§3.4) — o mesmo documento que motivou este script (§11 é de 07/09/2026) só cobria defesa
civil; o caso Bahia (18/09) mostrou que saúde tem exatamente o mesmo ponto cego.

O QUE ESTE SCRIPT FAZ (100% máquina, por decisão editorial de 07/09/2026): descobrir a
URL de um PDF candidato, baixar, hashear, preservar como evidência. NUNCA decide sozinho
que um documento é um novo instrumento pontuável — isso é promoção (regra R7), sempre
humana, sempre pela fila. Ver TRAVA ABSOLUTA abaixo.

MECANISMO: API WordPress padrão (`/wp-json/wp/v2/posts?search=...` para notícias/atos, e
`/wp-json/wp/v2/media?search=...&mime_type=application/pdf` para PDFs anexados) — devolve
JSON com título, data e URL, sem raspagem de HTML. Muitos sítios estaduais são WordPress
(SC, SE, ES, PA, RJ, entre outros — §11); onde não é, a API simplesmente não responde como
esperado, e o alvo vira `documento_nao_lido` — perda de recall, nunca invenção.

===========================================================================
TRAVA ABSOLUTA (mesma trava de monitorar_imprensa_regional.py e monitorar_imprensa_saude.py)
— três camadas independentes, cada uma suficiente sozinha:
  1. ESTRUTURAL: nunca escreve em estados.json, saude_uf.json, municipios.json ou
     indice.json/monitor_saude.json (garantia verificada por self-test).
  2. DE CAMPO: todo achado nasce com "documento_oficial_confirmado": null e
     "promovivel": false — só um humano muda isso.
  3. DE PROCESSO: achados vão para data/pistas_descobertas.json (fila própria) e para
     data/evidencias.json (origem="descobrir_planos", via coletores_base.preservar_evidencia,
     que já é o índice único de evidência do projeto) — nunca direto no banco.
===========================================================================

DOMÍNIOS-ALVO: lista curada por UF/setor abaixo (DOMINIOS_CONHECIDOS) — alguns confirmados
nesta sessão (ex.: saude.ba.gov.br), a maioria ainda não verificada individualmente.
Declarado, não escondido: esta lista precisa de curadoria contínua; um domínio ausente ou
errado só reduz recall (o alvo não é buscado), nunca produz um resultado inventado.

REGRAS (§11): cliente identificado (coletores_base.UA); nunca mais de 1 requisição por
domínio a cada 2s (backoff simples — o universo por rodada é pequeno, um por domínio já
respeita "nunca mais de N/min"); toda URL descoberta vira item em data/evidencias.json;
sítio que recusa ou não responde = acesso_recusado (nunca 'nada localizado'); período
eleitoral detectado pelo cliente comum (coletores_base.buscar) = fonte suspensa (defeso).

Uso: python3 descobrir_planos.py [--limite N] [--setor saude|defesa_civil]
     python3 descobrir_planos.py --autoteste    (offline)
"""
import json
import re
import sys
import time
import urllib.parse

from coletores_base import (RAIZ, buscar, preservar_evidencia, ler, gravar,
                             rodar_autoteste, setor_da_url)

FILA = RAIZ / "data" / "pistas_descobertas.json"

# 18/09/2026: alguns domínios confirmados nesta sessão ou em rodadas anteriores; os demais
# são o padrão mais comum observado (saude.<uf>.gov.br / defesacivil.<uf>.gov.br) como
# primeira tentativa — precisa de curadoria contínua (ver docstring acima).
DOMINIOS_CONHECIDOS = {
    "saude": {
        "BA": "saude.ba.gov.br",
        "SC": "saude.sc.gov.br",
        "PR": "saude.pr.gov.br",
        "RO": "sesau.ro.gov.br",
    },
    "defesa_civil": {
        "SC": "defesacivil.sc.gov.br",   # §11: robô recusado nas rodadas de 07/09/2026 — mantido para nova tentativa
        "SE": "defesacivil.se.gov.br",   # §11: idem
    },
}

UFS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
       "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]

TERMOS_BUSCA = {
    "saude": ["plano de ações de saúde", "plano estadual de enfrentamento", "plano de contingência arboviroses"],
    "defesa_civil": ["plano de contingência", "PLANCON", "plano de enfrentamento"],
}


def dominio_para(uf: str, setor: str) -> str:
    """Domínio conhecido, ou o padrão mais comum como primeira tentativa (§11: declarado,
    não escondido — precisa de curadoria; um palpite errado só perde recall)."""
    conhecido = DOMINIOS_CONHECIDOS.get(setor, {}).get(uf)
    if conhecido:
        return conhecido
    prefixo = "saude" if setor == "saude" else "defesacivil"
    return f"{prefixo}.{uf.lower()}.gov.br"


def consultar_wp_json(dominio: str, termo: str) -> list:
    """Consulta /wp-json/wp/v2/media (PDFs) do domínio. Devolve [] em qualquer falha
    (site fora do ar, não é WordPress, API desabilitada) — nunca levanta exceção."""
    q = urllib.parse.quote(termo)
    url = f"https://{dominio}/wp-json/wp/v2/media?search={q}&mime_type=application/pdf&per_page=10"
    try:
        corpo = buscar(url, timeout=30)
        dados = json.loads(corpo)
        if not isinstance(dados, list):
            return []
        achados = []
        for item in dados:
            src = (item.get("source_url") or "").strip()
            titulo = ((item.get("title") or {}).get("rendered") or "").strip()
            data_pub = (item.get("date") or "").strip()
            if src.lower().endswith(".pdf"):
                achados.append({"url": src, "titulo": titulo, "data_publicacao": data_pub})
        return achados
    except Exception as e:  # noqa: BLE001 — tolerante por design (ver docstring)
        print(f"[aviso] {dominio}: {type(e).__name__} ({e})")
        return []


def _hash_pista(p: dict) -> str:
    import hashlib
    return hashlib.sha256(f"{p['uf']}|{p['setor']}|{p['url']}".encode()).hexdigest()[:16]


def carregar_fila():
    return ler("pistas_descobertas.json", {"_governanca": (
        "Fila de DESCOBERTA automática (via API WordPress, §11) para triagem humana. "
        "TRAVA ABSOLUTA: nenhum item entra no banco (estados.json/saude_uf.json/"
        "municipios.json/indice.json/monitor_saude.json) sem confirmação humana do "
        "documento primário, pelo fluxo manual normal (promoção = regra R7). Criado "
        "18/09/2026 (handover ponto cego saúde, §3.4; especificado em "
        "INSTRUCOES_diarios_defeso_LAI_06-09-2026.md §11)."),
        "itens": []})


def registrar(fila: dict, achados: list) -> list:
    vistos = {i["hash"] for i in fila["itens"]}
    ineditos = []
    for a in achados:
        a["hash"] = _hash_pista(a)
        if a["hash"] in vistos:
            continue
        a["documento_oficial_confirmado"] = None
        a["promovivel"] = False
        a["status"] = "pendente_confirmacao_documento"
        a["descoberto_em"] = time.strftime("%Y-%m-%d")
        fila["itens"].append(a)
        vistos.add(a["hash"])
        ineditos.append(a)
    return ineditos


def descobrir(uf: str, setor: str, fila: dict) -> list:
    """Consulta um alvo (UF + setor), preserva PDFs achados como evidência, registra na fila.
    Nunca levanta — falha vira `[]` (documento_nao_lido / acesso_recusado, sem distinção
    fina nesta primeira versão; o hash_evidencia ausente já sinaliza 'não lido' a jusante)."""
    dominio = dominio_para(uf, setor)
    achados_brutos = []
    for termo in TERMOS_BUSCA[setor][:2]:   # 2 termos por alvo, mesma disciplina de custo dos monitores de imprensa
        achados_brutos.extend(consultar_wp_json(dominio, termo))
        time.sleep(2.0)   # backoff: nunca mais de 1 req/2s por domínio (§11)
    achados = []
    for a in achados_brutos:
        item = {"uf": uf, "setor": setor, "url": a["url"], "titulo": a["titulo"],
                "data_publicacao": a["data_publicacao"], "dominio": dominio, "hash_evidencia": None}
        try:
            pdf = buscar(a["url"], timeout=40)
            item["hash_evidencia"] = preservar_evidencia(pdf, a["url"], "pdf", "descobrir_planos")
        except Exception as e:  # noqa: BLE001
            item["status_leitura"] = f"acesso_recusado ({type(e).__name__})"
        achados.append(item)
    novos = registrar(fila, achados)
    return novos


def autoteste() -> int:
    def t_dominio_conhecido():
        return dominio_para("BA", "saude") == "saude.ba.gov.br"

    def t_dominio_padrao():
        return dominio_para("XX", "saude") == "saude.xx.gov.br" and dominio_para("XX", "defesa_civil") == "defesacivil.xx.gov.br"

    def t_wp_json_parse():
        # fixture: resposta típica da API WordPress /wp-json/wp/v2/media
        fx = json.dumps([
            {"source_url": "https://saude.xx.gov.br/wp-content/uploads/2026/plano.pdf",
             "title": {"rendered": "Plano de Ações de Saúde 2026"}, "date": "2026-08-15T10:00:00"},
            {"source_url": "https://saude.xx.gov.br/imagem.png",
             "title": {"rendered": "não é PDF"}, "date": "2026-08-15T10:00:00"},
        ])
        import unittest.mock as mock
        with mock.patch(f"{__name__}.buscar", return_value=fx.encode()):
            achados = consultar_wp_json("saude.xx.gov.br", "plano")
        return len(achados) == 1 and achados[0]["url"].endswith(".pdf")

    def t_wp_json_tolerante_a_falha():
        import unittest.mock as mock
        with mock.patch(f"{__name__}.buscar", side_effect=RuntimeError("timeout")):
            achados = consultar_wp_json("naoexiste.xx.gov.br", "plano")
        return achados == []

    def t_dedup_e_trava():
        fila = {"_governanca": "x", "itens": []}
        item = {"uf": "XX", "setor": "saude", "url": "https://x.pdf", "titulo": "t", "data_publicacao": "", "dominio": "x", "hash_evidencia": None}
        a = registrar(fila, [dict(item)])
        b = registrar(fila, [dict(item)])
        if not (len(a) == 1 and len(b) == 0):
            return False
        i = fila["itens"][0]
        return i["documento_oficial_confirmado"] is None and i["promovivel"] is False and i["status"] == "pendente_confirmacao_documento"

    def t_trava_estrutural():
        fonte = (RAIZ / "descobrir_planos.py").read_text(encoding="utf-8")
        for proibido in ["estados.json", "saude_uf.json", "municipios.json", "indice.json", "monitor_saude.json"]:
            for _ in re.finditer(r'open\([^)]*' + re.escape(proibido) + r'[^)]*,\s*["\']([wa])', fonte):
                return False
            for _ in re.finditer(r'json\.dump\([^,]*,\s*open\([^)]*' + re.escape(proibido), fonte):
                return False
        return True

    return rodar_autoteste({
        "domínio conhecido (BA/saúde)": t_dominio_conhecido,
        "domínio padrão (fallback declarado)": t_dominio_padrao,
        "wp-json: extrai só PDFs, com título e data": t_wp_json_parse,
        "wp-json: falha de rede vira lista vazia, nunca exceção": t_wp_json_tolerante_a_falha,
        "dedup por hash + trava absoluta (campos de nascença)": t_dedup_e_trava,
        "garantia estrutural: nunca escreve nos bancos": t_trava_estrutural,
    })


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()

    limite = 10
    if "--limite" in sys.argv:
        limite = int(sys.argv[sys.argv.index("--limite") + 1])
    setores = ["saude", "defesa_civil"]
    if "--setor" in sys.argv:
        setores = [sys.argv[sys.argv.index("--setor") + 1]]

    fila = carregar_fila()
    total_novos = 0
    consultas = 0
    for setor in setores:
        for uf in UFS:
            if consultas >= limite:
                break
            novos = descobrir(uf, setor, fila)
            total_novos += len(novos)
            consultas += 1
        if consultas >= limite:
            break

    gravar("pistas_descobertas.json", fila)
    print(f"Descoberta via wp-json: {consultas} alvo(s) consultado(s) ({'/'.join(setores)}).")
    if total_novos:
        print(f"[ACHADOS NOVOS] {total_novos} para triagem humana (status pendente_confirmacao_documento):")
        for p in fila["itens"][-total_novos:]:
            print(f"  · [{p['uf']}/{p['setor']}] {p['titulo'][:80] or p['url']}")
        print("  → NENHUM foi confirmado nem é promovível — trava absoluta. Ver data/pistas_descobertas.json.")
    else:
        print(f"Nenhum achado inédito (fila com {len(fila['itens'])} itens acumulados).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
