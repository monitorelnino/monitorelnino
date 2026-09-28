#!/usr/bin/env python3
"""
monitorar_redes_oficiais.py
===========================
Camada 5 — perfis oficiais em redes sociais, **só descoberta**.

Decisão da editoria de 28/09/2026 (item 2): redes sociais são canal de descoberta aceitável, com três
condições que este coletor implementa e não pode afrouxar:

1. **Só perfil oficial**, verificado pelo domínio: o perfil entra apenas quando um domínio oficial do
   próprio ente (`*.gov.br`) **linka para ele**. Sem selo de API, sem lista de handles digitada à mão,
   sem inferência por nome parecido — se o site oficial não aponta o perfil, o perfil não existe para o
   Monitor.
2. **A pista exige documento primário em fonte oficial no juiz.** Post de rede social nunca passa a
   Etapa 0 do `juiz.py`: nenhum domínio de rede social está em `PADROES_FONTE_PROVAVEL_OFICIAL`. A
   pista vale para acionar o seguimento (§159, `seguir_pistas.py`), que procura o ato na fonte oficial.
3. **Rede social nunca é fonte de registro nem aparece como fonte no site.** O portão
   `scripts/verificar_rede_social_nao_e_fonte.py` reprova se um registro ou uma página pública citar
   domínio de rede social como fonte.

COMO ELE BUSCA, E POR QUE ASSIM
-------------------------------
Sem chave e sem produto pago (regra do repositório): a consulta vai pela instância efêmera do SearXNG
que a rodada já sobe, restrita ao perfil confirmado, com os termos de plano. Isso reusa **o mesmo
disjuntor por motor de origem** (`motores_busca.py`) e **os mesmos contadores** (`funil.py`) que a
editoria pediu — não há um segundo caminho de rede a manter.

O ALCANCE É DECLARADO, NÃO ESCONDIDO
------------------------------------
Só é possível confirmar perfil onde já conhecemos o domínio oficial: os 47 alvos estaduais com domínio
em `data/dominios_oficiais.json` e os 90 registros municipais com URL `.gov.br` em
`data/municipios.json`. Para os outros municípios o coletor **não gera pista** — e dizer isso é parte do
método: ausência de cobertura não é ausência de plano.

USO
  python3 monitorar_redes_oficiais.py --autoteste
  python3 monitorar_redes_oficiais.py --limite 20
"""
import json
import re
import sys
import time
import urllib.parse

import funil
import motores_busca
from coletores_base import (buscar, gravar, hoje_editorial, ler, log_busca, marcar_fonte_consultada,
                            registrar_lacuna, rodar_autoteste)
from monitorar_busca_web import buscar_searxng, espera_do_ritmo, sinal_de_limite_de_taxa

FONTE = "Perfis oficiais em redes sociais"
CAMADA = 5

# Domínios de rede social reconhecidos. Lista declarada: entrar num domínio novo é decisão registrada,
# não descoberta automática. NENHUM deles está nos padrões de fonte oficial do juiz — é o que garante
# que a pista não vira registro.
REDES = ("facebook.com", "instagram.com", "twitter.com", "x.com", "youtube.com", "threads.net",
         "bsky.app", "tiktok.com")
# Perfil, não post: o que se confirma é a conta institucional.
RE_PERFIL = re.compile(
    r"https?://(?:www\.|m\.)?(" + "|".join(re.escape(d) for d in REDES) + r")/(@?[A-Za-z0-9_.\-]{3,40})",
    re.I)
TERMOS = ("plano de contingência", "plano de enfrentamento", "período chuvoso", "estiagem",
          "defesa civil plano")
LIMITE_PADRAO = 20


def perfis_no_html(html: str) -> set:
    """Os perfis de rede social linkados numa página. Devolve {(rede, identificador, url)}.

    Descarta caminhos que não são perfil (`sharer`, `share`, `intent`, `watch`, `plugins`): link de
    compartilhamento aparece em quase toda página e não é conta institucional."""
    fora = {"sharer", "share", "intent", "watch", "plugins", "dialog", "hashtag", "search", "home",
            "login", "privacy", "policies", "help", "about"}
    achados = set()
    for m in RE_PERFIL.finditer(html or ""):
        rede, ident = m.group(1).lower(), m.group(2)
        if ident.strip("@").lower() in fora:
            continue
        achados.add((rede, ident, m.group(0)))
    return achados


def alvos_com_dominio(dominios: dict, municipios: list) -> list:
    """Os entes cujo domínio oficial conhecemos. [(rótulo, uf, dominio_url)].

    É aqui que o alcance fica explícito: quem não tem domínio oficial conhecido não entra."""
    alvos = []
    for chave, v in ((dominios or {}).get("alvos") or {}).items():
        if v.get("dominio"):
            alvos.append((f"{v.get('setor')}/{v.get('uf')}", v.get("uf"),
                          f"https://{v['dominio']}"))
    for m in municipios or []:
        url = str(m.get("url") or "")
        if ".gov.br" in url:
            alvos.append((f"{m.get('nome')}/{m.get('uf')}", m.get("uf"), url))
    return alvos


