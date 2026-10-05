#!/usr/bin/env python3
"""
scripts/incorporar_lai_am_ro.py — os documentos de AM e RO e as respostas das COMPDECs
=======================================================================================
Bloco "AM e RO: arquivos de LAI JÁ ESTÃO no repositório" do `ESTADO_ATUAL.md` (04/10/2026).

O QUE O JUIZ LEU, E O QUE ISSO SIGNIFICA
-----------------------------------------
Os quatro PDFs foram lidos integralmente (46, 37, 40 e 3 páginas) e julgados com o codebook 1.3,
com a proveniência de LAI que a etapa 0 passou a aceitar — documento entregue pelo próprio órgão,
com órgão, data da resposta e hash do arquivo. **Nenhum dos quatro promove**, e cada recusa tem o
seu motivo:

  AM · Plano Tático de Estiagem 2026 (v2)   → `autoridade_nao_confirmada`: nenhuma fórmula de
      promulgação e nenhum texto articulado. O cronograma do próprio plano marca "Aprovação e
      Divulgação" como EM ANDAMENTO, o que é coerente com a recusa: o documento existe, a aprovação
      não está nele.
  AM · Plano Tático de Inundações 2026      → `resposta`: o teste-fósforo da etapa 4 encontra rota
      de reconhecimento federal/FIDE. Além disso trata de cheia, não do risco previsto para o ciclo.
  RO · Plano Operacional de Crise Hídrica   → `citacao_incompleta`: o documento não nomeia o
      instrumento que o institui.
  RO · Ofício 20265/2026                    → `autoridade_nao_confirmada`: é a resposta ao pedido,
      não um plano, e é como resposta que ele entra.

Então **nada sobe e nada desce**: AM continua com 100 no instrumento por outro registro, e RO
continua em READ (70) pelo seu. Os quatro entram como DOCUMENTOS do estado, com hash e proveniência
— prova de que existem e do que dizem, sem pontuar. Esse é o resultado, e não um resultado vazio: a
pergunta "o estado tem plano para este risco?" passa a ter documento por trás, com o que ele cobre.

AS COMPDECs DE RO
-----------------
34 respostas de 30 municípios (4 duplicados; vale a mais recente, pelo carimbo de data). É
afirmação do órgão municipal sem documento: **não pontua**. Vira nota com a data da resposta e
tarefa de busca dirigida no sítio de cada prefeitura. Nomes, telefones e e-mails do formulário não
entram em lugar nenhum — o extrato já chegou sem eles (LGPD, minimização).

USO
  python3 scripts/incorporar_lai_am_ro.py --autoteste
  python3 scripts/incorporar_lai_am_ro.py --dry-run
  python3 scripts/incorporar_lai_am_ro.py
"""
import csv
import io
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

PRIVADO = pathlib.Path("C:/Users/User/Documents/MARE/robo-registro/notas/lai/respostas")
EXTRATO = PRIVADO / "RO" / "COMPDEC_extrato_sem_dados_pessoais.csv"

# O que o juiz devolveu, em 04/10/2026, com o codebook 1.3. Fica aqui como DADO do veredito, não
# como opinião: hash do arquivo julgado, motivo da recusa e o que o documento cobre.
DOCUMENTOS = (
    {"uf": "AM", "titulo": "Plano Tático de Estiagem 2026 (versão 2)",
     "orgao": "Secretaria de Estado de Defesa Civil do Amazonas",
     "entregue_em": "01/10/2026", "paginas": 46,
     "sha256": "d1272acbef3d",
     "veredito": "autoridade_nao_confirmada",
     "cobre": "estiagem e vazante",
     "nota_do_juiz": ("Sem fórmula de promulgação e sem texto articulado; o cronograma do próprio "
                      "plano registra a aprovação como em andamento.")},
    {"uf": "AM", "titulo": "Plano Tático de Inundações 2026",
     "orgao": "Secretaria de Estado de Defesa Civil do Amazonas",
     "entregue_em": "01/10/2026", "paginas": 37,
     "sha256": "a96f534c36cc",
     "veredito": "resposta",
     "cobre": "cheia e inundação",
     "nota_do_juiz": ("Natureza de resposta pelo teste da etapa 4; trata de cheia, não do risco "
                      "previsto para o ciclo no estado.")},
    {"uf": "RO", "titulo": "Plano Operacional de Prevenção e Resposta à Crise Hídrica 2025/2026/2027",
     "orgao": "Governo do Estado de Rondônia (elaboração SEPOG)",
     "entregue_em": "30/09/2026", "paginas": 40,
     "sha256": "f7c0bf20c2c1",
     "veredito": "citacao_incompleta",
     "cobre": "seca, estiagem, ondas de calor e incêndios florestais",
     "nota_do_juiz": "O documento não nomeia o instrumento que o institui."},
    {"uf": "RO", "titulo": "Ofício 20265/2026 (CBMRO/CEPDEC)",
     "orgao": "Corpo de Bombeiros Militar de Rondônia — CEPDEC",
     "entregue_em": "30/09/2026", "paginas": 3,
     "sha256": "b3e5ee3f0bc7",
     "veredito": "autoridade_nao_confirmada",
     "cobre": None,
     "nota_do_juiz": "É a resposta ao pedido de acesso à informação, não um plano."},
)

