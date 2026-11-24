-- Esquema do Clareira.
-- Tudo é guardado em SRID 4326. Áreas em hectares são calculadas com
-- ST_Transform(geom, 5880) (SIRGAS 2000 / Brazil Polyconic).

CREATE EXTENSION IF NOT EXISTS postgis;

-- Cada base pública carregada, com data de atualização e link (aparece em todo sinal).
CREATE TABLE IF NOT EXISTS fontes (
    id            text PRIMARY KEY,           -- 'deter', 'prodes', 'ti_inpe', 'cnuc'
    nome          text NOT NULL,
    url           text NOT NULL,
    licenca       text,
    atualizado_em date,                       -- data do dado na origem (quando conhecida)
    baixado_em    timestamptz NOT NULL DEFAULT now()
);

-- DETER e PRODES na mesma tabela; a coluna fonte_id diz de onde veio.
CREATE TABLE IF NOT EXISTS alertas_desmatamento (
    id            bigserial PRIMARY KEY,
    fonte_id      text NOT NULL REFERENCES fontes(id),
    id_origem     text,
    classe        text,
    data_deteccao date NOT NULL,
    geom          geometry(MultiPolygon, 4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS alertas_geom_gix ON alertas_desmatamento USING gist (geom);
CREATE INDEX IF NOT EXISTS alertas_data_idx ON alertas_desmatamento (data_deteccao);

CREATE TABLE IF NOT EXISTS terras_indigenas (
    id        bigserial PRIMARY KEY,
    fonte_id  text NOT NULL REFERENCES fontes(id),
    codigo    text,
    nome      text,
    fase      text,
    geom      geometry(MultiPolygon, 4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS ti_geom_gix ON terras_indigenas USING gist (geom);

CREATE TABLE IF NOT EXISTS unidades_conservacao (
    id         bigserial PRIMARY KEY,
    fonte_id   text NOT NULL REFERENCES fontes(id),
    codigo     text,       -- código CNUC
    nome       text,
    categoria  text,
    esfera     text,
    geom       geometry(MultiPolygon, 4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS uc_geom_gix ON unidades_conservacao USING gist (geom);

-- Projetos de carbono (dupla contagem). No MVP, só projetos de EXEMPLO, fictícios.
CREATE TABLE IF NOT EXISTS projetos_carbono (
    id          bigserial PRIMARY KEY,
    fonte_id    text NOT NULL REFERENCES fontes(id),
    codigo      text NOT NULL UNIQUE,
    nome        text NOT NULL,
    data_inicio date,
    ficticio    boolean NOT NULL DEFAULT true,
    geom        geometry(MultiPolygon, 4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS projetos_geom_gix ON projetos_carbono USING gist (geom);
