#!/usr/bin/env python3
"""
gerar_lai.py — pedidos de acesso à informação (doc de redesenho §12; decisão C13)
=================================================================================
Gera, sem rede:
  - docs/lai/<UF>_defesa_civil.txt  (27) — modelo do §12, adaptado a órgão e UF;
  - docs/lai/<UF>_saude.txt         (27) — variante saúde, às secretarias estaduais;
  - docs/lai/BR_carro_pipa_CMNE_MIDR.txt (1) — relação nominal da Operação Carro-Pipa (C13);
  - data/lai_pedidos.json — registro público (§3.7): uf, órgão, protocolo (null até o
    envio), data_envio, prazo legal (20 dias + 10 de prorrogação), resultado.

O ENVIO é humano (Fala.BR exige pessoa física identificada). O registro nasce
com `status: "a_enviar"`; quem envia preenche protocolo e data por
`--registrar --uf XX --tipo defesa_civil --protocolo NNN --data AAAA-MM-DD`.
A LAI não é suspensa pelo defeso; o prazo de 20 dias cai antes de 25/10 para
pedidos enviados até 05/10/2026.
"""
import json, os, pathlib, sys
from datetime import date, timedelta

RAIZ = pathlib.Path(__file__).parent
# 03/09/2026 (decisão editorial): pedidos e textos de LAI NUNCA no site nem no repositório público —
# saída no repositório privado (monitorelnino/robo-registro), variável LAI_DIR ou ../registro/notas/lai
SAIDA = pathlib.Path(os.environ.get("LAI_DIR", RAIZ.parent / "registro" / "notas" / "lai")) / "textos"
UF_NOME = {"AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá", "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal",
           "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão", "MG": "Minas Gerais", "MS": "Mato Grosso do Sul", "MT": "Mato Grosso",
           "PA": "Pará", "PB": "Paraíba", "PE": "Pernambuco", "PI": "Piauí", "PR": "Paraná", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
           "RO": "Rondônia", "RR": "Roraima", "RS": "Rio Grande do Sul", "SC": "Santa Catarina", "SE": "Sergipe", "SP": "São Paulo", "TO": "Tocantins"}
ASSINATURA = "Futura Evidence Lab — Monitor El Niño Brasil (monitorelnino.com.br)"

MODELO_DC = """À {orgao} ({uf})
Serviço de Informação ao Cidadão — pedido com fundamento na Lei nº 12.527/2011 (Lei de Acesso à Informação)

Com fundamento na Lei nº 12.527/2011, solicito ao órgão estadual de proteção e defesa civil de {nome} ({uf}):

(1) a relação dos municípios do estado que possuem Plano de Contingência de Proteção e Defesa Civil vigente para o ciclo El Niño 2026/2027 ou para o período chuvoso/seco 2026-2027, com número e data do ato que o institui e, quando disponível, o endereço eletrônico do documento;
(2) a relação dos municípios com plano em elaboração, com a data prevista de conclusão;
(3) o plano estadual de contingência vigente para o mesmo ciclo, com número, data e endereço eletrônico;
(4) a relação dos municípios cujos decretos de situação de emergência ou estado de calamidade pública foram homologados pelo estado desde 29/06/2026, com número e data.

Solicito resposta em formato aberto (CSV ou planilha). Informo que as respostas serão publicadas, com crédito ao órgão, no registro de transparência do Monitor El Niño Brasil, como fonte de nível estadual da verificação.

{assinatura}
Data do envio: ____/____/2026 · Protocolo: ________________
"""

MODELO_SAUDE = """À Secretaria de Estado da Saúde de {nome} ({uf})
Serviço de Informação ao Cidadão — pedido com fundamento na Lei nº 12.527/2011 (Lei de Acesso à Informação)

Com fundamento na Lei nº 12.527/2011, solicito à Secretaria de Estado da Saúde de {nome}:

(1) o plano estadual de contingência vigente para arboviroses e/ou ondas de calor e/ou emergências em saúde pública associadas ao El Niño 2026-2027, com número, data e endereço eletrônico do documento;
(2) a relação dos municípios com plano municipal de contingência correspondente, se a Secretaria a mantiver, com número e data do ato e, quando disponível, o endereço eletrônico;
(3) a indicação do órgão ou estrutura responsável (CIEVS, COE, sala de situação) e a data de sua ativação para o ciclo, se houver.

Solicito resposta em formato aberto (CSV ou planilha). As respostas serão publicadas, com crédito ao órgão, na página "Saúde e El Niño" do Monitor El Niño Brasil — registro de transparência sem peso no índice.

{assinatura}
Data do envio: ____/____/2026 · Protocolo: ________________
"""

