#!/usr/bin/env python3
"""Decide se o site vai ao domínio agora (função pura, lê a lista de deploys do Netlify no stdin).

08/11/2026: o Netlify cobra 15 créditos por deploy de produção, e o publicador fazia ~25 por dia
(medido: 26 em 05/11, 25 em 06/11) — 375 créditos/dia contra 300/mês do plano Free e 1.000 do
Personal. Em 07/11 os créditos acabaram e o domínio congelou em 07/11 10:21 UTC. Prévia e branch
deploy custam zero; só a produção conta. Daqui em diante o domínio é reposto **no máximo uma vez por
janela** (JANELA_HORAS) e **só se o manifesto mudou** desde o último deploy que chegou ao ar.

Uso:
  python3 scripts/janela_de_deploy.py --manifesto <12 hex> [--alertas <12 hex>] [--agora <ISO 8601>] [--janela-horas 12] < deploys.json
  python3 scripts/janela_de_deploy.py --autoteste

Saída (uma linha, sempre exit 0 — quem decide o que fazer é repor_dominio.sh):
  DEPLOYAR                       nenhum deploy de produção no ar, ou janela aberta e manifesto novo
  IGUAL <hash>                   o domínio já serve este manifesto
  ADIADO <ISO da abertura>       manifesto novo, mas a janela do último deploy ainda não fechou

09/11/2026: a lista tem de vir FILTRADA a produção (`production: true`, página de 100). Na noite 08→09 a
página de 20 veio só com prévias (uma por commit automático na `main`), nenhum deploy de produção
apareceu, a decisão foi DEPLOYAR às 06:06 UTC com 9 h de janela — e o publicador gastou um deploy.
Deploy sem `manifesto=<hash>` no título (anteriores a esta regra) conta como manifesto diferente.
Lista vazia, inválida ou sem deploy `ready` de produção → DEPLOYAR (é o comportamento antigo, e o
próprio deploy dirá se o Netlify está fora)."""
import json
import re
import sys
from datetime import datetime, timedelta, timezone

JANELA_HORAS = 12
RE_MANIFESTO = re.compile(r"manifesto=([0-9a-f]{12})")
RE_ALERTAS = re.compile(r"alertas=([0-9a-f]{12})")