TEXTO_DOCUMENTO_DO_ESTADO = (
    "{titulo}, de {orgao}, entregue ao MARÉ em {entregue_em} em resposta a pedido de acesso à "
    "informação. O documento não altera o que o índice registra para o estado.")
TEXTO_COMPDEC_COM_PLANO = (
    "A Defesa Civil de RO informou ao MARÉ, em resposta a pedido de acesso à informação de "
    "30/09/2026, que o município declarou plano de contingência vigente, com última atualização "
    "em {ano}. O documento ainda não foi localizado em fonte pública e, por isso, não entra no "
    "índice.")
TEXTO_COMPDEC_SEM_PLANO = (
    "A Defesa Civil de RO informou ao MARÉ, em resposta a pedido de acesso à informação de "
    "30/09/2026, que o município declarou não ter plano de contingência elaborado.")
DATA_RO = "30/09/2026"


def respostas_do_extrato(texto_csv: str) -> list:
    """Uma resposta por município, a mais recente quando houver duplicata. Função pura.

    O desempate é pelo carimbo de data do formulário, e não pela ordem do arquivo: quatro
    municípios responderam duas vezes, e a resposta velha diria o contrário da nova.
    """
    linhas = list(csv.DictReader(io.StringIO(texto_csv or "")))
    def chave(l):
        # dd/mm/aaaa hh:mm:ss → ordenável
        c = str(l.get("carimbo_data") or "")
        try:
            d, h = c.split(" ")
            dia, mes, ano = d.split("/")
            return (ano, mes, dia, h)
        except ValueError:
            return ("", "", "", "")
    por_municipio = {}
    for l in linhas:
        nome = str(l.get("municipio") or "").strip()
        if not nome:
            continue
        atual = por_municipio.get(nome)
        if atual is None or chave(l) > chave(atual):
            por_municipio[nome] = l
    return [por_municipio[k] for k in sorted(por_municipio)]


def tem_plano(resposta: dict) -> bool:
    """O município declarou plano vigente? Função pura."""
    return str((resposta or {}).get("plano_vigente_5_1") or "").strip().lower() == "sim"


def nota_de_compdec(resposta: dict) -> str:
    """A nota da ficha, nos textos aprovados pela editoria. Função pura."""
    if not tem_plano(resposta):
        return TEXTO_COMPDEC_SEM_PLANO
    ano = str(resposta.get("ano_atualizacao_5_3") or "").strip()
    # Ano que não é ano não vira ano: a resposta "Não elaboramos o plano ainda" aparece neste
    # campo em quem respondeu "não", e um dígito qualquer aqui viraria uma data falsa na ficha.
    return TEXTO_COMPDEC_COM_PLANO.format(ano=ano if ano.isdigit() else "ano não declarado")


def resumo(respostas: list) -> dict:
    """Contagem por desfecho e por ano, para o relatório. Função pura."""
    com = [r for r in respostas if tem_plano(r)]
    anos = {}
    for r in com:
        a = str(r.get("ano_atualizacao_5_3") or "").strip()
        if a.isdigit():
            anos[a] = anos.get(a, 0) + 1
    formais = [r for r in com
               if "apenas formal" in str(r.get("natureza_5_4") or "").lower()]
    return {"municipios": len(respostas), "com_plano": len(com),
            "sem_plano": len(respostas) - len(com), "por_ano": dict(sorted(anos.items())),
            "apenas_formal": len(formais)}


def busca_dirigida(nome: str, uf: str, data: str) -> dict:
    """A tarefa de procurar o documento no sítio da prefeitura. Função pura.

    Não é pista da fila, pelo mesmo motivo de 03/10: a porta da fila exige endereço resolvido, e
    afirmação de órgão não tem endereço — é o que falta nela.
    """
    return {"municipio": nome, "uf": uf, "assunto": "plano de contingência", "nivel": "A",
            "origem": "resposta_lai",
            "fonte": f"Defesa Civil de {uf}, resposta a pedido de acesso à informação de {data}",
            "url": None, "registrado_em": "2026-10-04"}


def documentos_do_estado() -> list:
    """Os quatro documentos, com o texto da ficha. Função pura."""
    fora = []
    for d in DOCUMENTOS:
        fora.append({**d, "nota": TEXTO_DOCUMENTO_DO_ESTADO.format(
            titulo=d["titulo"], orgao=d["orgao"], entregue_em=d["entregue_em"])})
    return fora


