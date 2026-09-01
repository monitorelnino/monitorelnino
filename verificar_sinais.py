#!/usr/bin/env python3
"""
verificar_sinais.py — portão bloqueante do registro de sinais oficiais de risco.

Roda em `atualizar.py` (etapa 5b) e a mão. Verifica as invariantes que separam
esta página de um site de previsão climática — o risco que a própria existência
dela cria (METODOLOGIA §23.4):

  1. Estrutura: 27 UFs, catálogo de fontes íntegro, vocabulário de tipos fechado.
  2. Proveniência: TODO valor exibido tem fonte conhecida, documento e data.
     Sem os três, não pode ir para a tela.
  3. Peso zero: nenhuma chave de sinal aparece no motor do índice nem em
     data/indice.json. Este é o portão que impede a página de virar insumo.
  4. Linguagem: nenhum rótulo de severidade inventado pelo projeto, nenhuma
     frase de previsão em primeira pessoa, teto probatório respeitado.
  5. Lacuna honesta: fonte com status de espera não pode ter dado pendurado.

Saída 0 = pode publicar. Saída 1 = publicação bloqueada.
"""
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).parent
REGISTRO = RAIZ / "data" / "sinais_risco.json"
PAGINA = RAIZ / "sinais-de-risco.html"
INDICE = RAIZ / "data" / "indice.json"
MOTOR = RAIZ / "recalcular_mare.py"
UFS = {"AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT",
       "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"}
TIPOS = {"estiagem", "chuvas", "incendios", "misto", "sem_sinal"}
STATUS = {"coletado", "aguardando_primeira_coleta", "falha_de_rede"}

# Frases que fariam o Monitor falar como previsor. A página reproduz fonte; não prevê.
PROIBIDAS = [
    (r"\bpreve+mos\b|\bprevemos\b|\bnossa previs[ãa]o\b|\bnosso progn[óo]stico\b",
     "previsão em primeira pessoa — a página reproduz fonte, não prevê"),
    (r"\bn[ãa]o existe\b|\bn[ãa]o h[áa] risco\b|\bsem risco\b",
     "afirmação de inexistência acima do teto probatório"),
    (r"\bsuper el ni[ñn]o\b", "rótulo não presente no vocabulário dos boletins oficiais"),
    (r"\brisco cr[íi]tico\b|\bimpacto cr[íi]tico\b|\bn[íi]vel cr[íi]tico\b",
     "escala de severidade própria — proibida (transferência conceitual §11)"),
    (r"\bcertamente\b|\bcom certeza\b|\bgarantido\b", "modalidade de certeza indevida"),
]

falhas = []
avisos = []


def falha(msg):
    """Registra uma falha bloqueante."""
    falhas.append(msg)


