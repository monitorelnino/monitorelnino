#!/usr/bin/env python3
"""Teste de ponta a ponta do formulário `contribuicao`: envia, confere, apaga.

Passos 4 e 5 do handover de 30/09/2026 (Netlify Forms). Os três acontecem na mesma execução, de
propósito: submissão de teste que fica é submissão que entra na fila de `verificar_contribuicoes.py`
e vira trabalho humano sobre um dado inventado. **O teste se limpa ou falha dizendo que não limpou.**

POR QUE ISTO RODA NO CI, E NÃO NA MÁQUINA DE QUEM ESCREVE
---------------------------------------------------------
O sítio está atrás de Basic-Auth (o regime de cortina), e a credencial é segredo do GitHub. O envio
precisa passar por ela; a leitura e a limpeza precisam do `NETLIFY_AUTH_TOKEN`. Nenhum dos dois está
— nem deve estar — na máquina local.

O QUE ELE NÃO FAZ
-----------------
Não confirma que o e-mail chegou: a caixa é da editoria. Ele confirma que o Netlify **registrou** a
submissão e que a notificação existe; o resto é olhar a caixa.

USO
  python3 scripts/testar_formulario_ponta_a_ponta.py --autoteste
  NETLIFY_AUTH_TOKEN=... PREVIA_BASIC_AUTH=user:senha python3 scripts/testar_formulario_ponta_a_ponta.py
"""
import base64
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from coletores_base import ua_de  # noqa: E402 — o caminho precisa entrar antes do import

API = "https://api.netlify.com/api/v1"
SITIO = "monitorelnino.com.br"
FORMULARIO = "contribuicao"
MARCA = "teste automatizado 30/09 — descartar"

CAMPOS_DE_TESTE = {
    "form-name": FORMULARIO,
    "uf": "SP",
    "municipio": "TESTE-CENTRAL",
    "tipo": "plano",
    "link_oficial": "https://www.in.gov.br/",
    "observacoes": MARCA,
}


def eh_a_submissao_de_teste(sub: dict) -> bool:
    """True só para a submissão que ESTE teste criou. Função pura.

    A conferência é pelo conteúdo, não pela posição na lista: apagar "a mais recente" apagaria a
    contribuição de um cidadão que chegasse no mesmo minuto. O município de teste e a marca nas
    observações têm de bater os dois."""
    dados = (sub or {}).get("data") or {}
    return (str(dados.get("municipio", "")).strip() == "TESTE-CENTRAL"
            and MARCA in str(dados.get("observacoes", "")))


def campos_do_formulario(form: dict) -> set:
    """Os nomes de campo que o Netlify detectou. Função pura."""
    return {str(c.get("name") or "") for c in (form or {}).get("fields") or []}


def pedir(caminho: str, token: str, dados: dict = None, metodo: str = None):
    req = urllib.request.Request(
        API + caminho,
        data=(json.dumps(dados).encode() if dados is not None else None),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                 "User-Agent": ua_de("teste de ponta a ponta do formulário")},
        method=(metodo or ("POST" if dados is not None else "GET")))
    with urllib.request.urlopen(req, timeout=60) as r:
        corpo = r.read()
    return json.loads(corpo) if corpo else {}