def _data(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def ultimo_deploy_no_ar(deploys):
    """O deploy de produção mais recente que chegou ao ar (`state == ready`)."""
    if not isinstance(deploys, list):
        return None
    no_ar = [d for d in deploys if isinstance(d, dict) and d.get("state") == "ready"
             and d.get("context", "production") == "production" and _data(d.get("published_at") or d.get("created_at"))]
    return max(no_ar, key=lambda d: _data(d.get("published_at") or d.get("created_at")), default=None)


def resumo(deploys) -> str:
    """Uma linha de diagnóstico: quantos deploys vieram e de que contexto (prévia × produção)."""
    if not isinstance(deploys, list):
        return "lista inválida"
    por = {}
    for d in deploys:
        if isinstance(d, dict):
            k = f"{d.get('context', '?')}/{d.get('state', '?')}"
            por[k] = por.get(k, 0) + 1
    return f"{len(deploys)} deploy(s) na lista: " + ", ".join(f"{k}={v}" for k, v in sorted(por.items()))


def decidir(deploys, manifesto, agora, janela_horas=JANELA_HORAS, alertas=None):
    """`alertas` (09/11/2026, editoria): o hash de `data/alertas/vigentes.json`. Alerta do Inmet ou do
    Cemaden mudou desde o último deploy → DEPLOYAR mesmo dentro da janela — é para isso que o elo
    diurno existe. Sem hash de alertas no título do último deploy, só o manifesto decide."""
    u = ultimo_deploy_no_ar(deploys)
    if u is None:
        return "DEPLOYAR"
    titulo = str(u.get("title") or "")
    m = RE_MANIFESTO.search(titulo)
    if m and m.group(1) == manifesto:
        return f"IGUAL {manifesto}"
    al = RE_ALERTAS.search(titulo)
    if alertas and al and al.group(1) != alertas:
        return "DEPLOYAR"
    abre = _data(u.get("published_at") or u.get("created_at")) + timedelta(hours=janela_horas)
    if agora < abre:
        return "ADIADO " + abre.strftime("%Y-%m-%dT%H:%MZ")
    return "DEPLOYAR"


def autoteste() -> int:
    T = "2026-11-08T20:00:00Z"
    agora = _data(T)
    d = lambda t, title="x", state="ready": {"state": state, "context": "production", "published_at": t, "title": title}
    casos = [
        ("sem deploy no ar → DEPLOYAR", decidir([], "abc123abc123", agora) == "DEPLOYAR"),
        ("lista inválida → DEPLOYAR", decidir("lixo", "abc123abc123", agora) == "DEPLOYAR"),
        ("só deploys com erro → DEPLOYAR", decidir([d("2026-11-08T19:00:00Z", state="error")], "abc123abc123", agora) == "DEPLOYAR"),
        ("mesmo manifesto → IGUAL", decidir([d("2026-11-08T19:00:00Z", "Publicação · manifesto=abc123abc123")], "abc123abc123", agora) == "IGUAL abc123abc123"),
        ("manifesto novo dentro da janela → ADIADO na hora certa",
         decidir([d("2026-11-08T19:00:00Z", "Publicação · manifesto=000000000000")], "abc123abc123", agora) == "ADIADO 2026-11-09T07:00Z"),
        ("manifesto novo, janela fechada → DEPLOYAR", decidir([d("2026-11-08T07:59:00Z", "manifesto=000000000000")], "abc123abc123", agora) == "DEPLOYAR"),
        ("deploy antigo sem hash no título conta como diferente", decidir([d("2026-11-08T19:00:00Z", "Publicação 1a2b3c4")], "abc123abc123", agora).startswith("ADIADO")),
        ("o mais recente decide, não a ordem da lista",
         decidir([d("2026-11-08T07:00:00Z", "manifesto=000000000000"), d("2026-11-08T19:30:00Z", "manifesto=abc123abc123")], "abc123abc123", agora) == "IGUAL abc123abc123"),
        ("janela configurável", decidir([d("2026-11-08T19:00:00Z", "manifesto=000000000000")], "abc123abc123", agora, janela_horas=0.5) == "DEPLOYAR"),
        ("prévia (context deploy-preview) não conta", decidir([{"state": "ready", "context": "deploy-preview", "published_at": "2026-11-08T19:00:00Z", "title": "manifesto=000000000000"}], "abc123abc123", agora) == "DEPLOYAR"),
        ("alertas novos dentro da janela → DEPLOYAR",
         decidir([d("2026-11-08T19:00:00Z", "Publicação · manifesto=000000000000 · alertas=aaaaaaaaaaaa")], "abc123abc123", agora, alertas="bbbbbbbbbbbb") == "DEPLOYAR"),
        ("alertas iguais dentro da janela → ADIADO",
         decidir([d("2026-11-08T19:00:00Z", "Publicação · manifesto=000000000000 · alertas=aaaaaaaaaaaa")], "abc123abc123", agora, alertas="aaaaaaaaaaaa").startswith("ADIADO")),
        ("último deploy sem hash de alertas → só o manifesto decide (ADIADO)",
         decidir([d("2026-11-08T19:00:00Z", "Publicação · manifesto=000000000000")], "abc123abc123", agora, alertas="bbbbbbbbbbbb").startswith("ADIADO")),
        ("resumo conta por contexto", resumo([{"state": "ready", "context": "deploy-preview"}, {"state": "ready", "context": "production"}, {"state": "ready", "context": "deploy-preview"}]) == "3 deploy(s) na lista: deploy-preview/ready=2, production/ready=1"),
    ]
    falhas = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(("  OK   " if ok else "  FALHOU ") + n)
    print(f"{'OK' if not falhas else 'FALHOU'} AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main(argv) -> int:
    if "--autoteste" in argv:
        return autoteste()
    manifesto = argv[argv.index("--manifesto") + 1] if "--manifesto" in argv else ""
    agora = _data(argv[argv.index("--agora") + 1]) if "--agora" in argv else datetime.now(timezone.utc)
    janela = float(argv[argv.index("--janela-horas") + 1]) if "--janela-horas" in argv else JANELA_HORAS
    alertas = argv[argv.index("--alertas") + 1] if "--alertas" in argv else None
    try:
        deploys = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        deploys = []
    print(resumo(deploys), file=sys.stderr)
    print(decidir(deploys, manifesto, agora, janela, alertas))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
