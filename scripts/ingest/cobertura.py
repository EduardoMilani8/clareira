"""Registra a região de cobertura (o município de demo) na tabela `cobertura`."""

from _comum import MUNICIPIO_IBGE, engine, regiao
from sqlalchemy import text


def main() -> None:
    print("Cobertura")
    reg = regiao()
    linha = reg.iloc[0]
    with engine().begin() as con:
        con.execute(
            text(
                """
                INSERT INTO cobertura (id, nome, geom)
                VALUES (:id, :nome, ST_Multi(ST_CollectionExtract(ST_MakeValid(
                        ST_SetSRID(ST_GeomFromText(:wkt), 4326)), 3)))
                ON CONFLICT (id) DO UPDATE SET nome = EXCLUDED.nome, geom = EXCLUDED.geom
                """
            ),
            {"id": MUNICIPIO_IBGE, "nome": linha["nome"], "wkt": linha.geometry.wkt},
        )
    print(f"  cobertura: {linha['nome']} ({MUNICIPIO_IBGE})")


if __name__ == "__main__":
    main()
