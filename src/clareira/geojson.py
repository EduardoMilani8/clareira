"""Leitura da área enviada pelo usuário (GeoJSON desenhado no mapa ou de arquivo)."""

from __future__ import annotations

from shapely.geometry import mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from clareira.domain.modelos import EntradaInvalida

_POLIGONAIS = {"Polygon", "MultiPolygon"}


def _geometrias(obj: dict) -> list[dict]:
    tipo = obj.get("type") if isinstance(obj, dict) else None
    if tipo == "FeatureCollection":
        return [g for f in obj.get("features", []) for g in _geometrias(f)]
    if tipo == "Feature":
        return _geometrias(obj.get("geometry") or {})
    if tipo == "GeometryCollection":
        return [g for sub in obj.get("geometries", []) for g in _geometrias(sub)]
    if tipo in _POLIGONAIS:
        return [obj]
    return []


def extrair_poligono(obj: dict) -> dict:
    """Junta todos os polígonos do GeoJSON numa única geometria (GeoJSON).

    Aceita Geometry, Feature ou FeatureCollection. Pontos e linhas são ignorados.
    """
    partes = _geometrias(obj)
    if not partes:
        raise EntradaInvalida("Envie a área do projeto como polígono (GeoJSON ou KML).")
    try:
        formas: list[BaseGeometry] = [shape(p) for p in partes]
    except Exception as erro:  # coordenadas malformadas
        raise EntradaInvalida(f"Geometria inválida: {erro}") from erro
    uniao = unary_union([f.buffer(0) if not f.is_valid else f for f in formas])
    if uniao.is_empty:
        raise EntradaInvalida("A área enviada está vazia.")
    minx, miny, maxx, maxy = uniao.bounds
    if not (-180 <= minx <= maxx <= 180 and -90 <= miny <= maxy <= 90):
        raise EntradaInvalida("Coordenadas fora do intervalo de longitude/latitude (use WGS 84).")
    return mapping(uniao)
