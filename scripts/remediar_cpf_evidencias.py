#!/usr/bin/env python3
"""
scripts/remediar_cpf_evidencias.py — remediação de dados pessoais em evidências já preservadas
================================================================================================
Achado de auditoria (12/09/2026): coletar_diarios_municipais.py preserva a edição INTEIRA do
Diário Oficial quando ela bate a busca por "plano de contingência" — e diários oficiais brasileiros
publicam dezenas de atos não relacionados na mesma edição, alguns citando CPF de contribuintes e
servidores. 1.018 CPFs distintos em 69 arquivos já publicados via evidencias/ (netlify.toml:
publish = "."  — o repositório inteiro é o site).

A causa raiz já foi corrigida em preservar_texto_integral() e gravar_texto() (coletores_base.py e
preservar_evidencias.py) — toda evidência NOVA sai redigida. Este script trata o que já existe:
1. redige CPF de cada arquivo afetado;
2. recalcula o hash de conteúdo, quando o nome do arquivo É esse hash (preservar_evidencias.py);
   arquivos cujo nome é o hash do PDF de origem, não do texto (coletar_diarios_municipais.py),
   mantêm o nome — só o conteúdo muda;
3. atualiza data/evidencias.json com o novo hash/tamanho onde aplicável;
4. nunca apaga o arquivo nem o registro: a evidência do plano de contingência continua íntegra,
   só os CPFs somem.

Idempotente: rodar de novo em arquivo já redigido não muda nada (0 CPFs encontrados = sem escrita).
  python3 scripts/remediar_cpf_evidencias.py            # aplica de verdade
  python3 scripts/remediar_cpf_evidencias.py --dry-run  # só relata, não grava
"""
import hashlib, json, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from coletores_base import redigir_dados_pessoais  # noqa: E402

EVID = RAIZ / "evidencias"


def main() -> int:
    dry = "--dry-run" in sys.argv
    idx_path = RAIZ / "data" / "evidencias.json"
    idx = json.load(open(idx_path, encoding="utf-8"))
    total_arquivos = total_cpfs = 0
    # .txt: preservar_texto_integral() e gravar_texto() — o grosso dos casos (edição inteira de
    # diário). .json/.html: achados isolados de auditoria — mesma redação, sem tocar em sintaxe:
    # o padrão de CPF é sequência de dígitos/pontos/traço, nunca parte de chave ou marcação.
    for p in sorted(list(EVID.glob("*.txt")) + list(EVID.glob("*.json")) + list(EVID.glob("*.html"))):
        h_antigo = p.stem
        try:
            texto = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # arquivo antigo em outra codificação (comum em sites .gov.br mais velhos); lê tolerando
            # bytes inválidos — mesma prática já usada pelos coletores (.decode(enc, "replace")) — e
            # sempre regrava em utf-8 daqui em diante, normalizando.
            texto = p.read_bytes().decode("utf-8", errors="replace")
        novo_texto, n = redigir_dados_pessoais(texto)
        if n == 0:
            continue
        total_arquivos += 1
        total_cpfs += n
        print(f"{'[dry-run] ' if dry else ''}{p.name}: {n} CPF(s)")
        if dry:
            continue
        if p.suffix == ".json":
            json.loads(novo_texto)  # a redação não pode quebrar JSON válido — verifica antes de gravar
        p.write_text(novo_texto, encoding="utf-8")
        item = idx["itens"].get(h_antigo)
        if item is None:
            continue
        # o nome do arquivo É o hash do conteúdo (convenção de preservar_evidencias.py / itens
        # manuais desta sessão) → renomeia para o novo hash. Itens de coletar_diarios_municipais.py
        # têm o nome = hash do PDF/API de origem (texto_integral é um campo à parte) → não renomeia,
        # só atualiza tamanho.
        if item.get("arquivo") and item["arquivo"].endswith(f"{h_antigo}{p.suffix}") and "texto_integral" not in item:
            h_novo = hashlib.sha256(novo_texto.encode("utf-8")).hexdigest()
            p.rename(EVID / f"{h_novo}{p.suffix}")
            idx["itens"][h_novo] = idx["itens"].pop(h_antigo)
            idx["itens"][h_novo]["arquivo"] = f"evidencias/{h_novo}{p.suffix}"
            idx["itens"][h_novo]["tamanho"] = len(novo_texto.encode("utf-8"))
            idx["itens"][h_novo]["nota"] = (idx["itens"][h_novo].get("nota", "") +
                f" REDIGIDO em 12/09/2026 ({n} CPF removido(s) — achado de auditoria, LGPD art. 6º III).").strip()
        else:
            item["tamanho"] = len(novo_texto.encode("utf-8"))
            item["nota"] = (item.get("nota", "") +
                f" REDIGIDO em 12/09/2026 ({n} CPF removido(s) do texto_integral — achado de auditoria, LGPD art. 6º III).").strip()
    if not dry and total_arquivos:
        json.dump(idx, open(idx_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n{'Seria redigido' if dry else 'Redigido'}: {total_arquivos} arquivo(s), {total_cpfs} CPF(s) no total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