def consulta_do_perfil(rede: str, ident: str, termo: str) -> str:
    """A consulta restrita ao perfil confirmado. `site:` limita ao domínio; o identificador ao perfil."""
    return f'site:{rede} "{ident.strip("@")}" "{termo}"'


def montar_pista(rotulo: str, uf: str, rede: str, ident: str, url_perfil: str,
                 resultado: dict, confirmado_por: str) -> dict:
    """A pista, com a marca de que ela NÃO é fonte de registro."""
    nome = rotulo.split("/")[0]
    return {
        "municipio": nome, "uf": uf, "origem": "rede_social_oficial",
        "rede": rede, "perfil": ident, "url_perfil": url_perfil,
        "perfil_confirmado_por": confirmado_por,
        "url": resultado.get("url"),
        "titulo": (resultado.get("title") or "")[:300],
        "trecho": (resultado.get("content") or "")[:500],
        "data": hoje_editorial().strftime("%d/%m/%Y"),
        "registrado_em": hoje_editorial().isoformat(),
        "exige_documento_primario": True,
        "status": ("pista — rede social é canal de DESCOBERTA; promoção exige documento primário em "
                   "fonte oficial, julgado pelo juiz (§5.2.1). Nunca é fonte de registro."),
    }


def autoteste() -> int:
    def t_perfis_reconhece_as_redes():
        html = ('<a href="https://www.facebook.com/prefeituradebonito">f</a>'
                '<a href="https://instagram.com/defesacivilms">i</a>'
                '<a href="https://x.com/prefbonito">x</a>')
        achados = {(r, i) for r, i, _ in perfis_no_html(html)}
        return achados == {("facebook.com", "prefeituradebonito"), ("instagram.com", "defesacivilms"),
                           ("x.com", "prefbonito")}

    def t_descarta_link_de_compartilhamento():
        html = ('<a href="https://www.facebook.com/sharer/sharer.php?u=x">compartilhar</a>'
                '<a href="https://twitter.com/intent/tweet?url=x">tweetar</a>'
                '<a href="https://www.youtube.com/watch?v=abc">vídeo</a>')
        return perfis_no_html(html) == set()

    def t_pagina_sem_rede_devolve_vazio():
        return perfis_no_html("<a href='https://bonito.ms.gov.br/plano'>plano</a>") == set()

    def t_html_vazio_nao_estoura():
        return perfis_no_html("") == set() and perfis_no_html(None) == set()

    def t_alcance_declarado():
        """Só entra quem tem domínio oficial conhecido — e isso é o alcance, não um acidente."""
        dominios = {"alvos": {"MS/defesa_civil": {"uf": "MS", "setor": "defesa_civil",
                                                  "dominio": "defesacivil.ms.gov.br"},
                              "SP/saude": {"uf": "SP", "setor": "saude", "dominio": None}}}
        municipios = [{"nome": "Bonito", "uf": "MS", "url": "https://bonito.ms.gov.br/x"},
                      {"nome": "SemUrl", "uf": "SP", "url": None},
                      {"nome": "Imprensa", "uf": "SP", "url": "https://jornal.com.br/n"}]
        alvos = alvos_com_dominio(dominios, municipios)
        rotulos = {r for r, _, _ in alvos}
        return (rotulos == {"defesa_civil/MS", "Bonito/MS"}
                and all(".gov.br" in u for _, _, u in alvos))

    def t_consulta_restringe_ao_perfil():
        q = consulta_do_perfil("facebook.com", "@prefbonito", "plano de contingência")
        return q.startswith("site:facebook.com") and '"prefbonito"' in q and "@" not in q

    def t_nenhuma_rede_e_fonte_oficial_para_o_juiz():
        """A trava que sustenta a decisão: post de rede social não passa a Etapa 0 do juiz."""
        from juiz import PADROES_FONTE_PROVAVEL_OFICIAL as oficiais
        return not any(rede in p or p in rede for rede in REDES for p in oficiais)

    def t_pista_diz_que_nao_e_fonte_de_registro():
        p = montar_pista("Bonito/MS", "MS", "facebook.com", "prefbonito",
                         "https://facebook.com/prefbonito",
                         {"url": "https://facebook.com/prefbonito/posts/1", "title": "t", "content": "c"},
                         "https://bonito.ms.gov.br/x")
        return (p["exige_documento_primario"] is True and "DESCOBERTA" in p["status"]
                and "Nunca é fonte de registro" in p["status"]
                and p["perfil_confirmado_por"].endswith("/x") and p["origem"] == "rede_social_oficial")

    def t_pista_nao_traz_categoria_nem_decisao():
        p = montar_pista("Bonito/MS", "MS", "x.com", "p", "u", {"url": "u2"}, "c")
        return not any(k in p for k in ("categoria", "decisao", "promove", "fonte"))

    return rodar_autoteste({
        "reconhece perfil nas redes declaradas": t_perfis_reconhece_as_redes,
        "descarta link de compartilhamento, que não é perfil": t_descarta_link_de_compartilhamento,
        "página sem rede social devolve vazio": t_pagina_sem_rede_devolve_vazio,
        "HTML vazio ou nulo não estoura": t_html_vazio_nao_estoura,
        "alcance declarado: só ente com domínio oficial conhecido": t_alcance_declarado,
        "a consulta é restrita ao perfil confirmado": t_consulta_restringe_ao_perfil,
        "NENHUMA rede social é fonte oficial para o juiz": t_nenhuma_rede_e_fonte_oficial_para_o_juiz,
        "a pista diz que não é fonte de registro": t_pista_diz_que_nao_e_fonte_de_registro,
        "a pista não traz categoria nem decisão": t_pista_nao_traz_categoria_nem_decisao,
    })


