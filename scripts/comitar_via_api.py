#!/usr/bin/env python3
"""
scripts/comitar_via_api.py — commit do robô pela API do GitHub (AUD-21, 02/09/2026)
=====================================================================================
Commits criados pela API Git Data com o GITHUB_TOKEN saem **assinados e verificados
pelo GitHub** ("Verified"), ao contrário de `git commit` na runner. Este script pega o
que está no índice (`git add` já feito), cria blobs/árvore/commit pela API a partir do
HEAD atual e move a ref. Nenhuma credencial fora do token da Action.

Uso (na Action, com GITHUB_TOKEN e GITHUB_REPOSITORY no ambiente):
    python3 scripts/comitar_via_api.py --mensagem "Atualização automática de dados (dd/mm/aaaa)" --ref main
Sai 0 com "Sem alterações." quando o índice está limpo.
"""
import argparse, base64, json, os, subprocess, sys, urllib.request

API = "https://api.github.com"


def api(metodo, rota, token, dados=None):
    req = urllib.request.Request(API + rota, data=json.dumps(dados).encode() if dados is not None else None, method=metodo,
                                 headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                                          "Content-Type": "application/json", "User-Agent": "monitorelnino-robo"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read() or b"{}")


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--mensagem", required=True); ap.add_argument("--ref", default="main")
    a = ap.parse_args()
    token = os.environ["GITHUB_TOKEN"]; repo = os.environ["GITHUB_REPOSITORY"]
    linhas = [l for l in git("diff", "--cached", "--name-status").splitlines() if l.strip()]
    if not linhas:
        print("Sem alterações."); return 0
    head = git("rev-parse", "HEAD").strip()
    base_tree = api("GET", f"/repos/{repo}/git/commits/{head}", token)["tree"]["sha"]
    arvore = []
    for l in linhas:
        status, caminho = l.split("\t", 1)[0][0], l.split("\t", 1)[1]
        if status == "D":
            arvore.append({"path": caminho, "mode": "100644", "type": "blob", "sha": None}); continue
        conteudo = subprocess.run(["git", "show", f":{caminho}"], capture_output=True, check=True).stdout
        blob = api("POST", f"/repos/{repo}/git/blobs", token, {"content": base64.b64encode(conteudo).decode(), "encoding": "base64"})
        modo = "100755" if os.access(caminho, os.X_OK) else "100644"
        arvore.append({"path": caminho, "mode": modo, "type": "blob", "sha": blob["sha"]})
    tree = api("POST", f"/repos/{repo}/git/trees", token, {"base_tree": base_tree, "tree": arvore})
    commit = api("POST", f"/repos/{repo}/git/commits", token, {"message": a.mensagem, "tree": tree["sha"], "parents": [head]})
    api("PATCH", f"/repos/{repo}/git/refs/heads/{a.ref}", token, {"sha": commit["sha"], "force": False})
    print(f"commit {commit['sha'][:7]} criado pela API ({len(arvore)} arquivo[s]) e ref {a.ref} atualizada; verificação: {commit.get('verification', {}).get('verified')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
