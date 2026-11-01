#!/usr/bin/env python3
"""Projeção de mortalidade por calor do Climate Impact Lab (El Niño Heat Mortality Tracker), por ADM1.

Coluna 1 do quadro de mortalidade comparada (HANDOVER_MORTALIDADE_COMPARADA_30-10-2026 §6; decisão da
editoria, 30/10: "não precisa autorização, basta citar"). Crédito em toda exibição: "Climate Impact
Lab, El Niño Heat Mortality Tracker, edição de <mês/ano>; método: Carleton et al. (2022), QJE
137(4):2037–2105".

COMO A EDIÇÃO É ACHADA
----------------------
O mapa do Tracker lê um CSV por ADM1 cujo nome carrega a edição
(`/uploads/AAAA/MM/v<aammdd>_adm1_output_BASE_rounded_cust.csv`, sonda da janela D, 30/10). O nome
muda a cada mês, então ele nunca é montado: é LIDO da página. Se o link não está no HTML que a
página serve (o mapa pode carregá-lo por script), a coleta declara a lacuna e para: abrir navegador
no elo da noite é decisão à parte, e ler o que não está na página seria adivinhar.

O QUE É GUARDADO, E O QUE NÃO É
-------------------------------
Cada edição entra uma vez, datada, sem sobrescrever a anterior: edição, data da consulta, URL, hash
e tamanho do CSV, cabeçalho e as linhas do Brasil EXATAMENTE como vieram. Os nomes das colunas e a
faixa de incerteza ainda não foram lidos por nós; este coletor não os interpreta. Quem monta UF × mês
(`gerar_mortalidade_comparada.py`, A2) lê o cabeçalho guardado, e o que a fonte não trouxer vira
lacuna declarada, sem escolha nossa. Mesmo hash = nada a gravar (idempotente).

PESO ZERO
---------
Como todo o MARÉ Saúde: projeção de modelo, declarada como tal; sem nota, sem faixa, sem atribuição.

USO
  python3 coletar_projecao_cil.py --autoteste
  python3 coletar_projecao_cil.py
"""
import csv
import datetime
import hashlib
import io
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

PAGINA = "https://impactlab.org/el-nino-heat-mortality-tracker/"
SAIDA = "saude_desfechos/projecao_cil.json"
LIMITE_LINHAS_BRASIL = 5000
CREDITO = ("Climate Impact Lab, El Niño Heat Mortality Tracker; método: Carleton et al. (2022), "
           "QJE 137(4):2037–2105")
RESSALVA = ("Projeção de modelo, não contagem de óbitos. A edição, o cenário e a linha de base são os "
            "do arquivo da fonte; este arquivo guarda as linhas do Brasil como vieram, sem "
            "reinterpretar colunas.")
_LINK = re.compile(r"https?://[^\"'\s<>\\]+/uploads/\d{4}/\d{2}/v(\d{6})_adm1_output_[A-Za-z0-9_]+\.csv"
                   r"(?:\?[^\"'\s<>\\]*)?")
_BRASIL = {"BRA", "BRAZIL", "BRASIL"}


def achar_csv(html: str):
    """(url, 'AAAA-MM-DD') do CSV por ADM1 que a página declara, ou None. Função pura."""
    texto = html.replace("\\/", "/").replace("&amp;", "&")
    for m in _LINK.finditer(texto):
        try:
            d = datetime.datetime.strptime(m.group(1), "%y%m%d").date()
        except ValueError:
            continue
        return m.group(0), d.isoformat()
    return None


def _e_brasil(celula: str) -> bool:
    c = celula.strip().upper()
    return c in _BRASIL or c.startswith(("BRA.", "BRA_"))


def linhas_do_brasil(texto_csv: str):
    """(cabeçalho, linhas do Brasil, total de linhas) — as linhas inteiras, como vieram."""
    leitor = csv.reader(io.StringIO(texto_csv))
    cabecalho = next(leitor, [])
    total, brasil = 0, []
    for linha in leitor:
        if not linha:
            continue
        total += 1
        if any(_e_brasil(c) for c in linha):
            brasil.append(linha)
    return cabecalho, brasil, total


def nova_edicao(url: str, edicao: str, consultado_em: str, corpo: bytes) -> dict:
    """Registro de uma edição. Sem linha do Brasil ou acima do limite: lacuna declarada, nunca vazio."""
    cabecalho, brasil, total = linhas_do_brasil(corpo.decode("utf-8", "replace"))
    reg = {"edicao": edicao, "consultado_em": consultado_em, "url": url,
           "sha256": hashlib.sha256(corpo).hexdigest(), "bytes": len(corpo),
           "cabecalho": cabecalho, "n_linhas_csv": total, "n_linhas_brasil": len(brasil)}
    if not brasil:
        reg["lacuna"] = "nenhuma linha do Brasil reconhecida no arquivo (BRA/Brazil/Brasil em alguma coluna)"
    elif len(brasil) > LIMITE_LINHAS_BRASIL:
        reg["lacuna"] = f"linhas do Brasil acima do limite de {LIMITE_LINHAS_BRASIL}; não guardadas"
    else:
        reg["linhas_brasil"] = brasil
    return reg


def incorporar(atual: dict, reg: dict) -> bool:
    """Acrescenta `reg` a `atual['edicoes']` se o hash for novo. Nunca sobrescreve. True se mudou."""
    edicoes = atual.setdefault("edicoes", [])
    if any(e.get("sha256") == reg["sha256"] for e in edicoes):
        return False
    edicoes.append(reg)
    edicoes.sort(key=lambda e: (e["edicao"], e["consultado_em"]))
    return True


