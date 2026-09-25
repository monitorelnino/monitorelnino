#!/usr/bin/env python3
"""Autoteste dos lotes de escrita de `data/` (§209 e §212), sem rede e sem tocar no repositório.

POR QUE EXISTEM. Dois arquivos do projeto são lidos e regravados a cada município consultado:
`log_buscas.json` (20 MB) e `fontes_consultadas.json` (12 MB). A 27 capitais isso é irrelevante;
numa varredura de 2.965 municípios são dezenas de gigabytes de entrada e saída e outras tantas
janelas em que uma interrupção deixa o arquivo pela metade — foi assim que
`fontes_consultadas.json` foi corrompido em 21/09/2026.

A saída é um lote OPCIONAL, com teto: acumula em memória e descarrega de 250 em 250. O que estes
testes travam é o que não pode falhar em nenhuma das duas:
  · sem abrir lote, o comportamento é exatamente o de antes (uma gravação por chamada);
  · com lote aberto, nada se perde — o que foi acumulado chega ao arquivo ao fechar;
  · o teto existe de verdade, porque ele é o limite do que uma interrupção levaria embora;
  · fechar duas vezes não duplica nada.
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
    """Aponta `data/` para um diretório temporário e devolve tudo ao lugar no fim."""

    def __enter__(self):
        self.dir = tempfile.TemporaryDirectory()
        self.antigo = cb.DATA
        cb.DATA = pathlib.Path(self.dir.name)
        (cb.DATA / "log_buscas.json").write_text(
            json.dumps({"formato_versao": 2, "execucoes": []}), encoding="utf-8", newline="\n")
        self.gravacoes = []
        self.gravar_real = cb.gravar
        cb.gravar = lambda nome, obj: (self.gravacoes.append(nome), self.gravar_real(nome, obj))[1]
        return self

    def __exit__(self, *e):
        cb.fechar_lote_log()
        cb.fechar_lote_livro()
        cb.gravar = self.gravar_real
        cb.DATA = self.antigo
        self.dir.cleanup()
        return False

    def gravacoes_de(self, nome):
        return [g for g in self.gravacoes if g == nome]


def _log(c, n):
    for i in range(n):
        cb.log_busca("DOM", 1, ["x"], "consultado sem achado", resultados=f"m{i}")


def _execucoes(c):
    return len(json.loads((cb.DATA / "log_buscas.json").read_text(encoding="utf-8"))["execucoes"])


def _municipios():
    p = cb.DATA / "fontes_consultadas.json"
    return len(json.loads(p.read_text(encoding="utf-8"))["municipios"]) if p.exists() else 0


def t_log_sem_lote_grava_a_cada_chamada():
    with _Cofre() as c:
        _log(c, 5)
        return len(c.gravacoes_de("log_buscas.json")) == 5 and _execucoes(c) == 5


def t_log_com_lote_grava_uma_vez_ao_fechar():
    with _Cofre() as c:
        cb.abrir_lote_log()
        _log(c, 5)
        gravou_durante = len(c.gravacoes_de("log_buscas.json"))
        cb.fechar_lote_log()
        return gravou_durante == 0 and len(c.gravacoes_de("log_buscas.json")) == 1 and _execucoes(c) == 5


def t_log_nada_se_perde_no_teto():
    """O teto não é otimização: é o limite do que uma interrupção levaria embora. Com 250 de teto,
    600 execuções descarregam duas vezes no caminho e o resto ao fechar — e as 600 chegam."""
    with _Cofre() as c:
        cb.abrir_lote_log()
        _log(c, 600)
        no_meio = len(c.gravacoes_de("log_buscas.json"))
        cb.fechar_lote_log()
        return no_meio == 2 and _execucoes(c) == 600


def t_log_fechar_duas_vezes_nao_duplica():
    with _Cofre() as c:
        cb.abrir_lote_log()
        _log(c, 3)
        cb.fechar_lote_log()
        cb.fechar_lote_log()
        return _execucoes(c) == 3


def t_livro_sem_lote_grava_a_cada_chamada():
    with _Cofre() as c:
        for i in range(4):
            cb.marcar_fonte_consultada([f"110000{i}"], "fonte", "nao_verificado")
        return len(c.gravacoes_de("fontes_consultadas.json")) == 4 and _municipios() == 4


def t_livro_com_lote_grava_uma_vez_ao_fechar():
    with _Cofre() as c:
        cb.abrir_lote_livro()
        for i in range(4):
            cb.marcar_fonte_consultada([f"110000{i}"], "fonte", "nao_verificado")
        gravou_durante = len(c.gravacoes_de("fontes_consultadas.json"))
        cb.fechar_lote_livro()
        return gravou_durante == 0 and _municipios() == 4


def t_livro_nada_se_perde_no_teto():
    with _Cofre() as c:
        cb.abrir_lote_livro()
        for i in range(600):
            cb.marcar_fonte_consultada([str(1100000 + i)], "fonte", "nao_verificado")
        no_meio = len(c.gravacoes_de("fontes_consultadas.json"))
        cb.fechar_lote_livro()
        return no_meio == 2 and _municipios() == 600


def t_livro_nivel_nunca_rebaixa_nem_com_lote():
    """A regra de fundo do livro — nível só sobe — tem de valer igual com o lote aberto."""
    with _Cofre() as c:
        cb.abrir_lote_livro()
        cb.marcar_fonte_consultada(["1100001"], "a", "estadual")
        cb.marcar_fonte_consultada(["1100001"], "b", "nao_verificado")
        cb.fechar_lote_livro()
        livro = json.loads((cb.DATA / "fontes_consultadas.json").read_text(encoding="utf-8"))
        return livro["municipios"]["1100001"]["nivel_verificacao"] == "estadual"


def t_livro_fato_municipal_tambem_entra_no_lote():
    with _Cofre() as c:
        cb.abrir_lote_livro()
        cb.marcar_fato_municipal("1100001", "decreto_reconhecido", True)
        durante = len(c.gravacoes_de("fontes_consultadas.json"))
        cb.fechar_lote_livro()
        livro = json.loads((cb.DATA / "fontes_consultadas.json").read_text(encoding="utf-8"))
        return durante == 0 and livro["municipios"]["1100001"]["decreto_reconhecido"] is True


if __name__ == "__main__":
    sys.exit(rodar_autoteste({
        "log sem lote: uma gravação por chamada (comportamento antigo intacto)": t_log_sem_lote_grava_a_cada_chamada,
        "log com lote: nada é gravado até fechar, e tudo chega": t_log_com_lote_grava_uma_vez_ao_fechar,
        "§209 log: o teto descarrega no caminho e nada se perde": t_log_nada_se_perde_no_teto,
        "log: fechar duas vezes não duplica": t_log_fechar_duas_vezes_nao_duplica,
        "livro sem lote: uma gravação por chamada (comportamento antigo intacto)": t_livro_sem_lote_grava_a_cada_chamada,
        "livro com lote: nada é gravado até fechar, e tudo chega": t_livro_com_lote_grava_uma_vez_ao_fechar,
        "§212 livro: o teto descarrega no caminho e nada se perde": t_livro_nada_se_perde_no_teto,
        "livro: nível de verificação nunca rebaixa, nem com lote aberto": t_livro_nivel_nunca_rebaixa_nem_com_lote,
        "livro: fato municipal também entra no lote": t_livro_fato_municipal_tambem_entra_no_lote,
    }))
