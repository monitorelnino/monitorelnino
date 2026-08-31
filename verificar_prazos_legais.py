#!/usr/bin/env python3
"""Checagem de prazos federais (legais e judiciais) contra o banco do índice.

Criado em 29/08/2026 (METODOLOGIA §15). Lê o registro curado
data/marcos_prazos.json, computa vencimentos e cruza cada marco com o que o
banco efetivamente localizou por UF (data/estados.json), produzindo
data/prazos_uf.json e um digesto legível.

GOVERNANÇA — o que esta rotina NUNCA faz:
  1. Não pontua: o resultado é marcador editorial e relatório; nenhum campo
     daqui entra em recalcular_mare.py nesta versão (mudança de pontuação
     exige versão maior — CHANGELOG, regra de governança).
  2. Não afirma inexistência: a língua máxima é sempre "não localizado até o
     corte" — nunca "não cumpriu", porque o banco mede o arcabouço PÚBLICO
     localizado, não o universo de atos existentes.
  3. Não computa prazo sem data-base verificada: marco com data_base null é
     reportado como "não computável — pendência declarada", nunca estimado.

Vencimentos: meses por aritmética de calendário; dias corridos por soma
simples; "dias úteis" por dias de semana SEM tabela de feriados — limitação
declarada no próprio registro e repetida na saída.

Uso: python3 verificar_prazos_legais.py            (gera data/prazos_uf.json + digesto)
     python3 verificar_prazos_legais.py --simular  (adiciona quadro EXPERIMENTAL de
                                                    conformidade hipotética — semente
                                                    para estudo da v3; NÃO PUBLICÁVEL)
"""
import datetime
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA",
       "PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"]


def _data(s):
    """Converte 'dd/mm/aaaa' em date; devolve None para formatos incompletos (ex.: '2026')."""
    try:
        return datetime.datetime.strptime(s.strip(), "%d/%m/%Y").date()
    except (ValueError, AttributeError):
        return None


def _soma_meses(d, m):
    """Soma m meses a uma data por aritmética de calendário (dia limitado ao fim do mês)."""
    mes = d.month - 1 + m
    ano = d.year + mes // 12
    mes = mes % 12 + 1
    dia = min(d.day, [31, 29 if ano % 4 == 0 and (ano % 100 != 0 or ano % 400 == 0) else 28,
                      31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mes - 1])
    return datetime.date(ano, mes, dia)


def _soma_dias_uteis(d, n):
    """Soma n dias de semana (seg–sex) a uma data; feriados não considerados (limitação declarada)."""
    atual = d
    while n > 0:
        atual += datetime.timedelta(days=1)
        if atual.weekday() < 5:
            n -= 1
    return atual


def _vencimento(marco):
    """Devolve (date | None, motivo) — None quando o prazo não é computável, com o porquê."""
    base = _data(marco.get("data_base") or "")
    if base is None:
        return None, marco.get("data_base_pendencia", "data-base ausente")
    prazo = marco.get("prazo")
    if not prazo:
        return None, "marco sem prazo (âncora informativa)"
    t, v = prazo["tipo"], prazo["valor"]
    if t == "meses":
        return _soma_meses(base, v), None
    if t == "dias":
        return base + datetime.timedelta(days=v), None
    if t == "dias_uteis":
        return _soma_dias_uteis(base, v), None
    raise AssertionError(f"tipo de prazo desconhecido no registro: {t}")


def validar_registro(reg):
    """Validações bloqueantes do esquema do registro (padrão assert-before-use do projeto)."""
    assert "marcos" in reg and isinstance(reg["marcos"], list) and reg["marcos"], "registro sem marcos"
    ids = [m["id"] for m in reg["marcos"]]
    assert len(ids) == len(set(ids)), "ids de marco duplicados"
    for m in reg["marcos"]:
        assert m.get("classe") in ("legal", "judicial", "tecnico"), f"classe inválida em {m.get('id')}"
        assert m.get("fundamento"), f"marco sem fundamento citável: {m.get('id')}"
        assert m.get("efeito_indice") in ("marcador_editorial", "ancora_de_antecipacao_vigente"), \
            f"efeito_indice fora do vocabulário em {m.get('id')} — pontuação exigiria versão maior"
        dest = m.get("destinatarios", [])
        # "UNIAO" (31/08/2026): marco cujo destinatário é a União — ex.: prazo de deliberação
        # de MP no Congresso — não cruza com o banco por UF; recebe só data e status.
        assert dest and all(d in UFS or d in ("*UF", "municipios_cadastro", "UNIAO") for d in dest), \
            f"destinatários inválidos em {m.get('id')}"


