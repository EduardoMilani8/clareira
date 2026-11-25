"""Caso de uso: analisar a área de um projeto e devolver o semáforo de sinais."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from clareira.domain.modelos import Analise, EntradaInvalida, Fonte, Sinal, Sobreposicao
from clareira.domain.semaforo import LIMITE_VERMELHO_PCT, TipoChecagem, classificar, percentual
from clareira.geojson import extrair_poligono
from clareira.ports import RepositorioAnalises, RepositorioGeografico

# Acima disso a consulta fica lenta e o "projeto" deixa de ser plausível.
AREA_MAXIMA_HA = 500_000
COBERTURA_MINIMA = 0.999

TITULOS = {
    TipoChecagem.DESMATAMENTO: "Desmatamento detectado após o início do projeto",
    TipoChecagem.AREA_PROTEGIDA: "Sobreposição com Terra Indígena ou Unidade de Conservação",
    TipoChecagem.OUTRO_PROJETO: "Sobreposição com outro projeto de carbono cadastrado",
}

# Quais bases cada checagem consulta (ids da tabela `fontes`).
FONTES_DA_CHECAGEM = {
    TipoChecagem.DESMATAMENTO: ("deter", "prodes"),
    TipoChecagem.AREA_PROTEGIDA: ("ti_inpe", "cnuc"),
    TipoChecagem.OUTRO_PROJETO: ("exemplos",),
}

INICIO_PRODES = date(2008, 1, 1)
INICIO_DETER = date(2016, 8, 1)


class ServicoAnalise:
    def __init__(self, geo: RepositorioGeografico, analises: RepositorioAnalises):
        self.geo = geo
        self.analises = analises

    def analisar(
        self, geometria: dict, data_inicio: date, codigo_projeto: str | None = None
    ) -> Analise:
        if data_inicio > date.today():
            raise EntradaInvalida("A data de início não pode estar no futuro.")

        poligono, area_ha = self.geo.normalizar(extrair_poligono(geometria))
        if area_ha <= 0:
            raise EntradaInvalida("A área enviada tem 0 ha.")
        if area_ha > AREA_MAXIMA_HA:
            raise EntradaInvalida(
                f"A área tem {area_ha:,.0f} ha; o limite é {AREA_MAXIMA_HA:,} ha.".replace(",", ".")
            )
        if self.geo.fracao_coberta(poligono) < COBERTURA_MINIMA:
            raise EntradaInvalida(
                "A área está fora (ou parcialmente fora) da região com dados carregados nesta "
                "demonstração. Sem dados, a ausência de sinais não teria significado."
            )

        avisos = []
        if data_inicio < INICIO_PRODES:
            avisos.append(
                "Os dados de desmatamento começam em 2008 (PRODES) e 2016 (DETER); "
                "o período anterior não foi verificado."
            )
        elif data_inicio < INICIO_DETER:
            avisos.append("Antes de ago/2016 só há dados anuais (PRODES), sem alertas do DETER.")

        fontes = {f.id: f for f in self.geo.fontes()}
        codigo = (codigo_projeto or "").strip() or None
        sobreposicoes = {
            TipoChecagem.DESMATAMENTO: self.geo.desmatamento_desde(poligono, data_inicio),
            TipoChecagem.AREA_PROTEGIDA: self.geo.areas_protegidas(poligono),
            TipoChecagem.OUTRO_PROJETO: self.geo.outros_projetos(poligono, codigo),
        }
        sinais = [self._sinal(tipo, s, area_ha, fontes) for tipo, s in sobreposicoes.items()]

        analise = Analise(
            id=str(uuid.uuid4()),
            criada_em=datetime.now(UTC),
            area_ha=area_ha,
            data_inicio=data_inicio,
            codigo_projeto=codigo,
            geometria=poligono,
            sinais=sinais,
            avisos=avisos,
        )
        self.analises.salvar(analise)
        return analise

    def buscar(self, id_analise: str) -> Analise | None:
        return self.analises.buscar(id_analise)

    def fontes(self) -> list[Fonte]:
        return self.geo.fontes()

    @staticmethod
    def _sinal(
        tipo: TipoChecagem, s: Sobreposicao, area_ha: float, fontes: dict[str, Fonte]
    ) -> Sinal:
        return Sinal(
            tipo=tipo,
            titulo=TITULOS[tipo],
            nivel=classificar(s.ha, area_ha, LIMITE_VERMELHO_PCT[tipo]),
            ha=s.ha,
            percentual=percentual(s.ha, area_ha),
            geometria=s.geometria,
            itens=s.itens,
            fontes=[fontes[i] for i in FONTES_DA_CHECAGEM[tipo] if i in fontes],
        )
