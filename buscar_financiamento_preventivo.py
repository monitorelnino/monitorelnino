#!/usr/bin/env python3
"""Bateria negativa de FINANCIAMENTO PREVENTIVO estadual (construída em 27/08/2026).

Objeto: instrumento normativo de transferência fundo a fundo condicionada a
preparação (o tipo Prepara RS/Resolução 008-FUNDEC-2026). Vocabulário de status
em data/financiamento_uf.json: "localizado" (norma citada + fonte),
"nao_verificado" (default; a NOTA não pode tratar como ausência) e
"ausente_verificado" (SOMENTE após bateria completa registrada em log).

Gabaritos por UF (executar em sessão de verificação ou produção com motor de
busca; cada execução grava em data/log_buscas.json):
  G1: fundo estadual de proteção e defesa civil {NOME_UF} resolução transferência fundo a fundo municípios
  G2: {SIGLA_FUNDO_SE_CONHECIDA} repasse municípios plano de contingência prevenção {ANO}
  G3: defesa civil {NOME_UF} programa estadual preparação repasse preventivo municípios
  G4: leitura direta da página de transferências do órgão estadual (quando existente)
Regra de promoção: "ausente_verificado" exige os 4 gabaritos executados e
registrados, com resultado negativo nos 4; qualquer achado positivo vira
"localizado" com norma e fonte primária. A regra espelha a bateria de planos
(§4.1.3) e herda suas garantias de abrangência.

Uso: --check valida estrutura e imprime o placar; --gabaritos UF imprime as
buscas prontas da UF para a sessão.
"""
import json, pathlib, sys

RAIZ = pathlib.Path(__file__).parent
NOMES = {"AC":"Acre","AL":"Alagoas","AP":"Amapá","AM":"Amazonas","BA":"Bahia","CE":"Ceará","DF":"Distrito Federal","ES":"Espírito Santo","GO":"Goiás","MA":"Maranhão","MT":"Mato Grosso","MS":"Mato Grosso do Sul","MG":"Minas Gerais","PA":"Pará","PB":"Paraíba","PR":"Paraná","PE":"Pernambuco","PI":"Piauí","RJ":"Rio de Janeiro","RN":"Rio Grande do Norte","RS":"Rio Grande do Sul","RO":"Rondônia","RR":"Roraima","SC":"Santa Catarina","SE":"Sergipe","SP":"São Paulo","TO":"Tocantins"}
VALIDOS = {"localizado", "nao_verificado", "ausente_verificado"}


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
    if "--gabaritos" in sys.argv:
        uf = sys.argv[sys.argv.index("--gabaritos") + 1].upper()
        print(f"Gabaritos de financiamento preventivo · {uf} ({NOMES[uf]}):")
        print(f"  G1: fundo estadual de proteção e defesa civil {NOMES[uf]} resolução transferência fundo a fundo municípios")
        print(f"  G2: fundo defesa civil {NOMES[uf]} repasse municípios plano de contingência prevenção 2026")
        print(f"  G3: defesa civil {NOMES[uf]} programa estadual preparação repasse preventivo municípios")
        print(f"  G4: página de transferências do órgão estadual de {NOMES[uf]}")
        return 0
    print(f"OK bateria de financiamento: {placar}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