def cruzar(reg, estados, corte):
    """Cruza cada marco computável com o banco por UF; devolve a estrutura de saída."""
    por_uf = {u["uf"]: u for u in estados["ufs"]}
    saida = {"gerado_em": corte.strftime("%d/%m/%Y"),
             "governanca": "marcador editorial — nenhum item pontua nesta versão (METODOLOGIA §15)",
             "marcos": []}
    for m in reg["marcos"]:
        venc, motivo = _vencimento(m)
        item = {"id": m["id"], "classe": m["classe"], "fundamento": m["fundamento"],
                "efeito_indice": m["efeito_indice"],
                # campos curados de exibição (caixa "Prazos em curso" do site, 31/08/2026):
                "titulo_curto": m.get("titulo_curto", ""), "status_curto": m.get("status_curto", ""),
                "fontes": m.get("fontes", [])}
        if venc is None:
            item["situacao"] = f"prazo não computável — {motivo}"
            saida["marcos"].append(item)
            continue
        item["vencimento"] = venc.strftime("%d/%m/%Y")
        if m["prazo"]["tipo"] == "dias_uteis":
            item["limitacao"] = m["prazo"].get("limitacao_declarada", "dias úteis sem feriados")
        destinos = UFS if m["destinatarios"] == ["*UF"] else \
                   [] if m["destinatarios"] in (["municipios_cadastro"], ["UNIAO"]) else m["destinatarios"]
        linhas = []
        for uf in destinos:
            e = por_uf.get(uf, {})
            d_inst = _data(e.get("data", ""))
            if e.get("status") == "LAC":
                sit = "instrumento estadual não localizado até o corte"
                rel = "atenção: vencimento " + ("transcorrido" if venc <= corte else "vigente") + " sem instrumento localizado"
            elif d_inst is None:
                # instrumento LOCALIZADO, mas com data em granularidade grossa (ex.: "2026"):
                # a língua probatória exige distinguir isto de "não localizado".
                sit = f"instrumento localizado, data registrada em granularidade insuficiente para o cômputo ('{e.get('data','')}')"
                rel = "relação com o prazo indeterminada — refinar a data na próxima verificação"
            else:
                sit = f"instrumento localizado, datado de {d_inst.strftime('%d/%m/%Y')}"
                rel = "anterior ao vencimento" if d_inst <= venc else "posterior ao vencimento"
            linhas.append({"uf": uf, "situacao": sit, "relacao_com_prazo": rel})
        if m["destinatarios"] == ["UNIAO"]:
            item["situacao"] = ("destinatário: União — prazo " + ("transcorrido" if venc <= corte else "vigente") +
                                f" (vence em {venc.strftime('%d/%m/%Y')}); status a reconferir na fonte oficial do marco")
        if m["destinatarios"] == ["municipios_cadastro"]:
            item["situacao"] = ("cruzamento municipal aguarda data/cadastro_prioritarios.json — "
                                "pendência declarada no registro")
        item["por_uf"] = linhas
        if m.get("fatos_verificaveis"):
            item["fatos_verificaveis"] = m["fatos_verificaveis"]
        saida["marcos"].append(item)
    return saida


def digesto(saida):
    """Imprime o digesto legível, na língua probatória do projeto."""
    print(f"Prazos federais × banco (corte {saida['gerado_em']}) — {saida['governanca']}")
    for m in saida["marcos"]:
        print(f"\n[{m['classe']}] {m['id']}")
        print(f"  {m['fundamento'][:120]}…" if len(m['fundamento']) > 120 else f"  {m['fundamento']}")
        if "vencimento" in m:
            print(f"  vencimento: {m['vencimento']}" + (f" ({m['limitacao']})" if m.get("limitacao") else ""))
        if m.get("situacao"):
            print(f"  {m['situacao']}")
        for l in m.get("por_uf", [])[:30]:
            print(f"    {l['uf']}: {l['situacao']} — {l['relacao_com_prazo']}")
        if m.get("fatos_verificaveis"):
            print(f"  fatos verificáveis registrados: {m['fatos_verificaveis']}")


def simular(saida):
    """Quadro EXPERIMENTAL: contagem hipotética de marcos atendidos por UF (semente v3, não publicável)."""
    print("\n" + "=" * 72)
    print("SIMULAÇÃO EXPERIMENTAL — NÃO PUBLICÁVEL · semente de estudo para a v3")
    print("Se 'conformidade a prazos' fosse subcritério (NÃO é), a contagem seria:")
    cont = {u: {"anteriores": 0, "aplicaveis": 0} for u in UFS}
    for m in saida["marcos"]:
        for l in m.get("por_uf", []):
            cont[l["uf"]]["aplicaveis"] += 1
            if l["relacao_com_prazo"] == "anterior ao vencimento":
                cont[l["uf"]]["anteriores"] += 1
    for u in UFS:
        c = cont[u]
        if c["aplicaveis"]:
            print(f"  {u}: {c['anteriores']}/{c['aplicaveis']} marcos com instrumento anterior ao vencimento")
    print("Nenhum destes números entra no índice publicado; qualquer promoção a")
    print("subcritério exige versão maior, bateria completa e decisão editorial.")


def main():
    """CLI: valida o registro, cruza com o banco, grava data/prazos_uf.json e imprime o digesto."""
    reg = json.load(open(RAIZ / "data" / "marcos_prazos.json", encoding="utf-8"))
    validar_registro(reg)
    estados = json.load(open(RAIZ / "data" / "estados.json", encoding="utf-8"))
    meta = json.load(open(RAIZ / "data" / "meta.json", encoding="utf-8"))
    corte = _data(meta.get("corte", "")) or datetime.date.today()
    saida = cruzar(reg, estados, corte)
    json.dump(saida, open(RAIZ / "data" / "prazos_uf.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    digesto(saida)
    if "--simular" in sys.argv:
        simular(saida)
    print("\n✓ data/prazos_uf.json gravado (marcador editorial; não pontua)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
