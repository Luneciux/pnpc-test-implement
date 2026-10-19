# Editais PNCP

Busca editais de licitação com propostas abertas na [API pública do PNCP](https://pncp.gov.br/api/consulta/swagger-ui/index.html),
salva os resultados em JSON (`data/`) e mostra tudo num frontend web com filtros, resumo,
ordenação e exportação CSV.

## Instalação

Requer Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Frontend + API

```bash
uvicorn app:app --reload
```

Abra http://localhost:8000. No topo ficam os filtros (UF, município IBGE, modalidade, data final,
palavras-chave, máximo de páginas). Cada busca é salva em `data/` e pode ser reaberta pelo seletor
"Buscas salvas".

Endpoints:

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/buscar` | Corpo JSON com `uf`, `municipio_ibge`, `modalidade`, `data_final` (AAAAMMDD), `palavras_chave` (lista ou texto separado por vírgula), `max_paginas`. Busca, salva e retorna `{arquivo, total, editais}`. |
| `GET` | `/api/arquivos` | Lista as buscas salvas. |
| `GET` | `/api/arquivos/{nome}` | Carrega uma busca salva. |

```bash
curl -X POST localhost:8000/api/buscar -H 'Content-Type: application/json' \
  -d '{"uf":"CE","modalidade":6,"palavras_chave":"software,sistema","max_paginas":3}'
curl localhost:8000/api/arquivos
```

## CLI

```bash
python buscar.py --uf CE
python buscar.py --uf SP --modalidade 6 --palavras-chave "limpeza,conservação" --max-paginas 10
python buscar.py --municipio-ibge 2304400 --data-final 20261231
```

| Opção | Descrição |
|---|---|
| `--uf` | Sigla da UF |
| `--municipio-ibge` | Código IBGE do município (7 dígitos) |
| `--modalidade` | 6 = pregão eletrônico, 8 = dispensa, 4 = concorrência eletrônica |
| `--data-final` | AAAAMMDD; propostas que encerram até essa data (padrão: hoje + 60 dias) |
| `--palavras-chave` | Separadas por vírgula; casa qualquer uma no objeto, sem diferenciar maiúsculas/acentos |
| `--max-paginas` | Limite de páginas de 50 registros |

## Dados

Os arquivos `data/editais_AAAAMMDD_HHMM.json` são versionados no git. O formato de cada registro
está descrito em [CLAUDE.md](CLAUDE.md). Para análises, abra o Claude Code no repositório e peça,
por exemplo: "quais editais de TI no Ceará encerram esta semana?".
