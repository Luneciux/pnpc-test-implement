"""Backend FastAPI: serve o frontend e expõe a busca e as buscas salvas.

Rodar com:  uvicorn app:app --reload
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import pncp

STATIC_DIR = Path(__file__).resolve().parent / "static"
NOME_ARQUIVO = re.compile(r"^editais_\d{8}_\d{4}(_\d+)?\.json$")

app = FastAPI(title="Editais PNCP")


class FiltrosBusca(BaseModel):
    uf: str | None = None
    municipio_ibge: str | None = None
    modalidade: int | None = None
    data_final: str | None = Field(None, pattern=r"^\d{8}$")
    palavras_chave: list[str] | str | None = None
    max_paginas: int | None = Field(None, ge=1)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/buscar")
async def buscar(filtros: FiltrosBusca) -> dict:
    palavras = filtros.palavras_chave
    if isinstance(palavras, str):
        palavras = palavras.split(",")
    try:
        editais = await run_in_threadpool(
            pncp.buscar_editais,
            data_final=filtros.data_final,
            uf=filtros.uf or None,
            codigo_municipio_ibge=filtros.municipio_ibge or None,
            modalidade=filtros.modalidade,
            palavras_chave=palavras,
            max_paginas=filtros.max_paginas,
        )
    except pncp.PNCPError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    caminho = pncp.salvar(editais)
    return {"arquivo": caminho.name, "total": len(editais), "editais": editais}


@app.get("/api/arquivos")
def arquivos() -> list[dict]:
    return [
        {"nome": p.name, "tamanho_bytes": p.stat().st_size}
        for p in pncp.listar_arquivos()
    ]


@app.get("/api/arquivos/{nome}")
def arquivo(nome: str) -> dict:
    caminho = pncp.DATA_DIR / nome
    if not NOME_ARQUIVO.match(nome) or not caminho.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    editais = json.loads(caminho.read_text(encoding="utf-8"))
    return {"arquivo": nome, "total": len(editais), "editais": editais}


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
