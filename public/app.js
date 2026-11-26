/* Clareira: tela única. Sem framework; Leaflet + Geoman (desenho) + togeojson (KML). */
(() => {
  "use strict";

  const COR = { verde: "#3DBE7A", amarelo: "#F2C230", vermelho: "#E5533D" };
  const NIVEL = { verde: "Sem sinal", amarelo: "Sinal baixo", vermelho: "Sinal alto" };
  const ha = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
  const ha1 = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });
  const pct = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1, minimumFractionDigits: 1 });
  const fmtHa = (v) => `${v > 0 && v < 10 ? ha1.format(v) : ha.format(v)} ha`;
  const fmtData = (iso) => (iso ? iso.split("-").reverse().join("/") : "data não informada");

  const $ = (id) => document.getElementById(id);
  const el = {
    form: $("form"), desenhar: $("btn-desenhar"), arquivo: $("arquivo"), status: $("area-status"),
    data: $("data-inicio"), codigo: $("codigo"), analisar: $("btn-analisar"), erro: $("erro"),
    resultado: $("resultado"), resumo: $("resumo-area"), sinais: $("sinais"), avisos: $("avisos"),
    link: $("btn-link"),
  };
  el.data.max = new Date().toISOString().slice(0, 10);
  const idUrl = new URLSearchParams(location.search).get("analise");

  // ---------------------------------------------------------------- mapa
  const mapa = L.map("mapa", { zoomControl: true, attributionControl: true }).setView([-8.3, -65.9], 8);
  L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 18,
    attribution: "Imagem © Esri, Maxar, Earthstar Geographics",
  }).addTo(mapa);
  L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 18, opacity: 0.8,
  }).addTo(mapa);

  // O grid (e a troca para o layout de celular) muda o tamanho do mapa depois da criação.
  new ResizeObserver(() => mapa.invalidateSize()).observe(document.getElementById("mapa"));

  mapa.pm.setGlobalOptions({
    pathOptions: { color: "#E6EFE9", weight: 2, fillOpacity: 0.08 },
    templineStyle: { color: "#E6EFE9" }, hintlineStyle: { color: "#E6EFE9", dashArray: "4 4" },
  });
  mapa.pm.setLang("pt_br");

  let camadaArea = null;      // área do projeto
  let camadaSinais = null;    // sobreposições do resultado
  let areaGeoJSON = null;
  let ultimaAnalise = null;

  fetch("/api/cobertura").then((r) => r.json()).then((fc) => {
    const cob = L.geoJSON(fc, {
      interactive: false,
      style: { color: "#E6EFE9", weight: 1.5, dashArray: "6 6", fill: false, opacity: 0.7 },
    }).addTo(mapa);
    fc.features.forEach((f) => {
      L.tooltip({ permanent: true, direction: "right", offset: [6, 0], className: "rotulo-cobertura" })
        .setLatLng(L.geoJSON(f).getBounds().getNorthWest())
        .setContent(`Dados carregados: ${f.properties.nome}`)
        .addTo(mapa);
    });
    // só enquadra a cobertura se nenhuma área chegou antes (exemplo, upload ou link)
    if (!idUrl && !camadaArea) mapa.fitBounds(cob.getBounds(), { padding: [20, 20] });
  }).catch(() => {});

  // ---------------------------------------------------------------- área
  function definirArea(geojson, origem) {
    limparResultado();
    if (camadaArea) mapa.removeLayer(camadaArea);
    camadaArea = L.geoJSON(geojson, {
      style: { color: "#E6EFE9", weight: 2.5, fillOpacity: 0.06 },
    }).addTo(mapa);
    areaGeoJSON = geojson;
    mapa.invalidateSize();
    mapa.fitBounds(camadaArea.getBounds(), { padding: [40, 40], maxZoom: 13 });
    el.status.innerHTML = `<strong>Área pronta</strong> (${origem}).`;
    atualizarBotao();
  }

  el.desenhar.addEventListener("click", () => {
    const ativo = mapa.pm.globalDrawModeEnabled();
    if (ativo) { mapa.pm.disableDraw(); return; }
    mapa.pm.enableDraw("Polygon", { snappable: false, finishOn: "dblclick" });
    el.desenhar.setAttribute("aria-pressed", "true");
    el.status.textContent = "Clique no mapa para marcar os vértices. Clique no primeiro ponto para fechar.";
  });
  mapa.on("pm:drawend", () => el.desenhar.setAttribute("aria-pressed", "false"));
  mapa.on("pm:create", ({ layer }) => {
    const gj = layer.toGeoJSON();
    mapa.removeLayer(layer);
    definirArea(gj, "desenhada no mapa");
  });

  el.arquivo.addEventListener("change", async () => {
    const arq = el.arquivo.files[0];
    el.arquivo.value = "";
    if (!arq) return;
    try {
      const texto = await arq.text();
      const gj = /\.kml$/i.test(arq.name)
        ? toGeoJSON.kml(new DOMParser().parseFromString(texto, "text/xml"))
        : JSON.parse(texto);
      if (!L.geoJSON(gj).getLayers().length) throw new Error("vazio");
      definirArea(gj, arq.name);
    } catch {
      mostrarErro(`Não foi possível ler “${arq.name}”. Envie um KML ou GeoJSON com o polígono da área.`);
    }
  });

  document.querySelectorAll(".exemplo").forEach((b) =>
    b.addEventListener("click", async () => {
      const fc = await fetch(`/demo/${b.dataset.demo}.geojson`).then((r) => r.json());
      definirArea(fc, `exemplo: ${b.textContent.trim().toLowerCase()}`);
      el.data.value = fc.features[0].properties.data_inicio;
      el.codigo.value = "";
      atualizarBotao();
      el.analisar.focus();
    })
  );

  el.data.addEventListener("input", atualizarBotao);
  function atualizarBotao() { el.analisar.disabled = !(areaGeoJSON && el.data.value); }

  // ---------------------------------------------------------------- análise
  el.form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (el.analisar.disabled) return;
    esconderErro();
    el.analisar.setAttribute("aria-busy", "true");
    el.analisar.textContent = "Analisando…";
    try {
      const r = await fetch("/api/analises", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          geometria: areaGeoJSON,
          data_inicio: el.data.value,
          codigo_projeto: el.codigo.value.trim() || null,
        }),
      });
      const corpo = await r.json();
      if (!r.ok) throw new Error(mensagemDeErro(corpo));
      mostrarResultado(corpo);
      history.replaceState(null, "", `?analise=${corpo.id}`);
    } catch (e) {
      mostrarErro(e.message || "Não foi possível analisar agora. Tente de novo em instantes.");
    } finally {
      el.analisar.removeAttribute("aria-busy");
      el.analisar.textContent = "Analisar área";
    }
  });

  function mensagemDeErro(corpo) {
    if (typeof corpo.detail === "string") return corpo.detail;
    if (Array.isArray(corpo.detail)) return "Confira a data de início e a área informada.";
    return "Não foi possível analisar esta área.";
  }

  function mostrarResultado(a) {
    ultimaAnalise = a;
    if (camadaSinais) mapa.removeLayer(camadaSinais);
    camadaSinais = L.featureGroup().addTo(mapa);

    el.resumo.textContent =
      `Área de ${fmtHa(a.area_ha)}, início em ${fmtData(a.data_inicio)}` +
      (a.codigo_projeto ? `, código ${a.codigo_projeto}` : "") + ".";
    el.sinais.replaceChildren(...a.sinais.map((s, i) => itemSinal(s, i)));
    el.avisos.replaceChildren(...a.avisos.map((t) => Object.assign(document.createElement("li"), { textContent: t })));
    el.resultado.hidden = false;
    $("btn-relatorio").href = `relatorio.html?analise=${encodeURIComponent(a.id)}`;

    // desmatamento embaixo, sobreposições tracejadas por cima; dentro de cada grupo, vermelho no topo
    const ordem = { verde: 0, amarelo: 1, vermelho: 2 };
    const peso = (s) => ordem[s.nivel] + (s.tipo === "desmatamento_pos_inicio" ? 0 : 3);
    [...a.sinais].sort((x, y) => peso(x) - peso(y)).forEach((s) => {
      if (!s.geometria) return;
      const desm = s.tipo === "desmatamento_pos_inicio";
      L.geoJSON(s.geometria, {
        // desmatamento: mancha cheia; sobreposições: contorno tracejado, preenchimento leve
        style: desm
          ? { color: COR[s.nivel], weight: 1.5, fillColor: COR[s.nivel], fillOpacity: 0.45 }
          : { color: COR[s.nivel], weight: 3, dashArray: "8 5", fillColor: COR[s.nivel], fillOpacity: 0.18 },
      }).bindTooltip(`${s.titulo}: ${fmtHa(s.ha)}`, { sticky: true }).addTo(camadaSinais);
    });
    el.resultado.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "nearest" });
  }

  function itemSinal(s, i) {
    const li = document.createElement("li");
    li.className = "sinal";
    li.dataset.nivel = s.nivel;
    const idDet = `det-${i}`;
    const numeros = s.ha > 0
      ? `<b>${fmtHa(s.ha)}</b>, ${pct.format(s.percentual)}% da área`
      : "Nada encontrado nas bases consultadas";
    li.innerHTML = `
      <button type="button" class="sinal-cabeca" aria-expanded="false" aria-controls="${idDet}">
        <span class="sinal-titulo"></span>
        <span class="sinal-nivel">${NIVEL[s.nivel]}</span>
        <span class="sinal-numeros">${numeros}</span>
      </button>
      <div class="sinal-detalhes" id="${idDet}" hidden></div>`;
    li.querySelector(".sinal-titulo").textContent = s.titulo;
    li.querySelector(".sinal-detalhes").append(...detalhes(s));

    const cabeca = li.querySelector(".sinal-cabeca");
    cabeca.addEventListener("click", () => {
      const aberto = cabeca.getAttribute("aria-expanded") === "true";
      cabeca.setAttribute("aria-expanded", String(!aberto));
      li.querySelector(".sinal-detalhes").hidden = aberto;
      if (!aberto && s.geometria) mapa.fitBounds(L.geoJSON(s.geometria).getBounds(), { padding: [60, 60], maxZoom: 14 });
    });
    return li;
  }

  function detalhes(s) {
    const partes = [];
    if (s.itens.length) {
      const h = document.createElement("h3");
      h.textContent = s.tipo === "desmatamento_pos_inicio" ? "Ano em que foi detectado" : "Onde há sobreposição";
      const ul = document.createElement("ul");
      s.itens.forEach((it) => {
        const li = document.createElement("li");
        li.append(texto("span", it.rotulo), texto("span", fmtHa(it.ha)));
        ul.append(li);
      });
      partes.push(h, ul);
    }
    const hf = document.createElement("h3");
    hf.textContent = "Bases consultadas";
    const uf = document.createElement("ul");
    s.fontes.forEach((f) => {
      const li = document.createElement("li");
      const a = Object.assign(document.createElement("a"), { href: f.url, textContent: f.nome, target: "_blank", rel: "noopener" });
      li.append(a, texto("span", f.atualizado_em ? `dados até ${fmtData(f.atualizado_em)}` : "", "data"));
      uf.append(li);
    });
    partes.push(hf, uf);
    return partes;
  }

  function texto(tag, conteudo, classe) {
    const n = document.createElement(tag);
    n.textContent = conteudo;
    if (classe) n.className = classe;
    return n;
  }

  function limparResultado() {
    if (camadaSinais) { mapa.removeLayer(camadaSinais); camadaSinais = null; }
    el.resultado.hidden = true;
    esconderErro();
    if (location.search) history.replaceState(null, "", location.pathname);
  }

  function mostrarErro(msg) { el.erro.textContent = msg; el.erro.hidden = false; }
  function esconderErro() { el.erro.hidden = true; }

  el.link.addEventListener("click", async () => {
    if (!ultimaAnalise) return;
    const url = `${location.origin}${location.pathname}?analise=${ultimaAnalise.id}`;
    try {
      await navigator.clipboard.writeText(url);
      el.link.textContent = "Link copiado";
    } catch {
      el.link.textContent = url;
    }
    setTimeout(() => (el.link.textContent = "Copiar link desta análise"), 2500);
  });

  // ---------------------------------------------------------------- reabrir por link
  if (idUrl) {
    fetch(`/api/analises/${encodeURIComponent(idUrl)}`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((a) => {
        definirArea(a.geometria, "análise salva");
        el.data.value = a.data_inicio;
        el.codigo.value = a.codigo_projeto || "";
        atualizarBotao();
        mostrarResultado(a);
        history.replaceState(null, "", `?analise=${a.id}`);
      })
      .catch(() => mostrarErro("Não encontramos esta análise. Informe a área para fazer uma nova."));
  }
})();