def rodar(limite: int = LIMITE_PADRAO) -> int:
    dominios = ler("dominios_oficiais.json") or {}
    municipios = (ler("municipios.json") or {}).get("municipios") or []
    alvos = alvos_com_dominio(dominios, municipios)[:limite]
    print(f"{len(alvos)} ente(s) com domínio oficial conhecido nesta rodada "
          f"(alcance declarado: só onde o domínio é conhecido)")

    estado_motores = motores_busca.ler_estado()
    agora = motores_busca.agora_iso()
    motores = motores_busca.ativos(estado_motores, agora)
    if len(motores) < motores_busca.MINIMO_ATIVOS:
        print(f"✗ só {len(motores)} motor(es) ativo(s) — a rodada não pergunta de verdade")
        return 1

    pistas_doc = ler("pistas_imprensa.json") or {"pistas": []}
    vistos = {(p.get("url"), p.get("trecho")) for p in pistas_doc["pistas"]}
    n_perfis = n_pistas = n_sem_perfil = n_lacunas = 0

    for rotulo, uf, dominio in alvos:
        try:
            html = buscar(dominio)
            html = html.decode("utf-8", "replace") if isinstance(html, bytes) else str(html or "")
        except Exception as e:  # noqa: BLE001
            registrar_lacuna(f"{FONTE}/{rotulo}", f"{type(e).__name__}", canal="rede_social",
                             camada=CAMADA, uf=uf)
            n_lacunas += 1
            continue
        perfis = perfis_no_html(html)
        if not perfis:
            n_sem_perfil += 1
            log_busca("rede_social", CAMADA, [dominio], "consultado sem achado", uf=uf,
                      resultados="domínio oficial sem perfil de rede social linkado")
            continue
        n_perfis += len(perfis)
        for rede, ident, url_perfil in sorted(perfis):
            for termo in TERMOS:
                time.sleep(espera_do_ritmo(0))
                try:
                    dados = buscar_searxng(consulta_do_perfil(rede, ident, termo), motores=motores)
                except Exception:  # noqa: BLE001
                    for m in motores:
                        motores_busca.contabilizar(estado_motores, m, consultas=1, falhas=1)
                    continue
                fora = motores_busca.falhas_por_motor(dados)
                for m in motores:
                    motores_busca.contabilizar(estado_motores, m, consultas=1,
                                               falhas=1 if m in fora else 0)
                for r in (dados.get("results") or [])[:3]:
                    pista = montar_pista(rotulo, uf, rede, ident, url_perfil, r, dominio)
                    if (pista["url"], pista["trecho"]) in vistos:
                        continue
                    vistos.add((pista["url"], pista["trecho"]))
                    pistas_doc["pistas"].append(pista)
                    n_pistas += 1
        marcar_fonte_consultada([], FONTE, "nao_verificado",
                                resultado=f"{len(perfis)} perfil(is) oficial(is) confirmado(s)")

    gravar("pistas_imprensa.json", pistas_doc)
    estado_motores, caidos, motivos = motores_busca.aplicar_disjuntor(estado_motores, agora)
    gravar(motores_busca.ARQUIVO, estado_motores)
    funil.registrar("rede_social", entes_consultados=len(alvos), perfis_confirmados=n_perfis,
                    pistas=n_pistas, sem_perfil=n_sem_perfil, lacunas=n_lacunas)
    print(f"redes oficiais: {n_perfis} perfil(is) confirmado(s), {n_pistas} pista(s) nova(s), "
          f"{n_sem_perfil} domínio(s) sem perfil, {n_lacunas} lacuna(s)")
    if caidos:
        print(f"disjuntor: {len(caidos)} motor(es) desligado(s) — "
              + "; ".join(f"{m} ({motivos[m]})" for m in caidos))
    return 0


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(autoteste())
    lim = int(sys.argv[sys.argv.index("--limite") + 1]) if "--limite" in sys.argv else LIMITE_PADRAO
    sys.exit(rodar(lim))
