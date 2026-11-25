-- Região onde as bases foram carregadas. Fora dela, "nenhum sinal" significaria
-- "nenhum dado", então a API recusa áreas que não estejam inteiramente cobertas.
CREATE TABLE IF NOT EXISTS cobertura (
    id        text PRIMARY KEY,          -- código IBGE do município
    nome      text NOT NULL,
    geom      geometry(MultiPolygon, 4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS cobertura_geom_gix ON cobertura USING gist (geom);

-- Análises feitas, para reabrir o resultado e gerar o relatório por link.
CREATE TABLE IF NOT EXISTS analises (
    id         uuid PRIMARY KEY,
    criada_em  timestamptz NOT NULL DEFAULT now(),
    resultado  jsonb NOT NULL
);