def main():
    """Executa as cinco baterias de verificação sobre o registro e a página, e devolve o código de saída do portão."""
    if not REGISTRO.exists():
        print("✗ data/sinais_risco.json ausente — rode coletar_sinais_risco.py --semear")
        return 1
    reg = json.loads(REGISTRO.read_text(encoding="utf-8"))

    # ---- 1. estrutura -----------------------------------------------------
    if set(reg.get("uf", {})) != UFS:
        falha(f"registro não cobre exatamente as 27 UFs (tem {len(reg.get('uf', {}))})")
    if set(reg["_formato"].get("tipos_de_risco", {})) != TIPOS:
        falha("vocabulário de tipos de risco divergente da lista fechada")
    if set(reg["_formato"].get("tipos_de_risco_curto", {})) != TIPOS:
        falha("rótulos curtos não cobrem exatamente os mesmos tipos de risco")
    if "NENHUM" not in reg["_formato"].get("efeito_no_indice", ""):
        falha("registro não declara efeito nulo sobre o índice")
    for chave, fonte in reg.get("fontes", {}).items():
        if fonte.get("status") not in STATUS:
            falha(f"fonte {chave}: status desconhecido ({fonte.get('status')})")
        for campo in ("nome", "orgao", "camada", "url_publica", "papel"):
            if not fonte.get(campo):
                falha(f"fonte {chave}: campo obrigatório ausente ({campo})")
        if not str(fonte.get("url_publica", "")).startswith("http"):
            falha(f"fonte {chave}: url_publica não é endereço absoluto")
    camadas = {f.get("camada") for f in reg.get("fontes", {}).values()}
    if camadas != {"ciclo", "observado", "enos"}:
        falha(f"as três camadas não estão representadas no catálogo: {sorted(camadas)}")

    # ---- 2. proveniência de todo valor exibido ----------------------------
    conhecidas = set(reg.get("fontes", {}))
    for uf, bloco in reg.get("uf", {}).items():
        for campo, valor in bloco.items():
            if valor is None:
                continue
            if not isinstance(valor, dict):
                falha(f"{uf}.{campo}: valor sem envelope de proveniência")
                continue
            if valor.get("fonte") not in conhecidas:
                falha(f"{uf}.{campo}: fonte desconhecida ({valor.get('fonte')})")
            if not valor.get("documento"):
                falha(f"{uf}.{campo}: sem documento citado")
            fonte = reg["fontes"].get(valor.get("fonte"), {})
            if not (valor.get("consultado_em") or fonte.get("consultado_em")):
                falha(f"{uf}.{campo}: sem data de consulta")
            if campo == "risco_projetado" and valor.get("tipo") not in TIPOS:
                falha(f"{uf}.risco_projetado: tipo fora do vocabulário ({valor.get('tipo')})")
    for nome, bloco in (reg.get("enos") or {}).items():
        if bloco is None:
            continue
        if bloco.get("fonte") not in conhecidas or not bloco.get("documento"):
            falha(f"enos.{nome}: proveniência incompleta")

    # ---- 3. peso zero: o portão que impede virar insumo do índice ---------
    motor = MOTOR.read_text(encoding="utf-8")
    for termo in ("sinais_risco", "sinal_risco", "avisos_inmet", "focos_24h", "monitor_secas"):
        if re.search(rf"\b{termo}\b", motor):
            falha(f"recalcular_mare.py menciona '{termo}' — sinal de risco não pode entrar no motor do índice")
    if INDICE.exists():
        indice = INDICE.read_text(encoding="utf-8")
        for termo in ("sinais_risco", "focos_24h", "avisos_inmet"):
            if termo in indice:
                falha(f"data/indice.json contém '{termo}' — o índice não pode carregar sinal de risco")

    # ---- 4. linguagem da página ------------------------------------------
    if PAGINA.exists():
        html = PAGINA.read_text(encoding="utf-8")
        visivel = re.sub(r"<script\b[\s\S]*?</script>|<style\b[\s\S]*?</style>|<!--[\s\S]*?-->", " ", html)
        texto = re.sub(r"<[^>]+>", " ", visivel)
        for padrao, motivo in PROIBIDAS:
            achado = re.search(padrao, texto, re.I)
            if achado:
                falha(f"sinais-de-risco.html: '{achado.group(0)}' — {motivo}")
        if "não faz previsão climática" not in texto:
            falha("sinais-de-risco.html: falta a declaração de que o Monitor não faz previsão climática")
        if "não entra no índice" not in texto and "não entram no índice" not in texto:
            falha("sinais-de-risco.html: falta a declaração de peso zero no índice MARÉ")
        # O crédito é montado em tempo de execução a partir do registro (função
        # `credito`), então o que se verifica aqui é o que É estático: a chamada
        # existe para cada fonte do catálogo. Que o crédito renderize com link,
        # documento e data é verificado por scripts/verificar_runtime_sinais.js.
        for chave in reg["fontes"]:
            if f"'{chave}'" not in html:
                falha(f"sinais-de-risco.html: fonte '{chave}' catalogada mas nunca creditada na página")
    else:
        avisos.append("sinais-de-risco.html ainda não existe — checagem de linguagem pulada")

    # ---- 5. lacuna honesta ------------------------------------------------
    for chave, fonte in reg["fontes"].items():
        if fonte["status"] != "coletado":
            if fonte.get("documento") or fonte.get("consultado_em"):
                falha(f"fonte {chave}: em espera, mas com documento/data pendurados")
            pendurado = [uf for uf, b in reg["uf"].items()
                         if any(isinstance(v, dict) and v.get("fonte") == chave for v in b.values())]
            if pendurado:
                falha(f"fonte {chave}: em espera, mas com dado em {len(pendurado)} UF(s)")

    n_espera = sum(1 for f in reg["fontes"].values() if f["status"] != "coletado")
    if n_espera:
        avisos.append(f"{n_espera} de {len(reg['fontes'])} fontes aguardam a primeira coleta "
                      "(a página as exibe como lacuna declarada)")

    for a in avisos:
        print(f"  ⚠ {a}")
    if falhas:
        print("\n".join("  ✗ " + f for f in falhas))
        print(f"\n✗ SINAIS: {len(falhas)} problema(s). Publicação bloqueada.")
        return 1
    coletadas = sum(1 for f in reg["fontes"].values() if f["status"] == "coletado")
    print(f"✓ SINAIS OK — 27 UFs, {len(reg['fontes'])} fontes catalogadas ({coletadas} coletada(s)), "
          "proveniência completa, peso zero confirmado no motor do índice.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
