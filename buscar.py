"""CLI para buscar editais abertos no PNCP e salvar em data/.

Exemplo:
    python buscar.py --uf CE --modalidade 6 --palavras-chave "software,informática" --max-paginas 5
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter

import pncp


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Busca editais com propostas abertas no PNCP.")
    parser.add_argument("--uf", help="Sigla da UF (ex.: CE)")
    parser.add_argument("--municipio-ibge", help="Código IBGE do município (ex.: 2304400)")
    parser.add_argument(
        "--modalidade",
        type=int,
        help="Código da modalidade: " + ", ".join(f"{k} = {v}" for k, v in pncp.MODALIDADES.items()),
    )
    parser.add_argument(
        "--data-final",
        default=pncp.data_final_padrao(),
        help="Data final de encerramento das propostas, AAAAMMDD (padrão: hoje + 60 dias)",
    )
    parser.add_argument(
        "--palavras-chave",
        help="Palavras separadas por vírgula; mantém editais cujo objeto contenha qualquer uma",
    )
    parser.add_argument("--max-paginas", type=int, help="Limite de páginas (50 registros cada)")
    args = parser.parse_args(argv)

    palavras = [p.strip() for p in (args.palavras_chave or "").split(",") if p.strip()]

    def progresso(pagina: int, total: int, registros: int) -> None:
        print(f"  página {pagina}/{total} ({registros} registros no PNCP)", file=sys.stderr)

    print(f"Buscando no PNCP (data final {args.data_final})...", file=sys.stderr)
    try:
        editais = pncp.buscar_editais(
            data_final=args.data_final,
            uf=args.uf,
            codigo_municipio_ibge=args.municipio_ibge,
            modalidade=args.modalidade,
            palavras_chave=palavras,
            max_paginas=args.max_paginas,
            progresso=progresso,
        )
    except pncp.PNCPError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    caminho = pncp.salvar(editais)
    total_valor = sum(e["valor_estimado"] or 0 for e in editais)
    print(f"\n{len(editais)} editais salvos em {caminho}")
    print(f"Valor estimado somado: R$ {total_valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    for modalidade, qtd in Counter(e["modalidade"] for e in editais).most_common():
        print(f"  {qtd:5d}  {modalidade}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
