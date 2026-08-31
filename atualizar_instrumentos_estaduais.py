#!/usr/bin/env python3
"""
atualizar_instrumentos_estaduais.py
=====================================
Camada 1 do Protocolo de Busca v2 (Metodologia §4.1.1): verifica repositórios
estaduais ESTRUTURADOS que listam publicamente os planos de contingência
municipais recebidos das coordenadorias, e propõe atualizações a
data/municipios.json quando encontra município novo ou edição mais recente
do que a registrada na base.

REGRA DE OURO (igual a atualizar_transferencias.py): este script NUNCA escreve
diretamente em municipios.json. Ele gera data/instrumentos_revisar.json — você
(ou eu, quando instruído) revisa, remove o que não deve entrar, e só então roda:

    python3 aplicar_revisao.py --arquivo data/instrumentos_revisar.json

REGISTRO DE REPOSITÓRIOS (extensível):
  Cada UF mapeada tem uma função de parser própria, porque cada site estadual
  publica a lista em formato diferente. Adicionar uma UF = escrever um parser
  novo e registrá-lo em REPOSITORIOS; nada mais muda.
  Implementadas: SE. Mapeadas mas SEM parser ainda (grafado no protocolo de
  busca como pendência): PR (SISDC), ES, AM — ver Metodologia §4.1.1(d).

LIMITAÇÃO DE AMBIENTE (declarada, não escondida): o sandbox onde este projeto
é normalmente editado tem a rede restrita a um allowlist de domínios de
pacotes (pypi/npm/github); domínios .gov.br NÃO estão liberados. Este script
portanto não pode ser executado ao vivo dali — ele roda no ambiente real de
publicação (a Action semanal do GitHub, ou a máquina de quem publica), que tem
acesso normal à internet. Por isso o parser é testado à parte, contra uma
cópia salva (fixture) de uma captura real da página — ver tests/.

Uso:
  python3 atualizar_instrumentos_estaduais.py                 # roda todas as UFs implementadas
  python3 atualizar_instrumentos_estaduais.py --uf SE          # só uma UF
  python3 atualizar_instrumentos_estaduais.py --uf SE --fixture tests/fixtures/se_planos_20260826.md
                                                                # modo offline/teste, sem rede
"""
import argparse
import datetime
import json
import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).parent
DATA = RAIZ / "data"

ANO_LIMIAR_VIGENTE = 2024  # edição >= este ano => "plano"; menor => "plano_antigo" (mesma régua já usada na edição de 26/08/2026)


def norm(s: str) -> str:
    """Normaliza nome de município (minúsculas, sem acento, sem pontuação) para comparação robusta contra a base IBGE."""
    return unicodedata.normalize("NFD", s.upper()).encode("ascii", "ignore").decode()


def categoria_por_ano(ano: int) -> str:
    """Deriva a categoria do registro (plano vigente, plano de ciclo anterior etc.) a partir do ano do documento encontrado no repositório estadual."""
    return "plano" if ano >= ANO_LIMIAR_VIGENTE else "plano_antigo"


# ---------------------------------------------------------------------------
# Parsers por UF — cada um recebe o texto bruto da página (markdown ou html
# já extraído) e devolve uma lista de {nome, ano_edicao, url}.
# ---------------------------------------------------------------------------

