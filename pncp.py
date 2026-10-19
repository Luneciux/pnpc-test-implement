"""Busca de editais com propostas abertas na API pública de consulta do PNCP."""

from __future__ import annotations

import json
import time
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable, Iterable

import requests

API_URL = "https://pncp.gov.br/api/consulta/v1/contratacoes/proposta"
HEADERS = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
PORTAL_EDITAL_URL = "https://pncp.gov.br/app/editais/{cnpj}/{ano}/{sequencial}"
DATA_DIR = Path(__file__).resolve().parent / "data"

MODALIDADES = {
    4: "Concorrência - Eletrônica",
    6: "Pregão - Eletrônico",
    8: "Dispensa",
}

TAMANHO_PAGINA = 50
PAUSA_ENTRE_REQUISICOES = 0.5  # segundos
TENTATIVAS = 3
TIMEOUT = 60


class PNCPError(RuntimeError):
    pass


def data_final_padrao() -> str:
    return (date.today() + timedelta(days=60)).strftime("%Y%m%d")


def normalizar_texto(texto: str | None) -> str:
    """Minúsculas e sem acentos, para comparação de palavras-chave."""
    sem_acento = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in sem_acento if not unicodedata.combining(c)).casefold()


def _get_pagina(params: dict) -> dict:
    ultimo_erro: Exception | None = None
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=TIMEOUT)
            # 204 = nenhum resultado para os filtros
            if resp.status_code == 204:
                return {"data": [], "totalPaginas": 0, "totalRegistros": 0}
            if 400 <= resp.status_code < 500 and resp.status_code != 429:
                # erro do cliente (parâmetro inválido): não adianta repetir
                raise PNCPError(f"HTTP {resp.status_code}: {resp.text[:500]}")
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as exc:
            ultimo_erro = exc
            if tentativa < TENTATIVAS:
                time.sleep(2 * tentativa)
    raise PNCPError(f"Falha ao consultar o PNCP ({params}): {ultimo_erro}")


def buscar_registros(
    data_final: str | None = None,
    uf: str | None = None,
    codigo_municipio_ibge: str | None = None,
    modalidade: int | None = None,
    max_paginas: int | None = None,
    tamanho_pagina: int = TAMANHO_PAGINA,
    progresso: Callable[[int, int, int], None] | None = None,
) -> list[dict]:
    """Retorna os registros brutos, paginando até totalPaginas ou max_paginas."""
    params: dict = {
        "dataFinal": data_final or data_final_padrao(),
        "tamanhoPagina": max(10, min(50, tamanho_pagina)),
    }
    if uf:
        params["uf"] = uf.upper()
    if codigo_municipio_ibge:
        params["codigoMunicipioIbge"] = codigo_municipio_ibge
    if modalidade:
        params["codigoModalidadeContratacao"] = int(modalidade)

    registros: list[dict] = []
    pagina = 1
    while True:
        resposta = _get_pagina({**params, "pagina": pagina})
        registros.extend(resposta.get("data") or [])
        total_paginas = resposta.get("totalPaginas") or 0
        if progresso:
            progresso(pagina, total_paginas, resposta.get("totalRegistros") or 0)
        if pagina >= total_paginas or (max_paginas and pagina >= max_paginas):
            break
        pagina += 1
        time.sleep(PAUSA_ENTRE_REQUISICOES)
    return registros


def filtrar_palavras_chave(registros: Iterable[dict], palavras: Iterable[str] | None) -> list[dict]:
    """Mantém registros cujo objetoCompra contém QUALQUER uma das palavras (sem caixa/acentos)."""
    termos = [normalizar_texto(p).strip() for p in (palavras or [])]
    termos = [t for t in termos if t]
    if not termos:
        return list(registros)
    return [r for r in registros if any(t in normalizar_texto(r.get("objetoCompra")) for t in termos)]


def resumir(r: dict) -> dict:
    """Converte um registro bruto no formato enxuto salvo em data/."""
    orgao = r.get("orgaoEntidade") or {}
    unidade = r.get("unidadeOrgao") or {}
    cnpj = orgao.get("cnpj")
    ano = r.get("anoCompra")
    seq = r.get("sequencialCompra")
    return {
        "id": r.get("numeroControlePNCP"),
        "orgao": orgao.get("razaoSocial"),
        "cnpj": cnpj,
        "municipio": unidade.get("municipioNome"),
        "uf": unidade.get("ufSigla"),
        "modalidade": r.get("modalidadeNome"),
        "objeto": r.get("objetoCompra"),
        "valor_estimado": r.get("valorTotalEstimado"),
        "data_abertura_proposta": r.get("dataAberturaProposta"),
        "data_encerramento_proposta": r.get("dataEncerramentoProposta"),
        "link_edital": PORTAL_EDITAL_URL.format(cnpj=cnpj, ano=ano, sequencial=seq)
        if cnpj and ano and seq
        else None,
        "raw": r,
    }


def buscar_editais(
    data_final: str | None = None,
    uf: str | None = None,
    codigo_municipio_ibge: str | None = None,
    modalidade: int | None = None,
    palavras_chave: Iterable[str] | None = None,
    max_paginas: int | None = None,
    progresso: Callable[[int, int, int], None] | None = None,
) -> list[dict]:
    registros = buscar_registros(
        data_final=data_final,
        uf=uf,
        codigo_municipio_ibge=codigo_municipio_ibge,
        modalidade=modalidade,
        max_paginas=max_paginas,
        progresso=progresso,
    )
    return [resumir(r) for r in filtrar_palavras_chave(registros, palavras_chave)]


def salvar(editais: list[dict], diretorio: Path = DATA_DIR) -> Path:
    diretorio.mkdir(parents=True, exist_ok=True)
    base = f"editais_{datetime.now():%Y%m%d_%H%M}"
    caminho = diretorio / f"{base}.json"
    n = 2
    while caminho.exists():  # duas buscas no mesmo minuto não se sobrescrevem
        caminho = diretorio / f"{base}_{n}.json"
        n += 1
    caminho.write_text(json.dumps(editais, ensure_ascii=False, indent=2), encoding="utf-8")
    return caminho


def listar_arquivos(diretorio: Path = DATA_DIR) -> list[Path]:
    if not diretorio.exists():
        return []
    return sorted(diretorio.glob("editais_*.json"), reverse=True)
