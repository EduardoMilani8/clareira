# Clareira

**Sinais de risco de créditos de carbono a partir de dados públicos de satélite, antes de você comprar.**

> Trilha: Meio ambiente & economia verde, Hack Brasil 2026. 🚧 Em construção.

## O problema

Créditos de carbono já foram emitidos para áreas que estavam sendo desmatadas, que se sobrepõem a
terras públicas ou indígenas, ou que foram vendidas duas vezes. Na Operação Greenwashing, a Polícia
Federal indiciou 31 pessoas: áreas de projetos REDD+ no Amazonas geravam créditos enquanto serviam
para lavar madeira de desmatamento ilegal. A suspeita surgiu comparando o que foi declarado com imagens
de satélite. Com o mercado regulado (Lei 15.042/2024, SBCE), a qualidade do crédito passa a valer dinheiro.

## A solução

Você informa a área do projeto (desenha no mapa ou envia KML/GeoJSON) e a Clareira cruza essa área com bases públicas:

1. **Desmatamento depois do início do projeto** (DETER e PRODES, INPE)
2. **Sobreposição com Terra Indígena ou Unidade de Conservação** (FUNAI via INPE; CNUC/MMA)
3. **Sobreposição com outro projeto de carbono** (possível dupla contagem)

Cada checagem vira **verde / amarelo / vermelho**, com hectares, percentual, o polígono no mapa e a fonte do dado.

> Sinais automáticos a partir de dados públicos. Não constituem conclusão sobre a regularidade do projeto.

## Fontes de dados

| Base | Origem | Formato | Versão |
|---|---|---|---|
| DETER Amazônia | INPE / TerraBrasilis | WFS (GeoJSON) | atualização contínua |
| PRODES Amazônia Legal | INPE / TerraBrasilis | WFS (GeoJSON) | anual |
| Terras Indígenas (Amazônia Legal) | FUNAI, publicada pelo INPE / TerraBrasilis | WFS (GeoJSON) | — |
| Unidades de Conservação | CNUC / MMA, dados.mma.gov.br | Shapefile | ago/2025 |
| Projetos de carbono | **exemplos fictícios** criados para a demo | GeoJSON | — |

Mapa: imagem de satélite Esri World Imagery (Esri, Maxar, Earthstar Geographics), via Leaflet,
Leaflet-Geoman (desenho) e @tmcw/togeojson (leitura de KML). A data da imagem varia por região e pode ser
anterior aos alertas mais recentes.

Nota: o geoserver do FUNAI recusa downloads automáticos (HTTP 403), por isso usamos a camada de TIs
que o INPE publica. Licenças: a confirmar antes da submissão.

## Como rodar localmente

Requisitos: Docker e [uv](https://docs.astral.sh/uv/).

```bash
docker compose up -d                       # PostGIS na porta 5433
uv sync
uv run python scripts/ingest/todas.py      # baixa e carrega as bases (região padrão: Lábrea/AM)
uv run python scripts/demo/gerar_areas.py  # (opcional) regera áreas de demo e projetos fictícios
uv run pytest                              # unitários + integração (precisa do banco)
uv run uvicorn clareira.api:app --reload   # tela em http://localhost:8000 (API em /api, docs em /docs)
```

## API

| Método | Rota | O que faz |
|---|---|---|
| `POST` | `/api/analises` | recebe `{geometria: GeoJSON, data_inicio: "AAAA-MM-DD", codigo_projeto?}` e devolve os 3 sinais |
| `GET` | `/api/analises/{id}` | reabre uma análise salva |
| `GET` | `/api/fontes` | bases carregadas e data de atualização de cada uma |

Áreas fora da região com dados carregados são **recusadas** (HTTP 422): sem dados, "nenhum sinal" não teria significado.

Para usar outra região, defina `CLAREIRA_MUNICIPIO_IBGE` com o código IBGE de um município da Amazônia Legal.

## Áreas de demonstração

Em `data/demo/` (Lábrea/AM). Use-as no upload da tela:

| Arquivo | Data de início | Sinais esperados |
|---|---|---|
| `1_area_limpa.geojson` | 2019-01-01 | todos verdes |
| `2_desmatamento_e_dupla_contagem.geojson` | 2020-01-01 | desmatamento 🔴 (~68%), outro projeto 🔴 (~9%) |
| `3_sobreposicao_uc.geojson` | 2021-03-01 | UC 🔴 (~27%, Flona do Iquiri) |

Os projetos em `data/exemplos/projetos_carbono.geojson` são **fictícios** (prefixo `EXEMPLO-`).

## Estrutura

```
db/init/            esquema PostGIS (roda na criação do container)
scripts/ingest/     um script idempotente por base pública
scripts/demo/       gerador das áreas de demo e dos projetos fictícios
data/demo/          áreas de demonstração (GeoJSON)
src/clareira/
  domain/           modelos e regras do semáforo (sem banco, sem HTTP)
  ports.py          interfaces que o serviço precisa (repositório geográfico, análises)
  servico.py        caso de uso: valida a área, roda as 3 checagens, monta os sinais
  adapters/         PostGIS (consultas SQL das checagens)
  api.py            FastAPI (também serve a tela e as áreas de demo)
frontend/           tela única: Leaflet + desenho/upload + semáforo
tests/              serviço com repositório falso, API, integração com PostGIS
```
