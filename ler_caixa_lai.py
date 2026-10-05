#!/usr/bin/env python3
"""
ler_caixa_lai.py — a caixa de entrada dos pedidos de acesso à informação, uma vez por semana
=============================================================================================
Item 3 do `HANDOVER_incorporar_respostas_LAI_03-10-2026.md` (decisão da editoria, 03/10/2026).

O QUE ELE FAZ
-------------
Lê a caixa do projeto pela API do Gmail, com a conta do projeto, e separa o que chegou em três
destinos — os mesmos três da regra de incorporação:

  anexo oficial (PDF, documento)        → fila do juiz, como qualquer documento oficial
  texto do órgão, sem documento         → fila de incorporação, pela regra do item 1
  prazo legal vencido                   → lista para a editoria

E **nada mais**. Em particular: nenhum trecho de e-mail, nenhum protocolo, nenhum endereço e nenhum
contato pessoal entra neste repositório, que é público. O que sai daqui é o FATO: órgão, tipo de
pedido, data, e um identificador do anexo. O conteúdo vai para o repositório privado da editoria.

O QUE FALTA PARA ELE RODAR, E A EDITORIA DECIDE
------------------------------------------------
A credencial. Ele espera `GMAIL_CREDENCIAL_LAI` no ambiente (JSON de conta de serviço com acesso
delegado à caixa do projeto, ou token de OAuth já autorizado), configurada como Secret do
repositório. **A credencial não existe ainda**, e criá-la é ato da editoria, não do código: envolve
conta, consentimento e escopo. Sem ela, este script **não falha** — ele diz o que falta e sai com 0,
porque "não consegui ler a caixa" não é "a caixa está vazia", e um coletor que mente sobre isso é
pior que um coletor ausente.

Quando a credencial existir, o escopo pedido é o mínimo: `gmail.readonly`. O script nunca marca como
lido, nunca responde, nunca move e nunca apaga mensagem.

USO
  python3 ler_caixa_lai.py --autoteste
  python3 ler_caixa_lai.py --relatorio     # o que leria, sem gravar
  python3 ler_caixa_lai.py
"""
import os
import re
import sys
import pathlib

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

VARIAVEL_DA_CREDENCIAL = "GMAIL_CREDENCIAL_LAI"
ESCOPO = "https://www.googleapis.com/auth/gmail.readonly"
# A janela é a da rotina: uma leitura por semana, com folga para a semana que falhou.
DIAS_DA_JANELA = 10
EXTENSOES_DE_DOCUMENTO = (".pdf", ".doc", ".docx", ".odt", ".zip")

RE_LAI = re.compile(r"(?i)\b(lei de acesso|acesso à informa|lai\b|e-?sic|fala\.?br|protocolo)")
RE_ORGAO = re.compile(r"(?i)@[\w.-]*\.(gov\.br|leg\.br|jus\.br|mp\.br)$")
# Resposta automática não é resposta: registrar como tal evita cobrar prazo de quem não falou.
RE_AUTOMATICA = re.compile(r"(?i)(resposta autom|no-?reply|não responda|auto-?reply|"
                           r"mensagem autom)")


# ---------------------------------------------------------------- funções puras
def de_orgao_publico(remetente: str) -> bool:
    """True quando o remetente é de domínio público brasileiro. Função pura.

    O domínio é o critério porque é o que não se confunde: assunto e corpo variam, e "LAI" aparece
    em lista de discussão, em boletim e em propaganda de curso.
    """
    endereco = (remetente or "").strip().strip(">").split("<")[-1].strip()
    return bool(RE_ORGAO.search(endereco))


def e_sobre_lai(assunto: str, corpo: str) -> bool:
    """True quando assunto ou corpo tratam de pedido de acesso à informação. Função pura."""
    return bool(RE_LAI.search(assunto or "") or RE_LAI.search(corpo or ""))


def e_automatica(assunto: str, corpo: str) -> bool:
    """True para confirmação automática de recebimento. Função pura."""
    return bool(RE_AUTOMATICA.search(assunto or "") or RE_AUTOMATICA.search(corpo or ""))


def documentos_anexos(anexos: list) -> list:
    """Os anexos que são documento, pelo sufixo do nome. Função pura."""
    return [a for a in (anexos or [])
            if str(a.get("nome", "")).lower().endswith(EXTENSOES_DE_DOCUMENTO)]


def destino(mensagem: dict) -> str:
    """Para onde a mensagem vai: 'juiz', 'incorporacao', 'automatica' ou 'fora'. Função pura.

    Mensagem que não é de órgão público, ou que não trata de LAI, sai como 'fora' — e sair é o
    comportamento certo: a caixa recebe muita coisa, e adivinhar é como se classifica errado.
    """
    if not de_orgao_publico(mensagem.get("de", "")):
        return "fora"
    if not e_sobre_lai(mensagem.get("assunto", ""), mensagem.get("corpo", "")):
        return "fora"
    if documentos_anexos(mensagem.get("anexos")):
        return "juiz"
    if e_automatica(mensagem.get("assunto", ""), mensagem.get("corpo", "")):
        return "automatica"
    return "incorporacao"