def parse_es(texto: str):
    """CEPDEC/ES — tabela cujo título de linha traz o município e o ano:
    '| [<NOME> - PLANO DE CONTINGÊNCIA - <ANO>](<url>) | ... |'

    O repositório capixaba usa SEIS grafias diferentes do mesmo termo
    (CONTINGÊNCIA, CONTIGÊNCIA, CONTINGENCIA, CONTIGENCIA, COMTINGÊNCIA,
    'PLANO CONTINGENCIA'), com e sem hífen antes do ano, e ainda erra nomes
    de município (ITAGUAÇUÍ→Itaguaçu, VILA PAVAO→Vila Pavão). Por isso o
    padrão é deliberadamente frouxo no meio e o nome é validado depois
    contra a malha IBGE — exatamente a lição que motivou o dicionário de
    recuperação com variantes erradas (Metodologia §4.1.1).
    """
    padrao = re.compile(
        r"\|\s*\[\s*(.+?)\s*[-–]?\s*PLANO\s+(?:DE\s+)?(?:CON|COM)T[IY]?N?G[ÊE]NCIA\s*[-–]?\s*"
        r"((?:\d{4})(?:\s*[-–]\s*\d{4})?)(?:\s*-\s*\d)?\s*\]\((https?://[^)]+)\)",
        re.IGNORECASE,
    )
    achados = []
    for m in padrao.finditer(texto):
        nome_bruto, anos, url = m.groups()
        nome = nome_bruto.strip(" -–").title()
        for prep in [" Da ", " De ", " Do ", " Das ", " Dos "]:
            nome = nome.replace(prep, prep.lower())
        # intervalo (ex.: 2025-2026, 2022-2025): usa o ano final = vigência declarada
        anos_encontrados = [int(a) for a in re.findall(r"\d{4}", anos)]
        achados.append({"nome": nome, "ano_edicao": max(anos_encontrados),
                        "rotulo_ano": anos.strip(), "url": url})
    return achados


def parse_se(texto: str):
    """Defesa Civil de Sergipe (DEPEC/SUPDEC) — lista em bullets:
    'PLANO DE CONTINGÊNCIA MUNICIPAL DE <NOME> – EDIÇÃO <ANO> [Clique aqui](<url>)'
    """
    padrao = re.compile(
        r"PLANO DE CONTING[ÊE]NCIA MUNICIPAL DE\s+(.+?)\s*[–-]\s*EDI[ÇC][ÃA]O\s*(\d{4})\s*"
        r"\[[^\]]*\]\((https?://\S+?)\)",
        re.IGNORECASE,
    )
    achados = []
    for m in padrao.finditer(texto):
        nome_bruto, ano, url = m.groups()
        nome = nome_bruto.strip().title()
        # correções de capitalização de conectivos comuns em nomes de município
        for prep in [" Da ", " De ", " Do ", " Das ", " Dos "]:
            nome = nome.replace(prep, prep.lower())
        achados.append({"nome": nome, "ano_edicao": int(ano), "url": url})
    return achados


REPOSITORIOS = {
    "SE": {
        "url": "https://defesacivil.se.gov.br/planos-de-contigencia/",
        "fonte": "Defesa Civil SE (DEPEC/SUPDEC) — repositório estadual de PLANCONs",
        "canal": "repositorio_estadual",
        "parser": parse_se,
    },
    "ES": {
        "url": "https://defesacivil.es.gov.br/planos-de-contigencia",
        "fonte": "CEPDEC/ES — repositório estadual de planos de contingência municipais",
        "canal": "repositorio_estadual",
        "parser": parse_es,
    },
    "PR": {"parser": None, "nota": "SISDC/CEPDEC-PR — planos gerados no sistema, sem lista pública de PDFs para parser (Protocolo de Busca v2, decisão pendente ii)"},
    "AM": {"parser": None, "nota": "repositório estadual conhecido, parser não implementado"},
    # Ausências VERIFICADAS em 26/08/2026 (registradas para não repetir a busca):
    # o estado publica material de orientação/modelo, mas NÃO um repositório dos
    # planos municipais recebidos. Rever se a página mudar.
    "SC": {"parser": None, "nota": "VERIFICADO 26/08/2026 — defesacivil.sc.gov.br/municipios/ publica apenas pacotes-modelo (PlanCon AS, PlanCon EduAgravi); sem repositório de planos municipais. Cobertura de SC vem do levantamento declarado do TCE-SC (Painel Farol)"},
    "RS": {"parser": None, "nota": "VERIFICADO 26/08/2026 — defesacivil.rs.gov.br publica modelo de plano (.doc), sem repositório de planos municipais. Cobertura de RS vem do levantamento declarado do TCE-RS 2025"},
}


