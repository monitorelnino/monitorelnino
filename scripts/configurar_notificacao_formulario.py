#!/usr/bin/env python3
"""Notificação por e-mail a cada envio do formulário `contribuicao`, pela API do Netlify.

Item 4 do handover do formulário mínimo (editoria, 30/09/2026, §311).

O QUE ESTE SCRIPT DECIDE, E O QUE ELE SE RECUSA A DECIDIR
--------------------------------------------------------
Ele **confere antes de criar**: se já existe notificação de e-mail para o formulário, não cria
outra. Notificação duplicada não é inofensiva — são dois e-mails por envio, e a editoria passa a
filtrar o próprio alerta.

Ele **não inventa endereço**. O destino vem do ambiente e é conferido contra o valor que a editoria
confirmou (`monitorelnino@gmail.com`, sem "h" — houve divergência de grafia no pedido original, e
errar aqui manda a notificação para uma caixa que ninguém lê, o que é pior do que não configurar).

Ele **falha com o erro exato** quando a API recusa, em vez de sair em silêncio: a configuração
manual é caminho previsto no handover, mas só serve se a editoria souber que precisa fazê-la.

USO
  NETLIFY_AUTH_TOKEN=... python3 scripts/configurar_notificacao_formulario.py
  python3 scripts/configurar_notificacao_formulario.py --autoteste
"""
import json
import os
import sys
import pathlib
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from coletores_base import ua_de  # noqa: E402 — o caminho precisa entrar antes do import

API = "https://api.netlify.com/api/v1"
FORMULARIO = "contribuicao"
DESTINO_CONFIRMADO = "monitorelnino@gmail.com"
SITIO = "monitorelnino.com.br"


def ja_existe(hooks: list, form_id: str, destino: str) -> bool:
    """True quando já há notificação de e-mail para ESTE formulário e ESTE destino. Função pura."""
    for h in hooks or []:
        if str(h.get("type")) != "email":
            continue
        if str(h.get("event")) not in ("submission_created", "submission_verified"):
            continue
        dados = h.get("data") or {}
        if form_id and str(h.get("form_id") or dados.get("form_id") or "") != str(form_id):
            continue
        if str(dados.get("email") or "").strip().lower() == destino.strip().lower():
            return True
    return False


def destino_valido(endereco: str) -> bool:
    """O endereço tem de ser exatamente o que a editoria confirmou. Função pura.

    Não é paranoia: o pedido original trazia outra grafia, e notificação para caixa errada é pior
    que notificação nenhuma — parece configurada e não chega."""
    return str(endereco or "").strip().lower() == DESTINO_CONFIRMADO


def pedir(caminho: str, token: str, dados: dict = None):
    req = urllib.request.Request(
        API + caminho,
        data=(json.dumps(dados).encode() if dados is not None else None),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                 # §185/§228: o cliente se identifica em toda requisição, inclusive numa API
                 # autenticada. Quem recebe o pedido tem direito de saber quem o fez.
                 "User-Agent": ua_de("notificação de e-mail do formulário de contribuição")},
        method=("POST" if dados is not None else "GET"))
    with urllib.request.urlopen(req, timeout=60) as r:
        corpo = r.read()
    return json.loads(corpo) if corpo else {}