def autoteste() -> int:
    casos = []
    html = ('<a href="https:\\/\\/impactlab.org\\/wp-content\\/uploads\\/2026\\/10\\/'
            'v261026_adm1_output_BASE_rounded_cust.csv?ver=1793065718">Download</a>')
    achado = achar_csv(html)
    casos.append(("lê o link com barras escapadas e a edição do nome",
                  achado == ("https://impactlab.org/wp-content/uploads/2026/10/"
                             "v261026_adm1_output_BASE_rounded_cust.csv?ver=1793065718", "2026-10-26")))
    casos.append(("página sem link devolve None, nunca um nome montado", achar_csv("<html></html>") is None))
    casos.append(("data impossível no nome não vira edição",
                  achar_csv('x/uploads/2026/10/v269999_adm1_output_BASE.csv') is None))

    corpo = (b"iso,adm1,month,value\nBRA,SP,2026-10,5\nUSA,TX,2026-10,9\nbrazil,RJ,2026-11,7\n"
             b"XBRA,AC,2026-10,1\n")
    cab, bra, total = linhas_do_brasil(corpo.decode())
    casos.append(("cabeçalho guardado como veio", cab == ["iso", "adm1", "month", "value"]))
    casos.append(("só linhas do Brasil, inteiras", bra == [["BRA", "SP", "2026-10", "5"],
                                                           ["brazil", "RJ", "2026-11", "7"]]))
    casos.append(("conta todas as linhas do arquivo", total == 4))

    reg = nova_edicao("u", "2026-10-26", "2026-11-01", corpo)
    casos.append(("edição traz hash, tamanho e linhas", len(reg["sha256"]) == 64 and reg["bytes"] == len(corpo)
                  and len(reg["linhas_brasil"]) == 2))
    sem = nova_edicao("u", "2026-10-26", "2026-11-01", b"a,b\nUSA,1\n")
    casos.append(("sem Brasil é lacuna declarada, não lista vazia",
                  "lacuna" in sem and "linhas_brasil" not in sem))

    arq = {}
    casos.append(("edição nova entra", incorporar(arq, reg) is True))
    casos.append(("mesmo hash não regrava (idempotente)", incorporar(arq, dict(reg, consultado_em="2026-11-02")) is False))
    outra = nova_edicao("u", "2026-11-16", "2026-11-17", corpo + b"BRA,MG,2026-12,3\n")
    incorporar(arq, outra)
    casos.append(("edição seguinte acrescenta e a anterior fica",
                  [e["edicao"] for e in arq["edicoes"]] == ["2026-10-26", "2026-11-16"]))
    fonte = pathlib.Path(__file__).read_text(encoding="utf-8")
    codigo = fonte.split("def autoteste")[0]
    casos.append(("trava estrutural: não escreve nos arquivos do banco",
                  not any(n in codigo.replace("estados.json, ", "") and f'/ "{n}"' in codigo
                          for n in ("estados.json", "saude_uf.json", "municipios.json",
                                    "indice.json", "monitor_saude.json"))))
    casos.append(("a ressalva diz que é projeção de modelo", "Projeção de modelo" in RESSALVA))

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()

    from coletores_base import DATA, buscar, gravar_em, hoje_editorial, ler, log_busca, registrar_lacuna

    hoje = hoje_editorial().isoformat()
    try:
        html = buscar(PAGINA, timeout=60).decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        registrar_lacuna("Climate Impact Lab (projeção de mortalidade por calor)",
                         f"página do Tracker: {type(e).__name__}", canal="DOU", camada=1)
        print("projecao_cil: página fora do ar — lacuna declarada, arquivo não tocado")
        return 0
    achado = achar_csv(html)
    if not achado:
        registrar_lacuna("Climate Impact Lab (projeção de mortalidade por calor)",
                         "o link do CSV por ADM1 não está no HTML servido pela página",
                         canal="DOU", camada=1)
        print("projecao_cil: link do CSV ausente no HTML — lacuna declarada, arquivo não tocado")
        return 0
    url, edicao = achado
    try:
        corpo = buscar(url, timeout=120)
    except Exception as e:  # noqa: BLE001
        registrar_lacuna("Climate Impact Lab (projeção de mortalidade por calor)",
                         f"CSV da edição {edicao}: {type(e).__name__}", canal="DOU", camada=1)
        print(f"projecao_cil: CSV da edição {edicao} não baixou — lacuna declarada")
        return 0

    atual = ler(SAIDA, {}) or {}
    reg = nova_edicao(url, edicao, hoje, corpo)
    if not incorporar(atual, reg):
        print(f"projecao_cil: edição {edicao} já guardada (mesmo hash) — nada a gravar")
        return 0
    atual.update({
        "_governanca": ("Projeção de mortalidade por calor, Climate Impact Lab — coluna 1 do quadro de "
                        "mortalidade comparada. Peso zero, sem nota, sem faixa. " + RESSALVA),
        "fonte": PAGINA, "credito": CREDITO, "granularidade": "ADM1, mensal (como no arquivo da fonte)"})
    (DATA / "saude_desfechos").mkdir(parents=True, exist_ok=True)
    gravar_em(DATA / SAIDA, atual)
    log_busca("DOU", 1, [PAGINA, url], "registro", nivel="nacional", n_resultados=reg["n_linhas_brasil"],
              resultados=f"projeção CIL, edição {edicao}: {reg['n_linhas_brasil']} linha(s) do Brasil")
    print(f"projecao_cil: edição {edicao} guardada; {reg['n_linhas_brasil']} linha(s) do Brasil"
          + (f"; LACUNA: {reg['lacuna']}" if "lacuna" in reg else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
