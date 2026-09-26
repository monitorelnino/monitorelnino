#!/usr/bin/env python3
"""Leitura de conteúdo dos decretos (METODOLOGIA §4.1.4) — dimensão incorporada
em 27/08/2026 a partir de achado editorial do Monitor do El Niño (Instituto
Talanoa / Política por Inteiro): decretos de emergência podem carregar
dispositivos de desregulação (dispensa de licenciamento, supressão de vegetação,
contratação sem licitação) ou conteúdo protetivo (abrigos, alertas, evacuação).

REGRA DE OURO: a leitura NUNCA altera a pontuação (decreto = 0 no MARÉ, sempre).
Ela produz um MARCADOR EDITORIAL por registro, e todo marcador passa pela fila
humana (R7) antes de ir ao público. Este script monta e alimenta a fila:
  1. Enumera os registros categoria 'decreto' do banco;
  2. Em produção (Action, rede aberta), obtém o texto pelo Querido Diário, por território e
     data do decreto. (Até 26/09/2026 esta linha prometia também tentar "(a) a URL do
     registro"; o código nunca teve essa perna, e prometer o que não se faz é pior do que
     declarar a lacuna — §230.)
  3. Varre o texto pelos dois dicionários e grava achados com trechos em
     data/decretos_conteudo_revisar.json (status: pendente_julgamento_humano).
Sem texto obtenível → 'texto_pendente' (a ausência fica registrada, nunca inferida).

Uso: python3 analisar_decretos.py [--check]
"""
import json, pathlib, re, sys, time, urllib.error, urllib.parse, urllib.request
from coletores_base import ua_de  # noqa: E402  (§228: um cliente só, com propósito)

RAIZ = pathlib.Path(__file__).parent
FILA = RAIZ / "data" / "decretos_conteudo_revisar.json"
# §230 (26/09/2026): era "https://api.queridodiario.ok.org.br/gazettes". Medido hoje com o
# cliente do projeto: esse host devolve SSLV3_ALERT_HANDSHAKE_FAILURE — não serve mais TLS.
# `coletar_diarios_municipais` migrou para o host vigente em 21/09 e ESTE arquivo ficou
# atrás; a fila registrava 59 dos 97 decretos como "erro_rede: SSLV3_...". Agora o endereço
# não é copiado: usa-se o consultor de lá, que já traz o host vigente E o de reserva.
from coletar_diarios_municipais import consultar_qd  # noqa: E402
from coletores_base import gravar_em, hoje_editorial  # noqa: E402  (§229, §227)
ALERTA = ["dispensa de licenciamento", "sem licenciamento", "supressão de vegetação",
          "supressão vegetal", "remoção de vegetação", "dispensa de licitação",
          "contratação direta", "dispensa de outorga"]
PROTETIVO = ["abrigo", "alerta antecipado", "evacuação", "distribuição de água",
             "brigada", "kit de emergência", "assistência humanitária"]
ANTECIPATORIO = ["iminente", "iminência", "desastre iminente", "previsão", "prognóstico",
                 "boletim", "antecipação", "preparação para", "el niño",
                 # limiares observacionais (refinamento slow-onset, 27/08/2026 §5.2.1):
                 "monitor de secas", "categoria de seca", "emergência hídrica",
                 "nível de alerta", "cemaden", "aviso meteorológico",
                 # família das chuvas (limiar observacional):
                 "aviso vermelho", "aviso laranja", "cota de alerta", "cota de inundação",
                 # frente de incêndio (limiar observacional):
                 "risco de fogo", "perigo de incêndio", "queimadas"]
ROTA_FEDERAL = ["fide", "reconhecimento federal", "s2id", "cobrade"]


def _qd(params):
    """Consulta a API do Querido Diário para um excerto específico.

    §230: delega a `coletar_diarios_municipais.consultar_qd`, que conhece o host vigente, cai no
    domínio de reserva quando a produção não responde e aplica a espera do §226. Manter aqui uma
    segunda URL foi exatamente o que deixou este arquivo cinco dias atrás do resto."""
    return json.loads(consultar_qd(urllib.parse.urlencode(params), timeout=60).decode("utf-8"))


def _varrer(texto):
    """Aplica os três dicionários (desregulação, proteção, antecipação) ao texto de um decreto e devolve os termos encontrados por categoria."""
    t = texto.lower()
    a = [x for x in ALERTA if x in t]
    p = [x for x in PROTETIVO if x in t]
    g = [x for x in ANTECIPATORIO if x in t]
    rf = [x for x in ROTA_FEDERAL if x in t]
    return a, p, g, rf