def enviar(credencial: str) -> int:
    """Faz o POST no formulário publicado, atravessando a cortina. Devolve o status HTTP."""
    corpo = urllib.parse.urlencode(CAMPOS_DE_TESTE).encode()
    cab = {"Content-Type": "application/x-www-form-urlencoded",
           "User-Agent": ua_de("teste de ponta a ponta do formulário")}
    if credencial:
        cab["Authorization"] = "Basic " + base64.b64encode(credencial.encode()).decode()
    req = urllib.request.Request(f"https://{SITIO}/", data=corpo, headers=cab, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def autoteste() -> int:
    casos = []
    boa = {"data": {"municipio": "TESTE-CENTRAL", "observacoes": MARCA}}
    casos.append(("reconhece a submissão de teste", eh_a_submissao_de_teste(boa) is True))
    casos.append(("município certo, sem a marca, NÃO é a de teste",
                  eh_a_submissao_de_teste({"data": {"municipio": "TESTE-CENTRAL",
                                                    "observacoes": "plano real"}}) is False))
    casos.append(("marca certa, outro município, NÃO é a de teste",
                  eh_a_submissao_de_teste({"data": {"municipio": "Campinas",
                                                    "observacoes": MARCA}}) is False))
    casos.append(("submissão de cidadão nunca é confundida",
                  eh_a_submissao_de_teste({"data": {"municipio": "Serra",
                                                    "observacoes": ""}}) is False))
    casos.append(("submissão vazia não quebra", eh_a_submissao_de_teste({}) is False))
    casos.append(("submissão nula não quebra", eh_a_submissao_de_teste(None) is False))
    casos.append(("espaço em volta do município não engana",
                  eh_a_submissao_de_teste({"data": {"municipio": "  TESTE-CENTRAL ",
                                                    "observacoes": MARCA}}) is True))

    casos.append(("lê os campos detectados",
                  campos_do_formulario({"fields": [{"name": "uf"}, {"name": "municipio"}]})
                  == {"uf", "municipio"}))
    casos.append(("formulário sem campos não quebra", campos_do_formulario({}) == set()))
    casos.append(("o envio de teste NÃO leva e-mail de contato",
                  "email_contato" not in CAMPOS_DE_TESTE))
    casos.append(("o envio de teste se identifica nas observações",
                  "descartar" in CAMPOS_DE_TESTE["observacoes"]))

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

    token = os.environ.get("NETLIFY_AUTH_TOKEN", "")
    credencial = os.environ.get("PREVIA_BASIC_AUTH", "")
    if not token:
        print("X NETLIFY_AUTH_TOKEN ausente.")
        return 1

    sites = pedir("/sites", token)
    alvo = next((s for s in sites if SITIO in (s.get("name", "") + s.get("url", ""))), None)
    if not alvo:
        print(f"X não achei o site {SITIO}.")
        return 1
    print(f"sítio: {alvo.get('name')} ({alvo.get('id')})")

    formularios = pedir(f"/sites/{alvo['id']}/forms", token)
    form = next((f for f in formularios if f.get("name") == FORMULARIO), None)
    if not form:
        print(f"X formulário {FORMULARIO!r} não detectado: {[f.get('name') for f in formularios]}")
        return 1
    campos = campos_do_formulario(form)
    print(f"formulário detectado: {form['id']} · campos: {sorted(campos)}")
    if "email_contato" in campos:
        print("X o formulário detectado ainda traz `email_contato` — o deploy é anterior ao §311.")
        return 1

    hooks = pedir(f"/hooks?site_id={alvo['id']}", token)
    notificacoes = [h for h in hooks if str(h.get("type")) == "email"]
    print(f"notificações de e-mail no sítio: {len(notificacoes)}")

    status = enviar(credencial)
    print(f"envio de teste: HTTP {status}")
    if status >= 400:
        print("X o envio não passou. Sem credencial da cortina, o sítio responde 401.")
        return 1

    # A indexação não é instantânea, e a submissão pode cair na fila de SPAM em vez da normal — um
    # POST sem JavaScript, sem referer e vindo de um runner tem exatamente a cara que o filtro
    # procura. Olhar só a fila normal, uma vez, dava "não registrou" para envio que registrou.
    minhas, subs, onde = [], [], ""
    for tentativa in range(6):
        for estado in ("", "?state=spam"):
            subs = pedir(f"/forms/{form['id']}/submissions{estado}", token)
            achadas = [x for x in subs if eh_a_submissao_de_teste(x)]
            if achadas:
                minhas, onde = achadas, ("spam" if estado else "normal")
                break
        if minhas:
            break
        print(f"  ainda não indexada (tentativa {tentativa + 1}/6); esperando 10 s", flush=True)
        time.sleep(10)
    print(f"submissões de teste encontradas: {len(minhas)} · fila: {onde or '—'}")
    if not minhas:
        print("X a submissão não apareceu na API, nem na fila normal nem na de spam.")
        print("  O envio devolveu 200, então o sítio aceitou o POST — o que falta é o Netlify")
        print("  processá-lo como formulário. Conferir no painel se o deploy atual detectou o form.")
        return 1

    # A limpeza varre em rodadas até não sobrar nenhuma. Execuções anteriores podem ter deixado
    # submissões de teste que só foram indexadas depois — apagar "as que eu vi" deixava resto.
    apagadas, restantes = 0, []
    for _ in range(4):
        restantes = [x for e in ("", "?state=spam")
                     for x in pedir(f"/forms/{form['id']}/submissions{e}", token)
                     if eh_a_submissao_de_teste(x)]
        if not restantes:
            break
        for sub in restantes:
            pedir(f"/submissions/{sub['id']}", token, metodo="DELETE")
            apagadas += 1
        time.sleep(5)
    print(f"submissões de teste apagadas: {apagadas}")
    if restantes:
        print(f"X ainda restam {len(restantes)} submissões de teste — limpe pelo painel.")
        return 1
    print("OK ponta a ponta: enviado, registrado, conferido e limpo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