def aplicar(dry_run: bool = False) -> int:
    from coletores_base import gravar, ler
    notas = ler("notas_lai.json") or {"municipios": [], "estados": [], "buscas_dirigidas": []}
    respostas = respostas_do_extrato(EXTRATO.read_text(encoding="utf-8")) if EXTRATO.exists() else []
    r = resumo(respostas)
    print(f"  COMPDECs de RO: {r['municipios']} município(s) · {r['com_plano']} com plano "
          f"declarado · {r['sem_plano']} sem · {r['apenas_formal']} apenas formal")
    print(f"  por ano da última atualização: {r['por_ano']}")

    docs = documentos_do_estado()
    print(f"  documentos de estado registrados: {len(docs)} (nenhum promove; nada sobe nem desce)")

    ja = {(m.get("nome"), m.get("uf")) for m in notas.get("municipios", [])}
    novos = 0
    for resp in respostas:
        nome = str(resp.get("municipio") or "").strip()
        if (nome, "RO") in ja:
            continue
        notas.setdefault("municipios", []).append(
            {"nome": nome, "uf": "RO",
             "situacao": "plano_informado" if tem_plano(resp) else "sem_plano_informado",
             "nota": nota_de_compdec(resp)})
        notas.setdefault("buscas_dirigidas", []).append(busca_dirigida(nome, "RO", DATA_RO))
        novos += 1
    # Espigão d'Oeste veio do ofício, não do formulário: o órgão disse que o plano está no sítio da
    # prefeitura. Mesma regra, mesma nota, e a busca dirigida é o que transforma isso em documento.
    if ("Espigão d'Oeste", "RO") not in ja:
        notas.setdefault("buscas_dirigidas", []).append(
            busca_dirigida("Espigão d'Oeste", "RO", DATA_RO))
    notas["documentos_de_estado"] = docs
    print(f"  notas de município novas: {novos}")
    if dry_run:
        print("(dry-run) nada gravado")
        return 0
    gravar("notas_lai.json", notas)
    return 0


def _autoteste() -> int:
    falhas = []
    # O total era um literal e envelhecia calado: dizia cobrir mais casos do que
    # cobre, ou menos. Agora e contado.
    _casos_contados = []

    def ok(nome, cond):
        _casos_contados.append(nome)
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    csv_teste = ("municipio,plano_vigente_5_1,quais_5_2,ano_atualizacao_5_3,natureza_5_4,"
                 "cadastro_s2id_4_1,mapeamento_risco_6_1,carimbo_data\n"
                 "Porto Velho,Sim,Estiagem,2025,Intersetorial,Sim,Sim,10/01/2026 08:00:00\n"
                 "Porto Velho,Não,,Não elaboramos o plano ainda,Não possui Plano,Sim,Não,"
                 "20/02/2026 09:00:00\n"
                 "Ariquemes,Sim,Plano Integrado,2026,Apenas formal (não operacionalizado),Sim,Sim,"
                 "05/02/2026 10:00:00\n"
                 "Vilhena,Não,,Não elaboramos o plano ainda,Não possui Plano,Sim,Não,"
                 "01/02/2026 11:00:00\n")
    rs = respostas_do_extrato(csv_teste)
    ok("duplicata colapsa num município só", len(rs) == 3)
    pv = [x for x in rs if x["municipio"] == "Porto Velho"][0]
    ok("vence a resposta mais recente, não a primeira do arquivo", not tem_plano(pv))
    ok("a ordem é alfabética, para o relatório ser conferível",
       [x["municipio"] for x in rs] == ["Ariquemes", "Porto Velho", "Vilhena"])

    n = nota_de_compdec([x for x in rs if x["municipio"] == "Ariquemes"][0])
    ok("a nota de quem tem plano traz o ano declarado", "em 2026" in n)
    ok("a nota diz que o documento não foi localizado, nunca que não existe",
       "ainda não foi localizado" in n and "não existe" not in n)
    ok("a nota de quem não tem plano é a outra, e não afirma nada além",
       nota_de_compdec(pv) == TEXTO_COMPDEC_SEM_PLANO)
    ok("campo de ano que não é ano não vira data falsa",
       "ano não declarado" in nota_de_compdec({"plano_vigente_5_1": "Sim",
                                               "ano_atualizacao_5_3": "não lembro"}))

    r = resumo(rs)
    ok("o resumo conta com e sem plano", r["com_plano"] == 1 and r["sem_plano"] == 2)
    ok("o resumo separa o 'apenas formal'", r["apenas_formal"] == 1)
    ok("o resumo não perde município", r["municipios"] == 3)

    ok("extrato vazio não quebra", respostas_do_extrato("") == [] and respostas_do_extrato(None) == [])

    b = busca_dirigida("Espigão d'Oeste", "RO", DATA_RO)
    ok("a busca dirigida é nível A e não finge ter documento",
       b["nivel"] == "A" and b["url"] is None)

    docs = documentos_do_estado()
    ok("são os quatro documentos lidos", len(docs) == 4)
    ok("nenhum documento é apresentado como promovido",
       all(d["veredito"] != "promove" for d in docs))
    ok("a nota do documento diz que ele não altera o índice",
       all("não altera o que o índice registra" in d["nota"] for d in docs))
    ok("cada documento carrega órgão, data de entrega e hash",
       all(d["orgao"] and d["entregue_em"] and d["sha256"] for d in docs))

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "aplicar", "main"):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não escrevem",
       not ({"gravar", "write_text"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv[1:]:
        return _autoteste()
    return aplicar(dry_run="--dry-run" in sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
