#!/usr/bin/env python3
"""
buscar_protocolo_calor.py — a busca semanal do Protocolo Nacional de Calor Extremo no DOU
=========================================================================================
HANDOVER_SAUDE_10-10-2026, item 3.4. Em 16/09/2026 o Ministério da Saúde anunciou, em coletiva,
um "Protocolo Nacional de Calor Extremo" baseado no Painel Nacional de Excesso de Calor. Até
11/10/2026 o documento oficial não foi localizado (buscas registradas no robo-registro). O
handover pede que a busca seja REPROGRAMADA: uma vez por semana, com rastro.

O QUE ELE FAZ
  Consulta a busca do Diário Oficial da União (seção 1) na janela do ciclo, com termos do calor
  extremo, e guarda em `data/saude_desfechos/busca_protocolo_calor.json`:
    · cada consulta feita (termo, janela, quantos itens, janelas que não couberam);
    · os CANDIDATOS: ato do Ministério da Saúde cujo título ou excerto cita calor e protocolo,
      diretriz, plano, nota técnica ou portaria — tal como a fonte escreve;
    · o estado da semana: "nao_localizado" ou "candidatos_a_ler";
    · o histórico das buscas (só cresce).

O QUE ELE NÃO FAZ
  Não registra o protocolo como instrumento, não muda `saude_federal.json` nem o índice: um
  candidato é um ato a LER. Entrar ou não no MARÉ Saúde é decisão de método da editoria (item
  3.3). Excerto do DOU não é o ato.

TRAVAS
  1. Rede: `buscar` do coletores_base (cliente identificado, espera e nova tentativa).
  2. Formato: página sem a estrutura de resultados → lacuna declarada e NADA é sobrescrito
     (lista vazia afirmaria "não há", e o que houve foi leitura quebrada).
  3. Recorte: janela do DOU que não coube é declarada; nunca se apresenta recorte como varredura.

USO
  python3 buscar_protocolo_calor.py
  python3 buscar_protocolo_calor.py --autoteste      # sem rede e sem escrita
"""
from __future__ import annotations

import re
import sys
from datetime import date

from coletores_base import (buscar, ler, gravar, log_busca, registrar_lacuna, rodar_autoteste,
                            preservar_evidencia, varrer_busca_dou, FormatoDoDOUMudou,
                            hoje_editorial)

ARQUIVO = "saude_desfechos/busca_protocolo_calor.json"
INICIO_CICLO = date(2026, 6, 1)
TERMOS = ('"calor extremo"', '"excesso de calor"', '"onda de calor"')
_CALOR = re.compile(r"calor", re.I)
_TIPO = re.compile(r"protocolo|diretriz|plano|nota t[ée]cnica|portaria", re.I)
_SAUDE = re.compile(r"sa[úu]de", re.I)


def candidatos(itens: list) -> list:
    """Atos do Ministério da Saúde que citam calor e um tipo de instrumento. Função pura."""
    out, vistos = [], set()
    for it in itens or []:
        texto = f"{it.get('titulo') or ''} {it.get('trecho') or ''}"
        if not (_SAUDE.search(it.get("orgao") or "") and _CALOR.search(texto) and _TIPO.search(texto)):
            continue
        if it.get("url") in vistos:
            continue
        vistos.add(it.get("url"))
        out.append({k: it.get(k) for k in ("titulo", "url", "data", "orgao", "trecho")})
    return out


def montar(anterior: dict, consultas: list, achados: list, hoje: str) -> dict:
    """O arquivo novo a partir do anterior. O histórico só cresce. Função pura."""
    estado = "candidatos_a_ler" if achados else "nao_localizado"
    historico = list((anterior or {}).get("historico") or [])
    historico.append({"data": hoje, "estado": estado, "candidatos": len(achados),
                      "consultas": len(consultas)})
    return {
        "_governanca": ("Busca semanal do Protocolo Nacional de Calor Extremo (Ministério da Saúde) "
                        "no DOU, seção 1, desde 01/06/2026. Candidato é ato a LER, não instrumento "
                        "registrado; o excerto do DOU não é o ato. Peso zero: nunca lido pelo índice."),
        "fonte": "Diário Oficial da União — busca pública (in.gov.br)",
        "ultima_busca": hoje,
        "estado": estado,
        "consultas": consultas,
        "candidatos": achados,
        "historico": historico,
    }


