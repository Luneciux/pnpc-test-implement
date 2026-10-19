# Editais PNCP

Busca editais de licitação com propostas abertas na API pública de consulta do PNCP
(Portal Nacional de Contratações Públicas), salva em JSON e exibe num frontend web.
**Não há integração com API de LLM**: as análises são feitas pelo usuário conversando
com o Claude Code sobre os arquivos em `data/`.

## Estrutura

| Arquivo | Papel |
|---|---|
| `pncp.py` | Lógica de busca: paginação, retry, pausa entre requisições, filtro por palavras-chave, conversão para o formato enxuto (`resumir`) e gravação em `data/` (`salvar`). |
| `buscar.py` | CLI (argparse) sobre `pncp.py`. `python buscar.py --help`. |
| `app.py` | Backend FastAPI: serve `static/index.html` e expõe `POST /api/buscar`, `GET /api/arquivos`, `GET /api/arquivos/{nome}`. |
| `static/index.html` | Frontend em um único arquivo (HTML/CSS/JS puros, sem build). |
| `data/` | Buscas salvas, `editais_AAAAMMDD_HHMM.json` (sufixo `_2`, `_3`… se houver mais de uma no mesmo minuto). **Versionado no git** de propósito. |

### API usada
`GET https://pncp.gov.br/api/consulta/v1/contratacoes/proposta`, com headers
`Accept: application/json` e `User-Agent: Mozilla/5.0`.
Parâmetros: `dataFinal` (AAAAMMDD, obrigatório), `pagina` (obrigatório), `tamanhoPagina` (10–50; usamos 50),
e opcionais `uf`, `codigoMunicipioIbge`, `codigoModalidadeContratacao` (6 = pregão eletrônico,
8 = dispensa, 4 = concorrência eletrônica). Resposta: `data`, `totalPaginas`, `totalRegistros`.
O endpoint retorna contratações cuja **proposta ainda está aberta** e encerra até `dataFinal`.
HTTP 204 significa "nenhum resultado".

### Filtro por palavras-chave
Local, sobre `objetoCompra`, sem diferenciar maiúsculas nem acentos. Com várias palavras,
basta **qualquer uma** aparecer (OU). É busca por substring (`"sistema"` casa com `"sistemas"`).

## Formato dos JSON em `data/`

Cada arquivo é uma **lista** de objetos com:

| Campo | Origem no PNCP | Significado |
|---|---|---|
| `id` | `numeroControlePNCP` | Identificador único da contratação no PNCP (`CNPJ-1-SEQUENCIAL/ANO`). |
| `orgao` | `orgaoEntidade.razaoSocial` | Órgão/entidade contratante. |
| `cnpj` | `orgaoEntidade.cnpj` | CNPJ do órgão (só dígitos). |
| `municipio` | `unidadeOrgao.municipioNome` | Município da unidade compradora. |
| `uf` | `unidadeOrgao.ufSigla` | UF da unidade compradora. |
| `modalidade` | `modalidadeNome` | Ex.: "Pregão - Eletrônico", "Dispensa", "Concorrência - Eletrônica", "Credenciamento". |
| `objeto` | `objetoCompra` | Descrição do que está sendo contratado. |
| `valor_estimado` | `valorTotalEstimado` | Valor total estimado em R$. **`0` ou `null` é comum** (orçamento sigiloso ou não informado) — não trate como valor real. |
| `data_abertura_proposta` | `dataAberturaProposta` | Início do recebimento de propostas (ISO, horário de Brasília, sem fuso). |
| `data_encerramento_proposta` | `dataEncerramentoProposta` | Prazo final para envio de propostas. |
| `link_edital` | montado | `https://pncp.gov.br/app/editais/{cnpj}/{anoCompra}/{sequencialCompra}`. |
| `raw` | — | Registro bruto completo retornado pela API. |

Campos úteis dentro de `raw`, quando necessário: `unidadeOrgao.nomeUnidade` e `codigoIbge`,
`amparoLegal` (base legal), `srp` (registro de preços), `modoDisputaNome` (aberto/fechado),
`situacaoCompraNome`, `informacaoComplementar`, `linkSistemaOrigem` (portal onde a disputa ocorre),
`numeroCompra`, `processo`, `orgaoEntidade.esferaId` (F/E/M = federal/estadual/municipal),
`dataPublicacaoPncp`, `dataAtualizacao`.

## Como fazer análises (instruções para o Claude Code)

Quando o usuário pedir análises sobre os editais:

1. Use o arquivo **mais recente** em `data/` (maior nome em ordem alfabética, por exemplo
   `ls data/editais_*.json | sort | tail -1`), a menos que o usuário indique outro.
2. Trabalhe com os **campos enxutos** (`id`, `orgao`, `municipio`, `uf`, `modalidade`, `objeto`,
   `valor_estimado`, datas, `link_edital`). Consulte `raw` **só quando necessário**: os arquivos
   podem ter vários MB e `raw` é a maior parte. Prefira processar com `python3`/`jq` e mostrar
   só o resultado, em vez de ler o JSON inteiro.
3. Ao somar ou comparar valores, avise sobre registros com valor 0/nulo e sobre outliers (um único
   edital pode concentrar a maior parte do total).
4. Sempre inclua `link_edital` ao citar editais específicos.
5. Se o usuário pedir dados novos, rode `python buscar.py ...` (gera um novo arquivo em `data/`)
   e faça commit do arquivo, já que `data/` é versionado.

## Comandos

```bash
pip install -r requirements.txt
python buscar.py --uf CE --modalidade 6 --palavras-chave "software,sistema" --max-paginas 5
uvicorn app:app --reload        # http://localhost:8000
```
