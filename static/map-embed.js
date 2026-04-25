(function() {
  "use strict";

  const PERTH = [115.8605, -31.9505];
  const TYPE_LABELS = {
    "sme": "SME",
    "prime": "Prime",
    "large-enterprise": "Large Enterprise",
    "government": "Government",
    "educational": "Educational",
    "research": "Research",
  };
  const SAFE_SLUG_RE = /^[a-z0-9][a-z0-9-]*$/;
  const SAFE_LOGO_RE = /^\/logos\/[a-z0-9][a-z0-9-]*\.png$/;
  const instances = new Map();
  let companiesPromise = null;
  let stylePromise = null;

  function asText(value) {
    return typeof value === "string" ? value : "";
  }

  function relUrl(path) {
    const base = document.documentElement.dataset.baseUrl || "/";
    return new URL(path.replace(/^\//, ""), new URL(base, location.href)).pathname;
  }

  function buildCompanyHref(slug) {
    return SAFE_SLUG_RE.test(slug) ? relUrl(`company/${slug}/`) : null;
  }

  function buildLogoUrl(logoUrl) {
    return SAFE_LOGO_RE.test(logoUrl) ? logoUrl : null;
  }

  function sanitizeStyleExpression(expr) {
    if (!Array.isArray(expr) || !expr.length) return expr;
    const op = expr[0];
    if ([">", ">=", "<", "<="].includes(op)) {
      return [op, ...expr.slice(1).map((arg, i) => {
        const next = sanitizeStyleExpression(arg);
        return Array.isArray(next) && next[0] === "get"
          ? ["to-number", next, i === 0 ? -Infinity : Infinity]
          : next;
      })];
    }
    return expr.map(sanitizeStyleExpression);
  }

  function loadMapStyle() {
    if (!stylePromise) {
      const styleUrl = document.documentElement.dataset.mapStyleUrl;
      stylePromise = fetch(styleUrl)
        .then(res => {
          if (!res.ok) throw new Error("Failed to load map style");
          return res.json();
        })
        .then(style => {
          (style.layers || []).forEach(layer => {
            if (layer.filter) layer.filter = sanitizeStyleExpression(layer.filter);
          });
          return style;
        });
    }
    return stylePromise;
  }

  function loadCompanies() {
    if (!companiesPromise) {
      companiesPromise = fetch(relUrl("companies-map.json"))
        .then(res => res.json())
        .then(companies => {
          companies.forEach(c => {
            (window.TAXONOMIES || []).forEach(tax => { c[tax] = (c[tax] || []).join("|"); });
          });
          return companies;
        });
    }
    return companiesPromise;
  }

  function appendText(parent, tag, className, text) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    el.textContent = text;
    parent.appendChild(el);
    return el;
  }

  function popupContent(c) {
    const name = asText(c.name);
    const slug = asText(c.slug);
    const overview = asText(c.overview);
    const overviewShort = asText(c.overview_short);
    const companyHref = buildCompanyHref(slug);
    const logoUrl = buildLogoUrl(asText(c.logo_url));
    const companyTypes = asText(c.company_types).split("|").filter(Boolean);
    const ownerships = asText(c.ownerships).split("|").filter(Boolean);

    const wrapper = document.createElement("article");
    wrapper.className = "map-popup";
    wrapper.setAttribute("aria-label", name);

    const header = document.createElement("div");
    header.className = "map-popup__header";
    wrapper.appendChild(header);

    const logo = document.createElement("div");
    logo.className = "map-popup__logo";
    if (logoUrl) {
      const img = document.createElement("img");
      img.src = logoUrl;
      img.alt = "";
      logo.appendChild(img);
    } else {
      logo.textContent = name.slice(0, 2).toUpperCase();
    }
    header.appendChild(logo);

    const titleWrap = document.createElement("div");
    titleWrap.className = "map-popup__title-wrap";
    header.appendChild(titleWrap);

    if (companyHref) {
      const link = appendText(titleWrap, "a", "map-popup__title", name);
      link.href = companyHref;
    } else {
      appendText(titleWrap, "div", "map-popup__title", name);
    }

    const badges = document.createElement("div");
    badges.className = "map-popup__badges";
    [...companyTypes, ...ownerships].slice(0, 4).forEach(type => {
      const badge = appendText(badges, "span", "map-popup__badge", TYPE_LABELS[type] || type);
      if (type === "indigenous" || type === "veteran") badge.classList.add("map-popup__badge--highlight");
    });
    if (badges.childNodes.length) titleWrap.appendChild(badges);

    if (overviewShort) {
      const text = appendText(wrapper, "p", "map-popup__overview", overviewShort);
      if (overview) text.title = overview;
    }

    if (companyHref) appendText(wrapper, "a", "map-popup__cta", "View profile →").href = companyHref;
    return wrapper;
  }

  function filtersFromParams(params) {
    const filters = { search: (params.get("q") || "").trim().toLowerCase() };
    (window.TAXONOMIES || []).forEach(tax => {
      const vals = params.getAll(tax);
      if (vals.length) filters[tax] = vals;
    });
    return filters;
  }

  function paramsForContainer(container) {
    const initial = container.dataset.initialParams || "";
    return initial ? new URLSearchParams(initial) : new URLSearchParams(location.search);
  }

  async function initMap(container) {
    if (!window.maplibregl || !container || instances.has(container.id)) return;

    const canvas = container.querySelector(".map-canvas");
    const noResults = container.querySelector(".map-no-results");
    const mapStatus = container.querySelector(".map-status");
    const [companies, mapStyle] = await Promise.all([loadCompanies(), loadMapStyle()]);
    const markers = [];

    const map = new maplibregl.Map({
      container: canvas,
      style: mapStyle,
      center: PERTH,
      zoom: 4,
    });

    map.on("style.load", () => map.setProjection({ type: "globe" }));
    map.addControl(new maplibregl.NavigationControl({ showZoom: true, showCompass: true, visualizePitch: true }), "top-right");

    let activePopup = null;
    function openPopup(marker, popup, name) {
      if (activePopup && activePopup !== popup) activePopup.remove();
      if (!popup.isOpen()) marker.togglePopup();
      activePopup = popup;
      if (mapStatus) mapStatus.textContent = "Selected: " + name;
    }

    companies.forEach(c => {
      if (!c.latitude || !c.longitude) return;
      const name = asText(c.name);
      const dot = document.createElement("button");
      dot.className = "marker-dot";
      dot.type = "button";
      dot.setAttribute("aria-label", `Show ${name} on map`);

      const popup = new maplibregl.Popup({ offset: 12, closeButton: true, focusAfterOpen: false })
        .setDOMContent(popupContent(c));
      const marker = new maplibregl.Marker({ element: dot })
        .setLngLat([c.longitude, c.latitude])
        .setPopup(popup)
        .addTo(map);

      dot.addEventListener("mouseenter", () => openPopup(marker, popup, name));
      dot.addEventListener("click", e => {
        e.stopPropagation();
        openPopup(marker, popup, name);
      });
      dot.addEventListener("keydown", e => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          openPopup(marker, popup, name);
        }
      });
      markers.push({ marker, data: c });
    });

    canvas.addEventListener("mouseleave", () => {
      if (activePopup) {
        activePopup.remove();
        activePopup = null;
      }
    });
    map.on("click", e => {
      if (e.originalEvent.target.classList.contains("marker-dot")) return;
      if (activePopup) {
        activePopup.remove();
        activePopup = null;
      }
    });

    let fitBoundsTimeout = null;
    function updateMarkers(params) {
      const filters = filtersFromParams(params || paramsForContainer(container));
      let visibleCount = 0;
      const bounds = new maplibregl.LngLatBounds();
      markers.forEach(({ marker, data }) => {
        const visible = matchesFilters(data, filters);
        marker.getElement().hidden = !visible;
        if (visible) {
          visibleCount++;
          bounds.extend([data.longitude, data.latitude]);
        }
      });
      noResults.hidden = visibleCount !== 0;
      container.dispatchEvent(new CustomEvent("mapMarkerCount", { detail: { count: visibleCount } }));
      clearTimeout(fitBoundsTimeout);
      if (visibleCount > 0 && visibleCount < markers.length) {
        fitBoundsTimeout = setTimeout(() => map.fitBounds(bounds, { padding: 50, maxZoom: 12, duration: 500 }), 300);
      }
    }

    instances.set(container.id, { map, updateMarkers });
    updateMarkers();
    requestAnimationFrame(() => map.resize());
  }

  function initAll() {
    document.querySelectorAll(".map-embed").forEach(initMap);
  }

  window.updateEmbeddedMap = function(id, params) {
    const inst = instances.get(id);
    if (!inst) return;
    requestAnimationFrame(() => inst.map.resize());
    inst.updateMarkers(params instanceof URLSearchParams ? params : new URLSearchParams(params || location.search));
  };

  window.addEventListener("load", initAll);
})();
