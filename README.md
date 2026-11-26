# Clareira

**Sinais de risco de créditos de carbono a partir de dados públicos de satélite, antes de você comprar.**

**Demo:** https://clareira-carbono.vercel.app (sem login) · **Vídeo:** _link do vídeo_

> Trilha: Meio ambiente & economia verde, Hack Brasil 2026.

## O problema

Créditos de carbono já foram emitidos para áreas que estavam sendo desmatadas, que se sobrepõem a
terras públicas ou indígenas, ou que foram vendidas duas vezes. Na Operação Greenwashing, a Polícia
Federal indiciou 31 pessoas: áreas de projetos REDD+ no Amazonas geravam créditos enquanto serviam
para lavar madeira de desmatamento não autorizado. A suspeita surgiu comparando o que foi declarado com imagens
de satélite. Com o mercado regulado (Lei 15.042/2024, SBCE), a qualidade do crédito passa a valer dinheiro.

## A solução

Você informa a área do projeto (desenha no mapa ou envia KML/GeoJSON) e a Clareira cruza essa área com bases públicas:

1. **Desmatamento depois do início do projeto** (DETER e PRODES, INPE)
2. **Sobreposição com Terra Indígena ou Unidade de Conservação** (FUNAI via INPE; CNUC/MMA)
3. **Sobreposição com outro projeto de carbono** (possível dupla contagem)

Cada checagem vira **verde / amarelo / vermelho**, com hectares, percentual, o polígono no mapa e a fonte do dado.

Toda análise ganha um link para reabrir e um **relatório para imprimir ou salvar em PDF** (mapa, semáforo,
detalhes por ano ou por área sobreposta, bases consultadas com data de atualização e o aviso legal).

Como o semáforo decide:

| Nível | Desmatamento / TI e UC | Outro projeto de carbono |
|---|---|---|
| 🟢 Sem sinal | até 0,5 ha **e** 0,1% da área (margem para diferença de borda) | idem |
| 🟡 Sinal baixo | acima da margem e abaixo de 1% | acima da margem e abaixo de 5% |
| 🔴 Sinal alto | 1% da área ou mais | 5% da área ou mais |

As áreas são medidas em SIRGAS 2000 / Brazil Polyconic (EPSG:5880), e o que aparece em mais de uma base
(ex.: DETER e PRODES) é contado uma vez só.

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
que o INPE publica.

Licenças dos dados: TerraBrasilis/INPE (DETER, PRODES, TIs) sob
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), conforme o portal; CNUC/MMA sob
Creative Commons Atribuição (CC BY), conforme o [Portal de Dados Abertos do MMA](https://dados.mma.gov.br/dataset/unidadesdeconservacao).
Cada sinal cita a base usada, com link e data de atualização.

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
| `GET` | `/api/cobertura` | região com dados carregados (GeoJSON) |
| `GET` | `/relatorio.html?analise={id}` | relatório da análise para imprimir ou salvar em PDF |

Áreas fora da região com dados carregados são **recusadas** (HTTP 422): sem dados, "nenhum sinal" não teria significado.

Para usar outra região, defina `CLAREIRA_MUNICIPIO_IBGE` com o código IBGE de um município da Amazônia Legal.

## Deploy (Vercel + Neon)

- `app.py` na raiz é o ponto de entrada da função; `public/` é servido pelo CDN da Vercel.
- Banco: Neon com PostGIS. Para preparar o banco a partir da sua máquina, ponha a URL do Neon em
  `.env.neon` (fora do git) e rode:

```bash
uv run --env-file .env.neon python scripts/db/migrar.py
uv run --env-file .env.neon python scripts/ingest/todas.py
```

## Áreas de demonstração

Em `public/demo/` (Lábrea/AM). Use-as no upload da tela:

| Arquivo | Data de início | Sinais esperados |
|---|---|---|
| `1_area_limpa.geojson` | 2019-01-01 | todos verdes |
| `2_desmatamento_e_dupla_contagem.geojson` | 2020-01-01 | desmatamento 🔴 (~68%), outro projeto 🔴 (~9%) |
| `3_sobreposicao_uc.geojson` | 2021-03-01 | UC 🔴 (~27%, Flona do Iquiri) |

Os projetos em `data/exemplos/projetos_carbono.geojson` são **fictícios** (prefixo `EXEMPLO-`).

## Limitações

- **Uma região por vez.** A demo tem dados de Lábrea (AM). Áreas fora dela são recusadas em vez de aparecerem
  como "sem sinal".
- **Projetos de carbono fictícios.** Não há base pública e aberta com os polígonos dos projetos; a checagem de
  dupla contagem usa exemplos criados para a demo.
- **Ausência de sinal não é atestado.** A área pode não ter floresta desde antes do início (ex.: pasto antigo), e
  isso ainda não é checado. Alertas de satélite também têm área mínima de detecção e podem ter falsos positivos.
- **Imagem de fundo.** A data da imagem Esri varia por região; os sinais vêm das bases do INPE/MMA, não da imagem.

## Próximos passos

- Cobrir toda a Amazônia Legal e o Cerrado (DETER/PRODES Cerrado) com carga incremental.
- Checar se havia floresta na data de início (máscara de não floresta do PRODES), para sinalizar crédito em área
  que já estava aberta.
- Ler os registros públicos de projetos (Verra, Gold Standard) e, quando existir, o Registro Central do SBCE.
- Incluir CAR/SIGEF para sobreposição com imóveis rurais, sem mostrar nome de pessoas físicas.
- API para corretoras e compradores rodarem a checagem em lote.

## Equipe

- _nome, papel_

## Estrutura

```
db/init/            esquema PostGIS (roda na criação do container)
scripts/ingest/     um script idempotente por base pública
scripts/demo/       gerador das áreas de demo e dos projetos fictícios
src/clareira/
  domain/           modelos e regras do semáforo (sem banco, sem HTTP)
  ports.py          interfaces que o serviço precisa (repositório geográfico, análises)
  servico.py        caso de uso: valida a área, roda as 3 checagens, monta os sinais
  adapters/         PostGIS (consultas SQL das checagens)
  api.py            FastAPI (localmente também serve a tela; na Vercel, public/ vai pelo CDN)
public/             tela única (Leaflet + desenho/upload + semáforo), relatório e áreas de demo
tests/              serviço com repositório falso, API, integração com PostGIS
```

## Licença

Código sob a licença [MIT](LICENSE). Os dados seguem as licenças das fontes listadas acima.
