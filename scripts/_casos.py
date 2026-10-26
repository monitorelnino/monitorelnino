"""Registro de casos dos autotestes: uma função `ok(nome, cond)` que imprime e acumula falhas."""


def ok_de(falhas, contados=None, marcas=("  ✓ ", "  ✗ ")):
    def ok(nome, cond):
        if contados is not None:
            contados.append(nome)
        print((marcas[0] if cond else marcas[1]) + nome)
        if not cond:
            falhas.append(nome)
    return ok