def coletar() -> int:
    hoje_d = hoje_editorial()
    hoje = hoje_d.strftime("%d/%m/%Y")
    consultas, todos = [], []
    for termo in TERMOS:
        paginas = []

        def _buscar_pagina(u, _p=paginas):
            b = buscar(u, timeout=45, origem="buscar_protocolo_calor")
            _p.append((b, u))
            return b

        try:
            itens, faltando = varrer_busca_dou(termo, INICIO_CICLO, hoje_d, buscar_fn=_buscar_pagina)
        except FormatoDoDOUMudou as e:
            registrar_lacuna(f"DOU/protocolo de calor {termo}",
                             f"página sem a estrutura de resultados ({e}); arquivo anterior mantido",
                             canal="DOU", camada=1, strings=[termo])
            print(f"buscar_protocolo_calor: formato do DOU mudou em {termo} — nada sobrescrito")
            return 0
        except Exception as e:  # noqa: BLE001
            registrar_lacuna(f"DOU/protocolo de calor {termo}",
                             f"{type(e).__name__}; arquivo anterior mantido",
                             canal="DOU", camada=1, strings=[termo])
            print(f"buscar_protocolo_calor: {type(e).__name__} em {termo} — nada sobrescrito")
            return 0
        h = None
        for bruto, u in paginas:
            h = preservar_evidencia(bruto, u, "html", "buscar_protocolo_calor") or h
        consultas.append({"termo": termo, "de": INICIO_CICLO.isoformat(), "ate": hoje_d.isoformat(),
                          "itens": len(itens), "janelas_incompletas": faltando, "hash_evidencia": h})
        todos += itens
    achados = candidatos(todos)
    gravar(ARQUIVO, montar(ler(ARQUIVO, {}) or {}, consultas, achados, hoje))
    if not achados:
        log_busca("DOU", 1, list(TERMOS), "consultado sem achado",
                  resultados="nenhum ato do Ministério da Saúde com calor e protocolo/diretriz/plano")
    print(f"buscar_protocolo_calor: {len(todos)} itens lidos, {len(achados)} candidato(s) a ler")
    return 0


def autoteste() -> int:
    ms = "Ministério da Saúde/Gabinete do Ministro"
    itens = [
        {"titulo": "PORTARIA GM/MS Nº 1, institui o Protocolo Nacional de Calor Extremo",
         "url": "u1", "data": "01/10/2026", "orgao": ms, "trecho": "..."},
        {"titulo": "PORTARIA Nº 2", "url": "u2", "data": "02/10/2026",
         "orgao": "Ministério da Fazenda", "trecho": "protocolo de calor extremo"},
        {"titulo": "AVISO", "url": "u3", "data": "03/10/2026", "orgao": ms,
         "trecho": "onda de calor no estado"},
        {"titulo": "PORTARIA GM/MS Nº 1, institui o Protocolo Nacional de Calor Extremo",
         "url": "u1", "data": "01/10/2026", "orgao": ms, "trecho": "republicação"},
    ]

    def t1():  # só ato da Saúde que cita calor E um tipo de instrumento; repetido entra uma vez
        c = candidatos(itens)
        return [x["url"] for x in c] == ["u1"]

    def t2():  # sem candidato: estado "nao_localizado", nunca "não existe"
        a = montar({}, [{"termo": "x"}], [], "11/10/2026")
        return a["estado"] == "nao_localizado" and a["candidatos"] == [] and len(a["historico"]) == 1

    def t3():  # o histórico só cresce
        a = montar({"historico": [{"data": "04/10/2026"}]}, [], [{"url": "u1"}], "11/10/2026")
        return len(a["historico"]) == 2 and a["estado"] == "candidatos_a_ler"

    def t4():  # entrada malformada não quebra
        return candidatos(None) == [] and candidatos([{}]) == []

    return rodar_autoteste({
        "candidato: Saúde + calor + instrumento; repetido uma vez": t1,
        "sem candidato é 'nao_localizado'": t2,
        "histórico só cresce": t3,
        "malformado não quebra": t4,
    })


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(autoteste())
    sys.exit(coletar())