MODELO_CARRO_PIPA = """Ao Comando Militar do Nordeste (Exército Brasileiro) e ao Ministério da Integração e do Desenvolvimento Regional (MIDR)
Serviço de Informação ao Cidadão — pedido com fundamento na Lei nº 12.527/2011 (Lei de Acesso à Informação)

Com fundamento na Lei nº 12.527/2011, solicito a relação NOMINAL dos municípios atendidos pela Operação Carro-Pipa (OCP) em 2026, por unidade da federação, com: data de inclusão no programa, número de carros-pipa e volume contratado por mês, e a base normativa da inclusão (portaria ou ato equivalente, com número e data). Solicito também a relação dos municípios cuja inclusão está condicionada a reconhecimento federal de situação de emergência, com a identificação do ato de reconhecimento.

Motivo: o portal do Exército bloqueou o acesso automatizado à relação em 02/09/2026 e o portal da Defesa Civil da Bahia estava fora do ar por período eleitoral; a lista nominal não é obtida por busca pública. Solicito resposta em formato aberto (CSV ou planilha). As respostas serão publicadas com crédito ao órgão no Monitor El Niño Brasil, como registro de transparência (programa permanente; sem crédito no índice nesta versão).

{assinatura}
Data do envio: ____/____/2026 · Protocolo: ________________
"""


def orgaos_dc():
    est = json.load(open(RAIZ / "data" / "estados.json", encoding="utf-8"))["ufs"]
    return {u["uf"]: (u.get("orgao") or f"Defesa Civil {u['uf']}") for u in est}


def gerar():
    SAIDA.mkdir(parents=True, exist_ok=True)
    dc = orgaos_dc(); pedidos = []
    for uf, nome in sorted(UF_NOME.items()):
        (SAIDA / f"{uf}_defesa_civil.txt").write_text(MODELO_DC.format(orgao=dc.get(uf, f"Defesa Civil {uf}"), uf=uf, nome=nome, assinatura=ASSINATURA), encoding="utf-8")
        (SAIDA / f"{uf}_saude.txt").write_text(MODELO_SAUDE.format(uf=uf, nome=nome, assinatura=ASSINATURA), encoding="utf-8")
        for tipo, org in (("defesa_civil", dc.get(uf, f"Defesa Civil {uf}")), ("saude", f"Secretaria de Estado da Saúde de {nome}")):
            pedidos.append({"uf": uf, "tipo": tipo, "orgao": org, "arquivo": f"docs/lai/{uf}_{tipo}.txt",
                            "status": "a_enviar", "protocolo": None, "data_envio": None, "prazo_legal": None,
                            "prorrogacao": None, "data_resposta": None, "resultado": None, "url_evidencia": None})
    (SAIDA / "BR_carro_pipa_CMNE_MIDR.txt").write_text(MODELO_CARRO_PIPA.format(assinatura=ASSINATURA), encoding="utf-8")
    pedidos.append({"uf": "BR", "tipo": "carro_pipa", "orgao": "Comando Militar do Nordeste / MIDR", "arquivo": "docs/lai/BR_carro_pipa_CMNE_MIDR.txt",
                    "status": "a_enviar", "protocolo": None, "data_envio": None, "prazo_legal": None, "prorrogacao": None,
                    "data_resposta": None, "resultado": None, "url_evidencia": None})
    reg = {"formato": "§3.7 do doc de redesenho 02/09/2026 — registro público dos pedidos de LAI do Monitor; "
                      "'a_enviar' = texto gerado, envio humano pendente (Fala.BR exige pessoa física identificada)",
           "gerado_em": date.today().isoformat(), "pedidos": pedidos}
    json.dump(reg, open(SAIDA.parent / "lai_pedidos.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"LAI: {len(pedidos)} pedidos gerados em docs/lai/ (27 defesa civil + 27 saúde + 1 Carro-Pipa); registro em data/lai_pedidos.json")


def registrar(uf, tipo, protocolo, data_envio):
    p = SAIDA.parent / "lai_pedidos.json"; reg = json.load(open(p, encoding="utf-8"))
    for it in reg["pedidos"]:
        if it["uf"] == uf and it["tipo"] == tipo:
            d = date.fromisoformat(data_envio)
            it.update({"status": "enviado", "protocolo": protocolo, "data_envio": data_envio,
                       "prazo_legal": (d + timedelta(days=20)).isoformat(), "prorrogacao": (d + timedelta(days=30)).isoformat(),
                       "resultado": "aguardando"})
            json.dump(reg, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1); print(f"registrado: {uf}/{tipo} protocolo {protocolo}"); return 0
    print("pedido não encontrado"); return 1


def autoteste():
    from coletores_base import rodar_autoteste
    def t1(): gerar(); return len(list(SAIDA.glob("*.txt"))) == 55
    def t2(): r = json.load(open(SAIDA.parent / "lai_pedidos.json", encoding="utf-8")); return len(r["pedidos"]) == 55 and all(p["protocolo"] is None for p in r["pedidos"])
    def t3(): return "12.527" in (SAIDA / "SC_defesa_civil.txt").read_text(encoding="utf-8") and "Santa Catarina" in (SAIDA / "SC_saude.txt").read_text(encoding="utf-8")
    return rodar_autoteste({"55 textos gerados": t1, "registro com 55 pedidos, protocolo null": t2, "texto cita a LAI e o estado": t3})


if __name__ == "__main__":
    if "--autoteste" in sys.argv: sys.exit(autoteste())
    if "--registrar" in sys.argv:
        a = sys.argv; sys.exit(registrar(a[a.index("--uf") + 1], a[a.index("--tipo") + 1], a[a.index("--protocolo") + 1], a[a.index("--data") + 1]))
    gerar()
