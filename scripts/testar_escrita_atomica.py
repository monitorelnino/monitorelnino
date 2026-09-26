#!/usr/bin/env python3
"""Autoteste da escrita de `data/` (§209, 24/09/2026), sem rede e sem tocar no repositório.

Duas garantias, uma antiga e uma nova:

1. **Atômica** (21/09/2026): `gravar()` escreve num temporário e substitui, porque a versão
   que escrevia direto no arquivo final deixava JSON truncado a cada interrupção — foi assim
   que `fontes_consultadas.json` foi corrompido (368.019 → 166.961 linhas).

2. **Resiste ao cadeado do Windows** (24/09/2026): `os.replace()` falha com PermissionError
   (WinError 5) quando outro processo tem o destino aberto — o indexador do sistema e o
   antivírus abrem os JSON grandes de `data/` sozinhos, por um instante. Isso derrubou o
   `coletar_s2id` no meio da rodada nacional, em `evidencias.json`. A espera curta resolve;
   o que não pode é engolir o erro, porque falta de permissão de verdade tem de aparecer —
   e o temporário não pode ficar órfão ao lado do arquivo bom.
"""
import json
import pathlib
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import coletores_base as cb  # noqa: E402
from coletores_base import rodar_autoteste  # noqa: E402


class _Cofre:
    """Aponta `gravar()` para um diretório temporário e devolve tudo ao lugar no fim."""

    def __enter__(self):
        self.dir = tempfile.TemporaryDirectory()
        self.antigo_data, self.antigo_replace, self.antigo_sleep = cb.DATA, cb.os.replace, cb.time.sleep
        cb.DATA = pathlib.Path(self.dir.name)
        self.dormiu = []
        cb.time.sleep = lambda s: self.dormiu.append(s)
        return self

    def __exit__(self, *e):
        cb.DATA, cb.os.replace, cb.time.sleep = self.antigo_data, self.antigo_replace, self.antigo_sleep
        self.dir.cleanup()
        return False


def t_grava_e_rele():
    with _Cofre() as c:
        cb.gravar("x.json", {"a": 1})
        return json.loads((pathlib.Path(c.dir.name) / "x.json").read_text(encoding="utf-8"))["a"] == 1


def t_cadeado_momentaneo_nao_perde_a_escrita():
    """Duas recusas seguidas e depois sucesso: o arquivo chega inteiro, e houve espera."""
    with _Cofre() as c:
        real, falhas = c.antigo_replace, {"n": 0}

        def teimoso(a, b):
            falhas["n"] += 1
            if falhas["n"] <= 2:
                raise PermissionError(5, "Access is denied")
            return real(a, b)

        cb.os.replace = teimoso
        cb.gravar("y.json", {"b": 2})
        destino = pathlib.Path(c.dir.name) / "y.json"
        return (falhas["n"] == 3 and json.loads(destino.read_text(encoding="utf-8"))["b"] == 2
                and len(c.dormiu) == 2)


def t_permissao_de_verdade_levanta_e_nao_deixa_lixo():
    """Recusa que não passa nunca tem de aparecer — e sem deixar .tmp ao lado do arquivo bom."""
    with _Cofre() as c:
        cb.os.replace = lambda a, b: (_ for _ in ()).throw(PermissionError(5, "Access is denied"))
        try:
            cb.gravar("z.json", {"c": 3})
            return False
        except PermissionError:
            pass
        restos = list(pathlib.Path(c.dir.name).glob("z.json.tmp*"))
        return restos == []


def t_temporario_fica_no_mesmo_diretorio():
    """O temporário nasce ao lado do destino: em outro volume, os.replace não seria atômico."""
    with _Cofre() as c:
        vistos = []
        real = c.antigo_replace
        cb.os.replace = lambda a, b: (vistos.append((a, b)), real(a, b))[1]
        cb.gravar("w.json", {"d": 4})
        origem, destino = vistos[0]
        return pathlib.Path(origem).parent == pathlib.Path(destino).parent


# Escrita de JSON que NÃO passa pela porta atômica. Cada um destes está aqui com motivo
# declarado — a lista é curta de propósito, e crescer nela é decisão, não descuido.
FORA_DA_PORTA = {
    "coletores_base.py": "é a própria porta",
    "gerar_lai.py": "escreve no repositório PRIVADO da editoria, fora desta árvore",
    "gerar_dados_abertos.py": "derivado em dados-abertos/, conferido byte a byte pelo portão 12",
    "gerar_feeds.py": "index.json de feeds/ é derivado; os dois arquivos de data/ já migraram",
    "gerar_painel.py": "derivado do painel, conferido pelo portão 12",
    "verificar_robustez_atualizacao.py": "escreve FIXTURE de teste em diretório temporário",
    "testar_escrita_atomica.py": "é este arquivo: a própria expressão de busca casaria consigo",
}


def t_json_de_data_passa_pela_porta_atomica():
    """26/09/2026 (§229): nenhuma escrita de JSON em `data/` fora de `gravar`/`gravar_em`.

    A correção de 21/09/2026 entrou em `gravar()` e ficou lá. Uma auditoria de 26/09 encontrou
    **trinta e três escritas diretas** espalhadas pelo projeto, entre elas o `log_buscas.json`
    (o livro-razão de 24 MB), o `historico_mudancas.json` (o outro arquivo append-only), o
    `municipios.json` (o banco, por TRÊS portas diferentes), o `atos_resposta.json` e o próprio
    `indice.json` — e `julgar_e_aplicar_descobertas.py`, que grava cinco deles, roda no ciclo.

    A razão de terem ficado de fora é de projeto: `gravar()` pedia o NOME relativo a `data/`, e
    quem já tinha o caminho montado achava mais fácil abrir o arquivo. Daí `gravar_em(caminho)`.

    O que o teste lê é o texto do código, e é suficiente: a forma `json.dump(obj, open(...))` e a
    forma `caminho.write_text(json.dumps(...))` são as duas maneiras de escrever JSON sem passar
    pela porta, e as duas são reconhecíveis na linha."""
    import re
    padrao = re.compile(r'json\.dump\(\s*[^,]+,\s*open\(|\.write_text\(\s*json\.dumps')
    achados = []
    for arq in sorted(list(RAIZ.glob("*.py")) + list(RAIZ.glob("scripts/*.py"))):
        if arq.name in FORA_DA_PORTA:
            continue
        for n, linha in enumerate(arq.read_text(encoding="utf-8").splitlines(), 1):
            if padrao.search(linha.split("#", 1)[0]):
                achados.append(f"{arq.relative_to(RAIZ).as_posix()}:{n}")
    if achados:
        print("    escrita de JSON fora da porta atômica: " + ", ".join(achados[:8]))
        print("    Conserto: `from coletores_base import gravar_em` e `gravar_em(caminho, obj)`.")
        return False
    return True


if __name__ == "__main__":
    sys.exit(rodar_autoteste({
        "grava e relê o que gravou": t_grava_e_rele,
        "§209 cadeado momentâneo do Windows não perde a escrita": t_cadeado_momentaneo_nao_perde_a_escrita,
        "falta de permissão de verdade levanta, e não deixa .tmp órfão": t_permissao_de_verdade_levanta_e_nao_deixa_lixo,
        "o temporário nasce no mesmo diretório do destino": t_temporario_fica_no_mesmo_diretorio,
        "§229 nenhum JSON de data/ é escrito fora da porta atômica": t_json_de_data_passa_pela_porta_atomica,
    }))