def casar_com_ibge(achados: list[dict], uf: str, ref: list[dict]):
    """Valida cada nome achado contra a malha IBGE da UF, devolve o nome oficial
    e anexa as coordenadas da referência (que traz lat/lon desde 26/08/2026, o
    que dispensa geocodificação externa no pipeline).
    O repositório do órgão pode grafar errado (ITAGUAÇUÍ→Itaguaçu, VILA PAVAO→
    Vila Pavão); nenhum registro entra na base com nome que não exista na malha —
    os não casados são devolvidos à parte para conferência humana, jamais
    descartados em silêncio."""
    oficiais = {norm(r["nome"]): r for r in ref if r["uf"] == uf}
    casados, orfaos = [], []
    for a in achados:
        chave = norm(a["nome"])
        oficial = oficiais.get(chave)
        if oficial is None:
            # tolerância a erro de grafia do órgão: similaridade alta e ÚNICA
            import difflib
            proximos = difflib.get_close_matches(chave, list(oficiais.keys()), n=2, cutoff=0.88)
            if len(proximos) == 1:
                oficial = oficiais[proximos[0]]
                a["nome_no_repositorio"] = a["nome"]
            else:
                orfaos.append(a)
                continue
        a["nome"] = oficial["nome"]
        if "lat" in oficial and "lon" in oficial:
            a["lat"], a["lon"] = oficial["lat"], oficial["lon"]
        casados.append(a)
    return casados, orfaos


def carregar_texto(uf: str, fixture: str | None) -> str:
    """Baixa e extrai o texto de uma página ou documento do repositório estadual, com tratamento de encoding e timeout."""
    if fixture:
        return Path(fixture).read_text(encoding="utf-8")
    try:
        import requests
    except ImportError:
        sys.exit("Erro: pacote 'requests' ausente (deveria estar em requirements.txt).")
    url = REPOSITORIOS[uf]["url"]
    resp = requests.get(url, timeout=30, headers={"User-Agent": "MonitorElNinoBrasil/1.0 (Futura Evidence Lab)"})
    resp.raise_for_status()
    return resp.text


def diagnosticar(uf: str, achados: list[dict], municipios: list[dict]) -> list[dict]:
    """Compara os achados do repositório contra a base e devolve propostas."""
    cfg = REPOSITORIOS[uf]
    base_uf = {norm(m["nome"]): m for m in municipios if m["uf"] == uf}
    hoje = datetime.date.today().strftime("%d/%m/%Y")
    propostas = []
    for a in achados:
        chave = norm(a["nome"])
        categoria_proposta = categoria_por_ano(a["ano_edicao"])
        atual = base_uf.get(chave)
        registro_base = {
            "nome": a["nome"], "uf": uf, "categoria": categoria_proposta,
            **({"lat": a["lat"], "lon": a["lon"]} if "lat" in a else {}),
            "documento": f"PLANCON edição {a.get('rotulo_ano', a['ano_edicao'])} (repositório estadual)",
            "data": hoje, "fonte": cfg["fonte"], "url": a["url"], "canal": cfg["canal"],
        }
        if atual is None:
            propostas.append({"acao": "novo", "uf": uf, **registro_base})
        elif atual["categoria"] == "nao_localizado":
            propostas.append({"acao": "atualizar", "uf": uf, "de_categoria": atual["categoria"], **registro_base})
        elif atual["categoria"] != categoria_proposta and atual.get("url") != a["url"]:
            # o repositório mostra edição de categoria diferente da já registrada
            # (ex.: base tinha plano_antigo e o repositório agora lista edição vigente)
            ordem = {"nao_localizado": 0, "plano_antigo": 1, "decreto": 1, "plano_elaboracao": 1, "plano": 2}
            if ordem.get(categoria_proposta, 0) > ordem.get(atual["categoria"], 0):
                propostas.append({"acao": "atualizar", "uf": uf, "de_categoria": atual["categoria"], **registro_base})
        # se já é 'plano' ou 'plano_antigo' e a URL bate: nada a propor (já sincronizado)
    return propostas


