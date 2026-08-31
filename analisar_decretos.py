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
  2. Em produção (Action, rede aberta), tenta obter o texto: (a) URL do registro;
     (b) Querido Diário por território × janela de ±5 dias da data do decreto;
  3. Varre o texto pelos dois dicionários e grava achados com trechos em
     data/decretos_conteudo_revisar.json (status: pendente_julgamento_humano).
Sem texto obtenível → 'texto_pendente' (a ausência fica registrada, nunca inferida).

Uso: python3 analisar_decretos.py [--check]
"""
import json, pathlib, re, sys, time, urllib.parse, urllib.request

RAIZ = pathlib.Path(__file__).parent
FILA = RAIZ / "data" / "decretos_conteudo_revisar.json"
QD = "https://api.queridodiario.ok.org.br/gazettes"
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
    """Consulta a API do Querido Diário para um excerto específico, reaproveitando o mesmo limitador de taxa do restante do pipeline."""
    url = QD + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "MonitorElNino/1.0 (monitorelnino.com.br)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


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
                for g in r.get("gazettes", []):
                    for ex in (g.get("excerpts") or []):
                        a, p, g, rf = _varrer(ex)
                        if a or p or g:
                            item["achados_alerta"] += a
                            item["achados_protetivos"] += p
                            item["achados_antecipatorios"] = sorted(set(item.get("achados_antecipatorios", []) + g))
                            item["marcadores_rota_federal"] = sorted(set(item.get("marcadores_rota_federal", []) + rf))
                            item["trechos"].append({"fonte": "QD " + (g.get("date") or ""),
                                                    "url": g.get("url"), "trecho": ex[:400]})
                if item["trechos"]:
                    item["situacao"] = "analisado"
                elif r.get("total_gazettes", 0) == 0:
                    item["situacao"] = "sem_cobertura_qd_na_data"
        except Exception as e:
            item["situacao"] = "erro_rede: " + str(e)[:80]
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
    json.dump({"execucao": time.strftime("%Y-%m-%d"), "regra": "marcador editorial apenas — NUNCA altera pontuação",
               "dicionario_alerta": ALERTA, "dicionario_protetivo": PROTETIVO, "fila": fila},
              open(FILA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
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