def rodar():
    """Lê os decretos do banco, aplica a varredura de dicionários a cada um e grava as marcações para revisão editorial; nunca altera a pontuação."""
    mun = json.load(open(RAIZ / "data" / "municipios.json", encoding="utf-8"))
    ref = json.load(open(RAIZ / "data" / "municipios_ibge_referencia.json", encoding="utf-8"))
    cod = {(m["nome"], m["uf"]): f"{m['codigo_ibge']:07d}" for m in ref}
    fila = []
    decs = [m for m in mun if m.get("categoria") == "decreto"]
    for m in decs:
        item = {"nome": m["nome"], "uf": m["uf"], "data": m.get("data"),
                "url": m.get("url"), "situacao": "texto_pendente",
                "achados_alerta": [], "achados_protetivos": [], "trechos": []}
        try:
            t = cod.get((m["nome"], m["uf"]))
            dt = m.get("data") or ""
            if t and re.match(r"\d{2}/\d{2}/\d{4}", dt):
                d, mo, y = dt.split("/")
                iso = f"{y}-{mo}-{d}"
                r = _qd({"territory_ids": t, "querystring": '"decreto"',
                         "published_since": iso, "published_until": iso,
                         "size": 3, "excerpt_size": 800, "number_of_excerpts": 3})
                time.sleep(1.1)
                # §230: aqui havia `a, p, g, rf = _varrer(ex)` DENTRO de `for g in gazettes` — a
                # gazeta era sobrescrita pela lista de termos antecipatórios, e duas linhas abaixo
                # `g.get("date")` era chamado sobre uma lista. AttributeError em todo excerto com
                # achado, engolido pelo `except` e gravado como "erro_rede: 'list' object has no
                # attribute 'get'": defeito nosso rotulado como falha da fonte, o que o CLAUDE.md
                # proíbe. O nome da variável de saída passa a ser `ant`.
                for gaz in r.get("gazettes", []):
                    for ex in (gaz.get("excerpts") or []):
                        a, prot, ant, rf = _varrer(ex)
                        if a or prot or ant:
                            item["achados_alerta"] += a
                            item["achados_protetivos"] += prot
                            item["achados_antecipatorios"] = sorted(set(item.get("achados_antecipatorios", []) + ant))
                            item["marcadores_rota_federal"] = sorted(set(item.get("marcadores_rota_federal", []) + rf))
                            item["trechos"].append({"fonte": "QD " + (gaz.get("date") or ""),
                                                    "url": gaz.get("url"), "trecho": ex[:400]})
                if item["trechos"]:
                    item["situacao"] = "analisado"
                elif r.get("total_gazettes", 0) == 0:
                    item["situacao"] = "sem_cobertura_qd_na_data"
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            item["situacao"] = "erro_rede: " + str(e)[:80]
        except Exception as e:  # noqa: BLE001
            # §230: o `except Exception` único rotulava QUALQUER falha como "erro_rede", inclusive
            # o AttributeError do defeito acima. Nomear a recusa errado é o erro que o projeto mais
            # persegue (§186, §187): quem lesse a fila concluiria que a fonte não respondeu.
            item["situacao"] = f"erro_interno: {type(e).__name__}: {e}"[:110]
        item["achados_alerta"] = sorted(set(item["achados_alerta"]))
        item["achados_protetivos"] = sorted(set(item["achados_protetivos"]))
        ga = item.get("achados_antecipatorios", [])
        rf = item.get("marcadores_rota_federal", [])
        if ga and not rf:
            item["classificacao_preliminar"] = "candidato_teste_objeto"   # possível ex-ante (§5.2.1) — julgamento humano
        elif ga and rf:
            item["classificacao_preliminar"] = "iminencia_com_rota_federal"  # subcategoria p/ revisão da fronteira na v2.3
        item["status_triagem"] = "pendente_julgamento_humano"
        fila.append(item)
    # §230: escrita atômica (§229) e data da REDAÇÃO (§227) — `time.strftime` usa o relógio local
    # do processo, que no runner é UTC, e esta é a data que a editoria lê como "quando a fila foi
    # montada". A escrita direta escapou do portão do §229 porque `json.dump(` e `open(` estavam
    # em linhas diferentes; o portão foi corrigido junto.
    gravar_em(FILA, {"execucao": hoje_editorial().isoformat(),
                     "regra": "marcador editorial apenas — NUNCA altera pontuação",
                     "dicionario_alerta": ALERTA, "dicionario_protetivo": PROTETIVO, "fila": fila})
    print(f"OK fila de conteúdo de decretos: {len(fila)} registros ({sum(1 for f in fila if f['situacao']=='analisado')} com texto analisado)")
    return 0


def main():
    """Ponto de entrada de linha de comando: executa rodar() ou, com --check, valida a integridade da estrutura de saída sem nova varredura."""
    if "--check" in sys.argv:
        if not FILA.exists():
            print("(fila ainda não gerada — roda na primeira execução em produção)"); return 0
        d = json.load(open(FILA, encoding="utf-8"))
        assert "fila" in d and "NUNCA altera pontuação" in d["regra"]
        print(f"OK fila válida — {len(d['fila'])} registros, execução {d['execucao']}"); return 0
    return rodar()


if __name__ == "__main__":
    sys.exit(main())