def main():
    """Percorre os repositórios estaduais com parser implementado, compara com o banco atual e grava as propostas em data/instrumentos_revisar.json para aprovação humana."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--uf", help="Rodar só esta UF (padrão: todas as implementadas)")
    ap.add_argument("--fixture", help="Arquivo local para testar sem rede (uso com --uf)")
    args = ap.parse_args()

    ufs = [args.uf] if args.uf else [u for u, c in REPOSITORIOS.items() if c["parser"]]
    municipios = json.load(open(DATA / "municipios.json", encoding="utf-8"))

    todas_propostas, falhas = [], []
    for uf in ufs:
        cfg = REPOSITORIOS.get(uf)
        if not cfg:
            print(f"[erro] UF não registrada: {uf}"); continue
        if not cfg["parser"]:
            print(f"[pulado] {uf}: {cfg.get('nota', 'sem parser implementado')}")
            continue
        print(f"[{uf}] verificando {cfg['url']} ...")
        try:
            texto = carregar_texto(uf, args.fixture)
        except Exception as e:
            print(f"  [FALHA] não foi possível verificar {uf}: {e}")
            falhas.append(uf)
            continue
        achados = cfg["parser"](texto)
        print(f"  {len(achados)} instrumento(s) listado(s) no repositório")
        ref = json.load(open(DATA / "municipios_ibge_referencia.json", encoding="utf-8"))
        achados, orfaos = casar_com_ibge(achados, uf, ref)
        if orfaos:
            print(f"  [atenção] {len(orfaos)} nome(s) não casaram com a malha IBGE — NÃO entram, conferir à mão:")
            for o in orfaos: print(f"      · '{o['nome']}' ({o['url'][:80]})")
        renomeados = [a for a in achados if "nome_no_repositorio" in a]
        if renomeados:
            print(f"  [nota] {len(renomeados)} grafia(s) corrigida(s) pela malha IBGE:")
            for r in renomeados: print(f"      · '{r['nome_no_repositorio']}' → {r['nome']}")
        propostas = diagnosticar(uf, achados, municipios)
        todas_propostas.extend(propostas)
        if propostas:
            for p in propostas:
                print(f"  → {p['acao'].upper()}: {p['nome']}/{p['uf']} ({p['documento']})")
        else:
            print(f"  ✓ nenhuma diferença — base já reflete o repositório")

    saida = DATA / "instrumentos_revisar.json"
    if todas_propostas:
        json.dump(todas_propostas, open(saida, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"\n{len(todas_propostas)} proposta(s) salvas em {saida.relative_to(RAIZ)}")
        print("PRÓXIMO PASSO (manual, obrigatório):")
        print("  Revise o arquivo, apague o que não deve entrar, e então rode:")
        print(f"    python3 aplicar_revisao.py --arquivo {saida.relative_to(RAIZ)}")
    else:
        if saida.exists():
            saida.unlink()
        verificadas = [u for u in ufs if u not in falhas]
        print(f"\nNenhuma proposta pendente nas UFs efetivamente verificadas: {', '.join(verificadas) or 'nenhuma'}.")

    if falhas:
        # Falha de rede NÃO pode ser lida como 'nada mudou' — sai com código != 0
        # para que o pipeline registre que a verificação ficou incompleta.
        print(f"\n[ATENÇÃO] {len(falhas)} UF(s) NÃO puderam ser verificadas: {', '.join(falhas)}.")
        print("          Isto não significa 'sem novidades' — significa verificação incompleta.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
