/* Coverage counties page: Leaflet map + accordion list kept in sync. */
(function () {
  'use strict';

  const dataEl = document.getElementById('coverageData');
  const mapEl = document.getElementById('coverageMap');
  const accordion = document.getElementById('coverageAccordion');
  if (!dataEl || !mapEl || !accordion) return;

  const counties = JSON.parse(dataEl.textContent);
  const byKey = new Map(counties.map((c) => [c.key, c]));
  const byFips = new Map(counties.map((c) => [c.fips, c]));

  const canHover = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  const stacked = window.matchMedia('(max-width: 979px)');
  const TOOLTIP_CITY_LIMIT = 10;
  const INFO_CITY_LIMIT = 8;

  const infoEl = document.getElementById('coverageMapInfo');
  const statusEl = document.getElementById('coverageMapStatus');
  const searchInput = document.getElementById('coverageSearch');
  const searchEmpty = document.getElementById('coverageSearchEmpty');
  const legendButtons = document.querySelectorAll('.coverage-legend__item[data-county]');

  const normalize = (s) => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
  const escapeHtml = (s) => s.replace(/[&<>"']/g, (ch) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[ch]));

  const items = new Map();
  accordion.querySelectorAll('.coverage-county').forEach((el) => {
    const key = el.dataset.county;
    items.set(key, {
      el,
      toggle: el.querySelector('.coverage-county__toggle'),
      panel: el.querySelector('.coverage-county__panel'),
      countEl: el.querySelector('[data-count]'),
      nameNorm: normalize(byKey.get(key).name),
      cities: Array.from(el.querySelectorAll('.coverage-county__cities li')).map((li) => ({
        li,
        norm: normalize(li.textContent),
      })),
    });
  });

  const state = { selected: null, hovered: null, query: '', matches: null };
  const layers = new Map();
  let homeBounds = null;

  /* ---------- Map ---------- */
  const isMobile = L.Browser.mobile;
  const map = L.map(mapEl, {
    scrollWheelZoom: false,
    dragging: !isMobile,
    minZoom: 5,
    maxZoom: 12,
    zoomSnap: 0.25,
  }).setView([34.4, -118.3], 7);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors',
  }).addTo(map);

  // Wheel zoom only after the user engages with the map, so page scrolling isn't hijacked.
  map.on('focus click', () => map.scrollWheelZoom.enable());
  map.on('mouseout blur', () => map.scrollWheelZoom.disable());

  // On phones one-finger drag must scroll the page; allow panning only once zoomed in.
  let homeZoom = 7;
  if (isMobile) {
    map.on('zoomend', () => {
      if (map.getZoom() > homeZoom + 0.1) map.dragging.enable();
      else map.dragging.disable();
    });
  }

  const ResetControl = L.Control.extend({
    options: { position: 'topleft' },
    onAdd() {
      const btn = L.DomUtil.create('button', 'leaflet-bar coverage-map__reset');
      btn.type = 'button';
      btn.title = 'Reset view';
      btn.setAttribute('aria-label', 'Reset view');
      btn.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 5V1L7 6l5 5V7a5 5 0 1 1-5 5H5a7 7 0 1 0 7-7z"/></svg>';
      L.DomEvent.disableClickPropagation(btn);
      btn.addEventListener('click', () => {
        select(null);
        fitHome(true);
      });
      return btn;
    },
  });
  new ResetControl().addTo(map);

  function fitHome(animate) {
    if (!homeBounds) return;
    homeZoom = map.getBoundsZoom(homeBounds, false, L.point(32, 32));
    map.fitBounds(homeBounds, { padding: [16, 16], animate });
  }

  function styleFor(key) {
    const c = byKey.get(key);
    const dimmed = state.matches && !state.matches.has(key);
    const active = key === state.selected;
    const hovered = key === state.hovered;
    return {
      color: active ? '#17120F' : c.color,
      weight: active ? 3.5 : hovered ? 3 : 1.5,
      opacity: dimmed ? 0.35 : 1,
      fillColor: c.color,
      fillOpacity: dimmed ? 0.08 : active ? 0.72 : hovered ? 0.6 : 0.38,
    };
  }

  function refreshStyles() {
    layers.forEach((layer, key) => layer.setStyle(styleFor(key)));
    if (state.hovered && layers.has(state.hovered)) layers.get(state.hovered).bringToFront();
    if (state.selected && layers.has(state.selected)) layers.get(state.selected).bringToFront();
  }

  function tooltipHtml(c) {
    const shown = c.cities.slice(0, TOOLTIP_CITY_LIMIT).map(escapeHtml).join(', ');
    const rest = c.cities.length - TOOLTIP_CITY_LIMIT;
    return (
      `<strong class="coverage-tooltip__title">${escapeHtml(c.name)}</strong>` +
      `<span class="coverage-tooltip__meta">${c.cities.length} cities</span>` +
      `<span class="coverage-tooltip__cities">${shown}${rest > 0 ? `, +${rest} more` : ''}</span>`
    );
  }

  function renderInfo() {
    const c = state.selected && byKey.get(state.selected);
    if (!c) {
      infoEl.hidden = true;
      infoEl.innerHTML = '';
      return;
    }
    const preview = c.cities.slice(0, INFO_CITY_LIMIT).map(escapeHtml).join(', ');
    const rest = c.cities.length - INFO_CITY_LIMIT;
    infoEl.style.setProperty('--county-color', c.color);
    infoEl.innerHTML =
      '<button type="button" class="coverage-map__info-close" aria-label="Clear selection">&times;</button>' +
      `<p class="coverage-map__info-title"><span class="coverage-map__info-swatch" aria-hidden="true"></span>${escapeHtml(c.name)}</p>` +
      `<p class="coverage-map__info-meta">${c.cities.length} cities` +
      `${c.cities.includes(c.seat) ? ` &middot; County seat: ${escapeHtml(c.seat)}` : ''}</p>` +
      `<p class="coverage-map__info-cities">${preview}${rest > 0 ? `, +${rest} more` : ''}</p>` +
      `<button type="button" class="coverage-map__info-link">See all ${c.cities.length} cities</button>`;
    infoEl.hidden = false;
    infoEl.querySelector('.coverage-map__info-close').addEventListener('click', () => select(null));
    infoEl.querySelector('.coverage-map__info-link').addEventListener('click', () => {
      items.get(c.key).el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  /* ---------- Selection / hover sync ---------- */
  function setExpanded(key, expanded) {
    const item = items.get(key);
    item.toggle.setAttribute('aria-expanded', String(expanded));
    item.panel.hidden = !expanded;
    item.el.classList.toggle('is-open', expanded);
  }

  function select(key, opts = {}) {
    state.selected = key;
    items.forEach((item, k) => {
      const isSelected = k === key;
      item.el.classList.toggle('is-selected', isSelected);
      // Outside of a search only the selected county stays open.
      if (!state.query) setExpanded(k, isSelected);
      else if (isSelected) setExpanded(k, true);
    });
    legendButtons.forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.county === key)));
    refreshStyles();
    renderInfo();

    if (!key) return;
    const layer = layers.get(key);
    if (opts.zoom && layer) {
      map.flyToBounds(layer.getBounds(), { padding: [24, 24], maxZoom: 9, duration: 0.6 });
    }
    if (opts.scrollList && !stacked.matches) {
      items.get(key).el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  function setHovered(key) {
    if (state.hovered === key) return;
    state.hovered = key;
    items.forEach((item, k) => item.el.classList.toggle('is-hovered', k === key));
    refreshStyles();
  }

  // Keeps the clicked header under the cursor when a panel above it collapses.
  function keepInPlace(anchor, fn) {
    const before = anchor.getBoundingClientRect().top;
    fn();
    const delta = anchor.getBoundingClientRect().top - before;
    if (!delta) return;
    const root = document.documentElement;
    const previous = root.style.scrollBehavior;
    root.style.scrollBehavior = 'auto';
    window.scrollBy(0, delta);
    root.style.scrollBehavior = previous;
  }

  items.forEach((item, key) => {
    item.toggle.addEventListener('click', () => {
      const open = item.toggle.getAttribute('aria-expanded') === 'true';
      keepInPlace(item.toggle, () => {
        if (open) {
          setExpanded(key, false);
          if (state.selected === key) select(null);
        } else {
          select(key, { zoom: true });
        }
      });
    });
    if (canHover) {
      item.toggle.addEventListener('mouseenter', () => setHovered(key));
      item.toggle.addEventListener('mouseleave', () => setHovered(null));
    }
  });

  legendButtons.forEach((btn) => {
    const key = btn.dataset.county;
    btn.addEventListener('click', () => {
      if (state.selected === key) select(null);
      else select(key, { zoom: true, scrollList: true });
    });
    if (canHover) {
      btn.addEventListener('mouseenter', () => setHovered(key));
      btn.addEventListener('mouseleave', () => setHovered(null));
    }
  });

  map.on('click', () => select(null));

  /* ---------- City search ---------- */
  function applySearch() {
    const q = normalize(searchInput.value);
    state.query = q;

    if (!q) {
      state.matches = null;
      items.forEach((item, key) => {
        item.el.hidden = false;
        item.countEl.textContent = item.cities.length;
        item.cities.forEach((ci) => {
          ci.li.hidden = false;
          ci.li.classList.remove('is-match');
        });
        setExpanded(key, key === state.selected);
      });
      searchEmpty.hidden = true;
      refreshStyles();
      return;
    }

    const matches = new Set();
    items.forEach((item, key) => {
      const countyHit = item.nameNorm.includes(q);
      let found = 0;
      item.cities.forEach((ci) => {
        const hit = countyHit || ci.norm.includes(q);
        ci.li.hidden = !hit;
        ci.li.classList.toggle('is-match', hit && !countyHit);
        if (hit) found += 1;
      });
      item.el.hidden = found === 0;
      item.countEl.textContent = countyHit ? item.cities.length : `${found} of ${item.cities.length}`;
      setExpanded(key, found > 0);
      if (found) matches.add(key);
    });
    state.matches = matches;
    searchEmpty.hidden = matches.size > 0;
    refreshStyles();
  }

  if (searchInput) searchInput.addEventListener('input', applySearch);

  /* ---------- Boundaries ---------- */
  fetch(mapEl.dataset.geojson)
    .then((resp) => {
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return resp.json();
    })
    .then((geo) => {
      L.geoJSON(geo, {
        filter: (f) => !byFips.has(f.id),
        interactive: false,
        style: { color: '#8f8a84', weight: 0.8, fillColor: '#d9d6d0', fillOpacity: 0.35 },
      }).addTo(map);

      geo.features.forEach((feature) => {
        const c = byFips.get(feature.id);
        if (!c) return;
        const layer = L.geoJSON(feature, { style: () => styleFor(c.key) });
        if (canHover) {
          layer.bindTooltip(tooltipHtml(c), {
            sticky: true,
            direction: 'top',
            offset: [0, -10],
            className: 'coverage-tooltip',
          });
        }
        layer.on('mouseover', () => { if (canHover) setHovered(c.key); });
        layer.on('mouseout', () => { if (canHover) setHovered(null); });
        layer.on('click', (e) => {
          L.DomEvent.stopPropagation(e);
          select(c.key, { scrollList: true });
        });
        layer.addTo(map);
        layers.set(c.key, layer);
      });

      homeBounds = L.featureGroup(Array.from(layers.values())).getBounds();
      fitHome(false);
      statusEl.hidden = true;

      const fromHash = window.location.hash.replace('#county-', '');
      if (byKey.has(fromHash)) select(fromHash, { zoom: true });
      else refreshStyles();
    })
    .catch(() => {
      statusEl.textContent = 'The map could not be loaded. Use the list to browse our coverage counties.';
    });
})();