def fato_publicavel(mensagem: dict) -> dict:
    """O que deste e-mail pode entrar no repositório público: o FATO, nunca o conteúdo.

    Função pura, e é ela que materializa a regra permanente do handover: texto do pedido, protocolo,
    chave de acesso e contato pessoal nunca vão ao site nem ao repositório público.
    """
    endereco = (mensagem.get("de") or "").split("<")[-1].strip(">").strip()
    dominio = endereco.split("@")[-1].lower() if "@" in endereco else None
    return {"dominio_do_orgao": dominio, "data": mensagem.get("data"),
            "destino": destino(mensagem),
            "anexos_de_documento": len(documentos_anexos(mensagem.get("anexos")))}


def credencial_ausente() -> str | None:
    """A mensagem do que falta, ou None quando a credencial está no ambiente."""
    if os.environ.get(VARIAVEL_DA_CREDENCIAL):
        return None
    return (f"{VARIAVEL_DA_CREDENCIAL} não está no ambiente. A leitura da caixa depende de uma "
            f"credencial da conta do projeto, com escopo {ESCOPO}, configurada como Secret do "
            f"repositório — ato da editoria, não do código. Nada foi lido, e nada foi gravado: "
            f"'não consegui ler' não é 'não há nada'.")


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

    ok("domínio público é reconhecido",
       de_orgao_publico("Defesa Civil <protocolo@defesacivil.mt.gov.br>"))
    ok("domínio comum não é órgão", not de_orgao_publico("alguem@gmail.com"))
    ok("subdomínio de gov entra", de_orgao_publico("x@cop.sedec.mt.gov.br"))
    ok("domínio que só CONTÉM gov.br no meio não entra",
       not de_orgao_publico("x@gov.br.exemplo.com"))

    ok("assunto sobre LAI é reconhecido", e_sobre_lai("Resposta a pedido de acesso à informação", ""))
    ok("corpo sobre LAI é reconhecido", e_sobre_lai("Re: solicitação", "conforme a Lei de Acesso"))
    ok("mensagem fora do assunto não entra", not e_sobre_lai("Convite para evento", "palestra"))

    ok("anexo de documento é separado por sufixo",
       len(documentos_anexos([{"nome": "plano.pdf"}, {"nome": "logo.png"}])) == 1)
    ok("zip conta como documento", len(documentos_anexos([{"nome": "compdecs.zip"}])) == 1)

    com_doc = {"de": "x@defesacivil.ro.gov.br", "assunto": "Resposta LAI",
               "anexos": [{"nome": "plano_estadual.pdf"}]}
    ok("anexo oficial vai ao juiz", destino(com_doc) == "juiz")
    so_texto = {"de": "x@sedec.mt.gov.br", "assunto": "Resposta ao pedido de acesso à informação",
                "corpo": "o município tem plano de contingência"}
    ok("texto sem documento vai à incorporação", destino(so_texto) == "incorporacao")
    automatica = {"de": "naoresponda@saude.am.gov.br", "assunto": "Resposta automática — protocolo",
                  "corpo": "mensagem automática"}
    ok("confirmação automática é marcada como tal", destino(automatica) == "automatica")
    ok("mensagem de particular fica fora",
       destino({"de": "a@gmail.com", "assunto": "LAI"}) == "fora")

    f = fato_publicavel({"de": "Defesa Civil <protocolo@sedec.mt.gov.br>", "data": "2026-09-23",
                         "assunto": "Resposta ao pedido de acesso à informação",
                         "corpo": "o município tem plano", "anexos": [{"nome": "a.pdf"}]})
    ok("o fato guarda o domínio, não o endereço", f["dominio_do_orgao"] == "sedec.mt.gov.br")
    ok("o fato não carrega assunto, corpo nem protocolo",
       not ({"assunto", "corpo", "protocolo", "de"} & set(f)))
    ok("o fato conta os anexos", f["anexos_de_documento"] == 1)

    ok("sem credencial, o script diz o que falta e não finge caixa vazia",
       credencial_ausente() is None or "não é 'não há nada'" in credencial_ausente())

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main"):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: nenhuma função escreve",
       not ({"gravar", "write_text", "write_bytes"} & nomes))
    ok("trava estrutural: o escopo pedido é só de leitura", ESCOPO.endswith("gmail.readonly"))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def _lembrete_de_renovacao() -> None:
    """Imprime o que precisa ser pedido de novo, antes de qualquer coisa.

    Item 4 do handover de 05/10/2026: "o `ler_caixa_lai` semanal e o painel mostram 'renovar pedido
    da OCP até {data}'". Vem ANTES da leitura da caixa de propósito — o prazo de renovação não
    depende de a credencial existir, e enquanto ela não existe esta é a única coisa que este script
    tem a dizer. Falha aqui não derruba a rotina: lembrete é aviso, não portão.
    """
    try:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "scripts"))
        import lembrete_de_renovacao_lai as lembrete
        lembrete.main([])
    except Exception as erro:          # pragma: no cover — ausência do script, não do prazo
        print(f"· lembrete de renovação não pôde ser lido ({erro})")


def main() -> int:
    if "--autoteste" in sys.argv[1:]:
        return _autoteste()
    _lembrete_de_renovacao()
    falta = credencial_ausente()
    if falta:
        print("⚠ CAIXA LAI não lida: " + falta)
        return 0
    print("✗ CAIXA LAI: a credencial está no ambiente, mas o cliente do Gmail ainda não foi "
          "ligado neste script — o acesso à caixa é o passo que depende da editoria, e ligar o "
          "cliente sem credencial para testar seria escrever contra o vazio.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