def autoteste() -> int:
    casos = []
    f = "form123"
    casos.append(("destino confirmado passa", destino_valido("monitorelnino@gmail.com") is True))
    casos.append(("a grafia com 'h' NÃO passa — foi a divergência do pedido original",
                  destino_valido("monitorhelnino@gmail.com") is False))
    casos.append(("espaço e maiúscula não mudam o destino",
                  destino_valido("  MonitorElNino@Gmail.com ") is True))
    casos.append(("endereço vazio não passa", destino_valido("") is False))

    hook = {"type": "email", "event": "submission_created", "form_id": f,
            "data": {"email": DESTINO_CONFIRMADO}}
    casos.append(("notificação existente é reconhecida",
                  ja_existe([hook], f, DESTINO_CONFIRMADO) is True))
    casos.append(("de outro formulário não conta",
                  ja_existe([{**hook, "form_id": "outro"}], f, DESTINO_CONFIRMADO) is False))
    casos.append(("de outro destino não conta",
                  ja_existe([{**hook, "data": {"email": "x@y.com"}}], f, DESTINO_CONFIRMADO)
                  is False))
    casos.append(("de outro tipo (webhook, Slack) não conta",
                  ja_existe([{**hook, "type": "slack"}], f, DESTINO_CONFIRMADO) is False))
    casos.append(("lista vazia não confunde com existente",
                  ja_existe([], f, DESTINO_CONFIRMADO) is False))
    casos.append(("lista nula não quebra", ja_existe(None, f, DESTINO_CONFIRMADO) is False))
    casos.append(("submission_verified também conta",
                  ja_existe([{**hook, "event": "submission_verified"}], f, DESTINO_CONFIRMADO)
                  is True))

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
    destino = os.environ.get("DESTINO", DESTINO_CONFIRMADO)
    if not token:
        print("X NETLIFY_AUTH_TOKEN ausente — a configuração é manual, no painel do Netlify.")
        return 1
    if not destino_valido(destino):
        print(f"X destino {destino!r} não é o endereço confirmado pela editoria "
              f"({DESTINO_CONFIRMADO}). Nada foi criado.")
        return 1

    try:
        sites = pedir("/sites", token)
        alvo = next((s for s in sites if SITIO in (s.get("name", "") + s.get("url", ""))), None)
        if not alvo:
            print(f"X não achei o site {SITIO} entre os {len(sites)} da conta. Nada foi criado.")
            return 1
        formularios = pedir(f"/sites/{alvo['id']}/forms", token)
        form = next((f for f in formularios if f.get("name") == FORMULARIO), None)
        if not form:
            # Diagnóstico, não palpite. A primeira execução parou aqui dizendo "não existe ainda",
            # e isso não diz POR QUE. O Netlify detecta formulários no DEPLOY, lendo o HTML
            # publicado; se a detecção estiver desligada nas configurações do site, nenhum
            # formulário aparece, e a causa não é a falta de envio. Os dois casos pedem ações
            # diferentes da editoria, então o log diz qual é.
            nomes = [f.get("name") for f in formularios]
            print(f"X formulário {FORMULARIO!r} não está na lista do Netlify.")
            print(f"  Formulários detectados no site ({len(formularios)}): {nomes or 'nenhum'}")
            if not formularios:
                print("  NENHUM formulário detectado, embora o HTML publicado tenha um marcado com"
                      " `data-netlify`. Isso aponta para a detecção DESLIGADA em Site configuration"
                      " → Forms → Form detection. Ligue, refaça o deploy e rode este botão de novo.")
            else:
                print("  Outros formulários aparecem, então a detecção está ligada — este ainda não"
                      " foi detectado no último deploy, ou mudou de nome.")
            return 1
        hooks = pedir(f"/sites/{alvo['id']}/hooks", token)
        if ja_existe(hooks, form["id"], destino):
            print(f"OK a notificação para {destino} já existe — nada a fazer.")
            return 0
        pedir(f"/hooks?site_id={alvo['id']}", token, {
            "type": "email", "event": "submission_created", "form_id": form["id"],
            "data": {"email": destino}})
        print(f"OK notificação criada: e-mail para {destino} a cada envio de {FORMULARIO!r}.")
        return 0
    except urllib.error.HTTPError as e:
        print(f"X a API do Netlify recusou: HTTP {e.code} — {e.read()[:300]!r}")
        print("  Caminho manual: Site settings → Forms → Form notifications → Add notification → "
              f"Email notification → {DESTINO_CONFIRMADO}, marcado para o formulário {FORMULARIO!r}.")
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"X falha ao falar com a API do Netlify: {type(e).__name__} — {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
