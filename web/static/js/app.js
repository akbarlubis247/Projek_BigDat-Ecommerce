/* ==========================================================================
   DATA INSIGHT — Enterprise Big Data Analytics Frontend Controller
   Strictly consumes existing FastAPI endpoints without altering backend logic
   ========================================================================== */

const PALETTE = {
  primary: '#526B9B',
  primaryDark: '#3E5683',
  primaryBar: '#8497B8',
  primaryLight: '#B4C1D6',
  secondary: '#C47B58',
  success: '#26866A',
  warning: '#D69A45',
  danger: '#C65C5C',
  ink: '#202938',
  muted: '#697586',
  subtle: '#8C96A5',
  grid: '#EEF1F5',
  border: '#E5E9F0',
};

const CLUSTER_COLORS = [
  PALETTE.primary,
  PALETTE.secondary,
  PALETTE.success,
  '#8D99AE',
];

const CHART_PALETTE = [
  PALETTE.primary,
  PALETTE.primaryBar,
  PALETTE.secondary,
  PALETTE.success,
  '#7D8DA6',
  '#B08B73',
  '#5A8A7B',
  '#9FAAC0',
];

const PAGE_CONFIG = {
  ringkasan: {
    crumb: 'Market Overview',
    eyebrow: 'E-COMMERCE INTELLIGENCE / INDONESIA',
    title: 'Market Overview',
    subtitle: 'Ringkasan performa katalog, kontribusi kategori, dan aktivitas pasar e-commerce.',
    showFilter: true,
  },
  produk: {
    crumb: 'Produk & Toko Terlaris',
    eyebrow: 'CATALOG ANALYTICS / RANKING',
    title: 'Produk & Toko Terlaris',
    subtitle: 'Pemeringkatan produk unggulan, distribusi kelompok harga, dan performa merchant utama.',
    showFilter: true,
  },
  waktu: {
    crumb: 'Waktu Belanja Puncak',
    eyebrow: 'TRANSACTION TELEMETRY / TIME SERIES',
    title: 'Waktu Belanja Puncak',
    subtitle: 'Analisis tren volume transaksi harian, jam puncak belanja, dan pola hari dalam seminggu.',
    showFilter: false,
  },
  geografi: {
    crumb: 'Sebaran Wilayah',
    eyebrow: 'REGIONAL INTELLIGENCE / GEOSPATIAL',
    title: 'Sebaran Wilayah',
    subtitle: 'Distribusi volume penjualan, estimasi GMV, dan konsentrasi merchant per kota di Indonesia.',
    showFilter: true,
  },
  klaster: {
    crumb: 'Segmentasi Produk (ML)',
    eyebrow: 'MACHINE LEARNING / UNSUPERVISED K-MEANS',
    title: 'Segmentasi Produk (ML)',
    subtitle: 'Hasil pengelompokan katalog produk dengan K-Means Clustering dan profil demografi pelanggan.',
    showFilter: true,
  },
  unggah: {
    crumb: 'Upload Data CSV',
    eyebrow: 'DATA MANAGEMENT / CSV IMPORT',
    title: 'Upload Data CSV',
    subtitle: 'Impor dataset katalog CSV baru atau buat dataset uji melalui AI Prompt Builder.',
    showFilter: false,
  },
  arsitektur: {
    crumb: 'Arsitektur Big Data',
    eyebrow: 'TECHNICAL DOCUMENTATION / LAMBDA ARCHITECTURE',
    title: 'Arsitektur Big Data',
    subtitle: 'Spesifikasi teknis pipeline end-to-end berbasis Apache Kafka, MongoDB, Apache Spark, dan FastAPI.',
    showFilter: false,
  },
};

const PRICE_LABELS = {
  ALL: 'Semua Harga',
  '0-100000': '< Rp100 rb',
  '100000-500000': 'Rp100 rb – Rp500 rb',
  '500000-2000000': 'Rp500 rb – Rp2 jt',
  '2000000-': '> Rp2 jt',
};

const state = {
  activePage: 'ringkasan',
  filters: {
    category: 'ALL',
    city: 'ALL',
    priceKey: 'ALL',
    min_price: '',
    max_price: '',
    min_rating: 0,
    top_n: 15,
    sort_by: 'terjual_clean',
    search: '',
  },
  catMetric: 'total_terjual',
  geoMetric: 'total_terjual',
  data: null,
  charts: {},
  debounceTimer: null,
  lastUpdated: null,
};

// ==========================================
// FORMATTING HELPERS
// ==========================================
function fmtInt(n) {
  return new Intl.NumberFormat('id-ID').format(Math.round(Number(n) || 0));
}

function fmtRupiahShort(val) {
  const n = Number(val) || 0;
  if (n >= 1e12) return `Rp${(n / 1e12).toFixed(2).replace('.', ',')} T`;
  if (n >= 1e9) return `Rp${(n / 1e9).toFixed(2).replace('.', ',')} M`;
  if (n >= 1e6) return `Rp${(n / 1e6).toFixed(1).replace('.', ',')} Jt`;
  if (n >= 1e3) return `Rp${(n / 1e3).toFixed(0)} rb`;
  return `Rp${fmtInt(n)}`;
}

function fmtRupiahFull(val) {
  return `Rp${fmtInt(val)}`;
}

function fmtUnitShort(val) {
  const n = Number(val) || 0;
  if (n >= 1e6) return `${(n / 1e6).toFixed(1).replace('.', ',')} Jt`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1).replace('.', ',')} rb`;
  return fmtInt(n);
}

function escapeHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function truncate(str, maxLen = 36) {
  const s = String(str || '');
  return s.length > maxLen ? s.slice(0, maxLen - 1) + '…' : s;
}

function shortCategoryLabel(cat) {
  const map = {
    'Kebutuhan Harian & Lainnya': 'Kebutuhan',
    'Fashion & Pakaian': 'Fashion',
    'Kecantikan & Perawatan': 'Kecantikan',
    'Elektronik & Gadget': 'Elektronik',
    'Perlengkapan Rumah & Dapur': 'Rumah',
    'Makanan & Minuman': 'Makanan',
    'Hobi, Olahraga & Otomotif': 'Hobi & Oto',
    'Logam Mulia & Investasi': 'Logam Mulia',
    'Alat Tulis & Kantor': 'ATK',
    'Hewan Peliharaan': 'Hewan',
  };
  return map[cat] || truncate(cat, 14);
}

async function copyTextSafe(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  document.execCommand('copy');
  ta.remove();
}

// ==========================================
// FEEDBACK & ECHARTS HELPERS
// ==========================================
function setLoading(active) {
  const el = document.getElementById('top-loader');
  if (active) {
    el.classList.remove('done');
    el.classList.add('active');
  } else {
    el.classList.remove('active');
    el.classList.add('done');
    setTimeout(() => el.classList.remove('done'), 260);
  }
}

function showToast(msg, isError = false) {
  const root = document.getElementById('toast-root');
  const t = document.createElement('div');
  t.className = `toast ${isError ? 'err' : ''}`;
  t.textContent = msg;
  root.appendChild(t);
  setTimeout(() => {
    t.style.opacity = '0';
    t.style.transition = 'opacity 180ms ease';
    setTimeout(() => t.remove(), 200);
  }, 3200);
}

function getChart(id) {
  const el = document.getElementById(id);
  if (!el) return null;
  if (!state.charts[id]) {
    state.charts[id] = echarts.init(el, null, { renderer: 'canvas' });
  }
  return state.charts[id];
}

function resizeCharts() {
  Object.values(state.charts).forEach((ch) => {
    try { ch.resize(); } catch (_) {}
  });
}

const TOOLTIP_THEME = {
  backgroundColor: '#202938',
  borderWidth: 0,
  padding: [10, 14],
  textStyle: {
    color: '#F5F6F8',
    fontFamily: 'Inter, system-ui, sans-serif',
    fontSize: 12,
  },
};

// ==========================================
// NAVIGATION & SIDEBAR
// ==========================================
function navigateTo(pageKey) {
  const cfg = PAGE_CONFIG[pageKey] || PAGE_CONFIG.ringkasan;
  state.activePage = pageKey;

  document.getElementById('breadcrumb-current').textContent = cfg.crumb;
  document.getElementById('page-eyebrow').textContent = cfg.eyebrow;
  document.getElementById('page-title').textContent = cfg.title;
  document.getElementById('page-subtitle').textContent = cfg.subtitle;
  document.getElementById('filter-bar').classList.toggle('hidden', !cfg.showFilter);

  document.querySelectorAll('.nav[data-page]').forEach((btn) => {
    const isActive = btn.dataset.page === pageKey;
    btn.classList.toggle('active', isActive);
    btn.setAttribute('aria-selected', String(isActive));
  });

  document.querySelectorAll('.page-view').forEach((panel) => {
    panel.classList.toggle('active', panel.id === `page-${pageKey}`);
  });

  closeMobileSidebar();
  renderCurrentPage();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function openMobileSidebar() {
  document.getElementById('sidebar').classList.add('open');
  document.getElementById('sidebar-backdrop').classList.remove('hidden');
}

function closeMobileSidebar() {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('sidebar-backdrop').classList.add('hidden');
}

// ==========================================
// DATA FETCHING & FILTER SYNC
// ==========================================
async function fetchDashboard() {
  setLoading(true);
  try {
    const params = new URLSearchParams();
    params.set('category', state.filters.category);
    params.set('city', state.filters.city);
    if (state.filters.min_price !== '') params.set('min_price', state.filters.min_price);
    if (state.filters.max_price !== '') params.set('max_price', state.filters.max_price);
    params.set('min_rating', String(state.filters.min_rating));
    params.set('top_n', String(state.filters.top_n));
    params.set('sort_by', state.filters.sort_by);
    if (state.filters.search.trim()) params.set('search', state.filters.search.trim());

    const res = await fetch(`/api/dashboard?${params.toString()}`);
    if (!res.ok) throw new Error('Gagal memuat data dari server.');
    state.data = await res.json();
    state.lastUpdated = new Date();

    syncSourceUI(state.data.meta);
    renderActiveFilterChips();
    renderCurrentPage();
  } catch (err) {
    showToast(err.message || 'Gagal terhubung ke backend FastAPI', true);
  } finally {
    setLoading(false);
  }
}

function populateFilterOptions(meta) {
  const catSel = document.getElementById('filter-category');
  const citySel = document.getElementById('filter-city');

  catSel.innerHTML =
    '<option value="ALL">Semua Kategori</option>' +
    meta.categories.map((c) => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
  catSel.value = meta.categories.includes(state.filters.category) ? state.filters.category : 'ALL';

  citySel.innerHTML =
    '<option value="ALL">Semua Kota</option>' +
    meta.cities.map((c) => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
  citySel.value = meta.cities.includes(state.filters.city) ? state.filters.city : 'ALL';
}

function syncSourceUI(meta) {
  const isCustom = meta.source === 'custom';
  ['sidebar-source-dot', 'top-source-dot', 'meta-source-dot'].forEach((id) => {
    document.getElementById(id).classList.toggle('custom', isCustom);
  });

  document.getElementById('sidebar-source-title').textContent = isCustom
    ? truncate(meta.filename, 20)
    : 'Dataset Tokopedia';
  document.getElementById('top-source-label').textContent = isCustom
    ? `Kustom: ${truncate(meta.filename, 18)}`
    : 'Dataset Tokopedia';

  document.getElementById('meta-dataset-text').innerHTML = isCustom
    ? `Dataset aktif <b>${escapeHtml(meta.filename)}</b> · ${fmtInt(meta.total_rows)} produk`
    : `Dataset aktif <b>Tokopedia</b> · ${fmtInt(meta.total_rows)} produk`;

  if (state.lastUpdated) {
    const hh = String(state.lastUpdated.getHours()).padStart(2, '0');
    const mm = String(state.lastUpdated.getMinutes()).padStart(2, '0');
    document.getElementById('meta-updated').textContent = `Diperbarui pukul ${hh}:${mm} WIB`;
  }

  document.getElementById('upload-current-status').innerHTML = isCustom
    ? `Status saat ini: menggunakan dataset kustom <b>${escapeHtml(meta.filename)}</b> (${fmtInt(meta.total_rows)} produk · ${fmtInt(meta.total_merchants)} toko).`
    : `Status saat ini: menggunakan dataset bawaan <b>Tokopedia</b> (${fmtInt(meta.total_rows)} produk · ${fmtInt(meta.total_merchants)} toko).`;

  document.getElementById('btn-reset-dataset').classList.toggle('hidden', !isCustom);
}

function renderActiveFilterChips() {
  const chips = [];
  if (state.filters.category !== 'ALL') {
    chips.push({ label: `Kategori: ${state.filters.category}`, clear: () => setFilter('category', 'ALL') });
  }
  if (state.filters.city !== 'ALL') {
    chips.push({ label: `Kota: ${state.filters.city}`, clear: () => setFilter('city', 'ALL') });
  }
  if (state.filters.priceKey !== 'ALL') {
    chips.push({ label: `Harga: ${PRICE_LABELS[state.filters.priceKey]}`, clear: () => setFilter('priceKey', 'ALL') });
  }
  if (Number(state.filters.min_rating) > 0) {
    chips.push({ label: `Rating ≥ ${state.filters.min_rating}`, clear: () => setFilter('min_rating', 0) });
  }
  if (state.filters.search.trim()) {
    chips.push({ label: `Cari: "${state.filters.search.trim()}"`, clear: () => setFilter('search', '') });
  }

  document.getElementById('btn-reset-filters').classList.toggle('hidden', chips.length === 0);

  const row = document.getElementById('active-filter-chips');
  if (!chips.length) {
    row.classList.add('hidden');
    row.innerHTML = '';
    return;
  }
  row.classList.remove('hidden');
  row.innerHTML = '';
  chips.forEach((c) => {
    const el = document.createElement('span');
    el.className = 'filter-chip';
    el.innerHTML = `${escapeHtml(c.label)} <button type="button" aria-label="Hapus filter">&times;</button>`;
    el.querySelector('button').addEventListener('click', c.clear);
    row.appendChild(el);
  });
}

function setFilter(key, val) {
  if (key === 'category') {
    state.filters.category = val;
    document.getElementById('filter-category').value = val;
  } else if (key === 'city') {
    state.filters.city = val;
    document.getElementById('filter-city').value = val;
  } else if (key === 'priceKey') {
    state.filters.priceKey = val;
    document.getElementById('filter-price').value = val;
    if (val === 'ALL') {
      state.filters.min_price = '';
      state.filters.max_price = '';
    } else {
      const [mn, mx] = val.split('-');
      state.filters.min_price = mn;
      state.filters.max_price = mx;
    }
  } else if (key === 'min_rating') {
    state.filters.min_rating = Number(val);
    document.getElementById('filter-rating').value = String(val);
  } else if (key === 'search') {
    state.filters.search = val;
    document.getElementById('global-search').value = val;
  }
  fetchDashboard();
}

function resetAllFilters(shouldFetch = true) {
  state.filters.category = 'ALL';
  state.filters.city = 'ALL';
  state.filters.priceKey = 'ALL';
  state.filters.min_price = '';
  state.filters.max_price = '';
  state.filters.min_rating = 0;
  state.filters.search = '';

  document.getElementById('filter-category').value = 'ALL';
  document.getElementById('filter-city').value = 'ALL';
  document.getElementById('filter-price').value = 'ALL';
  document.getElementById('filter-rating').value = '0';
  document.getElementById('global-search').value = '';

  if (shouldFetch) fetchDashboard();
}

// ==========================================
// PAGE RENDER ROUTER
// ==========================================
function renderCurrentPage() {
  if (!state.data) return;
  switch (state.activePage) {
    case 'ringkasan': renderMarketOverview(); break;
    case 'produk': renderProdukPage(); break;
    case 'waktu': renderWaktuPage(); break;
    case 'geografi': renderGeografiPage(); break;
    case 'klaster': renderKlasterPage(); break;
    default: break;
  }
  requestAnimationFrame(resizeCharts);
}

// ==========================================
// PAGE 1: MARKET OVERVIEW
// ==========================================
function renderMarketOverview() {
  const { kpis, categories, top_products, time_trends, geo_summary } = state.data;

  // B. Exact 4 KPIs (Total Produk, Total Toko, Total Unit Terjual, Estimated GMV)
  document.getElementById('kpi-products').textContent = fmtInt(kpis.total_products);
  document.getElementById('kpi-products-note').textContent =
    `${kpis.coverage_pct}% dari ${fmtInt(kpis.total_catalog_raw)} total katalog`;

  document.getElementById('kpi-merchants').textContent = fmtInt(kpis.total_merchants);
  document.getElementById('kpi-merchants-note').textContent =
    `Tersebar di ${fmtInt(kpis.total_cities)} kota · Rating ${kpis.avg_rating.toFixed(2)}/5`;

  document.getElementById('kpi-volume').textContent = fmtUnitShort(kpis.total_volume_sold);
  document.getElementById('kpi-volume-note').textContent =
    `${fmtInt(kpis.total_volume_sold)} unit tercatat`;

  document.getElementById('kpi-gmv').textContent = fmtRupiahShort(kpis.total_gmv);
  document.getElementById('kpi-gmv-note').textContent =
    `Median harga ${fmtRupiahFull(kpis.median_price)} · Diskon ${kpis.avg_discount.toFixed(1)}%`;

  // C. Main Analytics: Sales Performance by Category (Vertical Column Chart like preview!)
  const metric = state.catMetric;
  const topCats = [...categories].sort((a, b) => b[metric] - a[metric]).slice(0, 7);
  const chCat = getChart('chart-overview-category');
  chCat.setOption({
    tooltip: {
      ...TOOLTIP_THEME,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const c = topCats[params[0].dataIndex];
        return `
          <div style="font-weight:600;margin-bottom:5px">${escapeHtml(c.kategori)}</div>
          <div>Unit Terjual: <b>${fmtInt(c.total_terjual)}</b></div>
          <div>Estimasi GMV: <b>${fmtRupiahShort(c.total_gmv)}</b></div>
          <div>Jumlah Produk: <b>${fmtInt(c.total_produk)}</b></div>
          <div>Rata-rata Harga: <b>${fmtRupiahFull(c.avg_harga)}</b></div>
        `;
      },
    },
    grid: { top: 18, left: 10, right: 14, bottom: 26, containLabel: true },
    xAxis: {
      type: 'category',
      data: topCats.map((c) => shortCategoryLabel(c.kategori)),
      axisLine: { lineStyle: { color: PALETTE.border } },
      axisTick: { show: false },
      axisLabel: { color: PALETTE.muted, fontSize: 11, interval: 0 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: PALETTE.grid } },
      axisLabel: {
        color: PALETTE.subtle,
        fontSize: 11,
        formatter: (v) => (metric === 'total_gmv' ? fmtRupiahShort(v) : fmtUnitShort(v)),
      },
    },
    series: [{
      type: 'bar',
      barMaxWidth: 42,
      cursor: 'pointer',
      data: topCats.map((c, idx) => ({
        value: c[metric],
        itemStyle: {
          color: idx === 0 ? PALETTE.secondary : PALETTE.primaryBar,
          borderRadius: [4, 4, 0, 0],
        },
        emphasis: {
          itemStyle: { color: idx === 0 ? '#B36846' : PALETTE.primary },
        },
      })),
    }],
  }, true);

  chCat.off('click');
  chCat.on('click', (p) => {
    const clicked = topCats[p.dataIndex];
    if (clicked) {
      setFilter('category', state.filters.category === clicked.kategori ? 'ALL' : clicked.kategori);
    }
  });

  // D. Market Highlights
  const insightEl = document.getElementById('overview-insight');
  const barsEl = document.getElementById('overview-category-bars');
  if (!categories.length) {
    insightEl.innerHTML = 'Tidak ada produk yang cocok dengan kombinasi filter saat ini. Klik <b>Reset filter</b> untuk melihat seluruh data.';
    barsEl.innerHTML = '';
  } else {
    const leader = topCats[0];
    const totalMetricSum = Math.max(1, categories.reduce((acc, c) => acc + c[metric], 0));
    insightEl.innerHTML = metric === 'total_gmv'
      ? `<b>${escapeHtml(leader.kategori)}</b> menyumbang estimasi GMV tertinggi sebesar <b>${fmtRupiahShort(leader.total_gmv)}</b> dari ${fmtInt(leader.total_produk)} produk aktif.`
      : `<b>${escapeHtml(leader.kategori)}</b> menjadi kategori dengan volume penjualan tertinggi, mencapai <b>${fmtUnitShort(leader.total_terjual)} unit</b> (${fmtRupiahShort(leader.total_gmv)}).`;

    const maxLeaderVal = Math.max(1, leader[metric]);
    barsEl.innerHTML = topCats.slice(0, 4).map((c, i) => {
      const pct = ((c[metric] / totalMetricSum) * 100).toFixed(1).replace('.', ',');
      const widthPct = Math.max(6, Math.round((c[metric] / maxLeaderVal) * 100));
      return `
        <div class="cat-row">
          <div class="cat-head">
            <span>${escapeHtml(c.kategori)}</span>
            <b>${pct}%</b>
          </div>
          <div class="track"><div class="fill ${i === 0 ? 'top' : ''}" style="width:${widthPct}%"></div></div>
        </div>
      `;
    }).join('');
  }

  // E. Top Performing Products (Compact 5-row summary)
  const previewRows = top_products.slice(0, 5);
  const tbodyOv = document.getElementById('tbody-overview-products');
  tbodyOv.innerHTML = !previewRows.length
    ? `<tr><td colspan="7" style="text-align:center;color:var(--subtle);padding:22px">Tidak ada produk yang sesuai filter.</td></tr>`
    : previewRows.map((p, i) => `
      <tr>
        <td class="col-rank">${String(i + 1).padStart(2, '0')}</td>
        <td>
          <a class="prod-link" href="${escapeHtml(p.url)}" target="_blank" rel="noopener" title="${escapeHtml(p.nama_produk)}">${escapeHtml(p.nama_produk)}</a>
          <small class="prod-sub">${escapeHtml(p.nama_toko)}</small>
        </td>
        <td><span class="cat-badge">${escapeHtml(shortCategoryLabel(p.kategori))}</span></td>
        <td>${escapeHtml(p.lokasi)}</td>
        <td class="num">${fmtRupiahFull(p.harga)}</td>
        <td class="num"><span class="rating-val">${p.rating.toFixed(1).replace('.', ',')}</span></td>
        <td class="num"><strong>${fmtInt(p.terjual)}</strong></td>
      </tr>
    `).join('');

  // Bottom Snapshots
  document.getElementById('overview-tx-summary').innerHTML = `
    <div class="mini-stat"><span>Jam belanja tersibuk</span><b>${String(time_trends.peak_hour).padStart(2, '0')}:00 WIB</b></div>
    <div class="mini-stat"><span>Hari paling aktif</span><b>${escapeHtml(time_trends.peak_day)}</b></div>
    <div class="mini-stat"><span>Tanggal lonjakan tertinggi</span><b>${escapeHtml(time_trends.peak_date)}</b></div>
  `;

  document.getElementById('overview-geo-summary').innerHTML = `
    <div class="mini-stat"><span>Kontribusi Jabodetabek</span><b>${String(geo_summary.jabodetabek_share_pct).replace('.', ',')}%</b></div>
    <div class="mini-stat"><span>Wilayah non-Jabodetabek</span><b>${String(geo_summary.non_jabo_share_pct || 0).replace('.', ',')}%</b></div>
    <div class="mini-stat"><span>Kota dengan volume tertinggi</span><b>${escapeHtml(geo_summary.top_city)}</b></div>
  `;
}

// ==========================================
// PAGE 2: PRODUK & TOKO TERLARIS
// ==========================================
function renderProdukPage() {
  const { top_products, top_shops, price_tiers, top_products_total_match } = state.data;
  const sortField = state.filters.sort_by === 'estimasi_gmv' ? 'gmv'
    : state.filters.sort_by === 'Harga (IDR)' ? 'harga'
    : state.filters.sort_by === 'Rating' ? 'rating'
    : 'terjual';

  document.getElementById('product-match-count').textContent =
    `Menampilkan ${top_products.length} teratas dari ${fmtInt(top_products_total_match)} produk cocok`;

  // Top Products Horizontal Bar
  const slice = [...top_products].slice(0, 10).reverse();
  getChart('chart-top-products').setOption({
    tooltip: {
      ...TOOLTIP_THEME,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (p) => {
        const item = slice[p[0].dataIndex];
        return `
          <div style="font-weight:600;max-width:270px;white-space:normal;margin-bottom:4px">${escapeHtml(item.nama_produk)}</div>
          <div>Toko: ${escapeHtml(item.nama_toko)} (${escapeHtml(item.lokasi)})</div>
          <div>Harga: <b>${fmtRupiahFull(item.harga)}</b> · Terjual: <b>${fmtInt(item.terjual)}</b></div>
          <div>Estimasi GMV: <b>${fmtRupiahShort(item.gmv)}</b></div>
        `;
      },
    },
    grid: { top: 8, left: 8, right: 56, bottom: 16, containLabel: true },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: PALETTE.grid } },
      axisLabel: {
        color: PALETTE.subtle,
        fontSize: 10.5,
        formatter: (v) => (sortField === 'gmv' || sortField === 'harga' ? fmtRupiahShort(v) : fmtUnitShort(v)),
      },
    },
    yAxis: {
      type: 'category',
      data: slice.map((p) => truncate(p.nama_produk, 30)),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: PALETTE.ink, fontSize: 11 },
    },
    series: [{
      type: 'bar',
      barMaxWidth: 18,
      label: {
        show: true,
        position: 'right',
        distance: 5,
        color: PALETTE.muted,
        fontSize: 10,
        formatter: (p) => (sortField === 'gmv' || sortField === 'harga' ? fmtRupiahShort(p.value) : sortField === 'rating' ? Number(p.value).toFixed(1) : fmtUnitShort(p.value)),
      },
      data: slice.map((p, idx) => ({
        value: p[sortField],
        itemStyle: {
          color: idx === slice.length - 1 ? PALETTE.secondary : PALETTE.primaryBar,
          borderRadius: [0, 4, 4, 0],
        },
      })),
    }],
  }, true);

  // Price Tier Distribution Combo
  getChart('chart-price-tier').setOption({
    tooltip: {
      ...TOOLTIP_THEME,
      trigger: 'axis',
      formatter: (p) => {
        const t = price_tiers[p[0].dataIndex];
        return `
          <div style="font-weight:600;margin-bottom:4px">${escapeHtml(t.price_tier)}</div>
          <div>Unit Terjual: <b>${fmtInt(t.total_terjual)}</b></div>
          <div>Estimasi GMV: <b>${fmtRupiahShort(t.total_gmv)}</b></div>
          <div>Jumlah Produk: <b>${fmtInt(t.total_produk)}</b></div>
        `;
      },
    },
    legend: { top: 0, right: 4, itemWidth: 10, itemHeight: 8, textStyle: { color: PALETTE.muted, fontSize: 11 } },
    grid: { top: 34, left: 10, right: 10, bottom: 16, containLabel: true },
    xAxis: {
      type: 'category',
      data: price_tiers.map((t) => t.short_label),
      axisLine: { lineStyle: { color: PALETTE.border } },
      axisTick: { show: false },
      axisLabel: { color: PALETTE.muted, fontSize: 11 },
    },
    yAxis: [
      { type: 'value', splitLine: { lineStyle: { color: PALETTE.grid } }, axisLabel: { color: PALETTE.subtle, fontSize: 10.5, formatter: fmtUnitShort } },
      { type: 'value', splitLine: { show: false }, axisLabel: { color: PALETTE.secondary, fontSize: 10.5, formatter: fmtRupiahShort } },
    ],
    series: [
      { name: 'Unit Terjual', type: 'bar', barMaxWidth: 32, itemStyle: { color: PALETTE.primaryBar, borderRadius: [4, 4, 0, 0] }, data: price_tiers.map((t) => t.total_terjual) },
      { name: 'Estimasi GMV', type: 'line', yAxisIndex: 1, smooth: 0.25, symbolSize: 7, lineStyle: { color: PALETTE.secondary, width: 2 }, itemStyle: { color: PALETTE.secondary }, data: price_tiers.map((t) => t.total_gmv) },
    ],
  }, true);

  // Full Top Products Table
  const tbodyProd = document.getElementById('tbody-top-products');
  tbodyProd.innerHTML = !top_products.length
    ? `<tr><td colspan="9" style="text-align:center;color:var(--subtle);padding:24px">Tidak ada produk yang cocok dengan filter atau pencarian.</td></tr>`
    : top_products.map((p, idx) => `
      <tr>
        <td class="col-rank">${String(idx + 1).padStart(2, '0')}</td>
        <td>
          <a class="prod-link" href="${escapeHtml(p.url)}" target="_blank" rel="noopener" title="${escapeHtml(p.nama_produk)}">${escapeHtml(p.nama_produk)}</a>
          <small class="prod-sub">${escapeHtml(p.nama_toko)} · ${escapeHtml(p.product_id)}</small>
        </td>
        <td><span class="cat-badge">${escapeHtml(p.kategori)}</span></td>
        <td>${escapeHtml(p.lokasi)}</td>
        <td class="num">${fmtRupiahFull(p.harga)}</td>
        <td class="num">${p.diskon > 0 ? `${p.diskon}%` : '—'}</td>
        <td class="num"><span class="rating-val">${p.rating.toFixed(1).replace('.', ',')}</span></td>
        <td class="num"><strong>${fmtInt(p.terjual)}</strong></td>
        <td class="num">${fmtRupiahShort(p.gmv)}</td>
      </tr>
    `).join('');

  // Top Shops Table
  const tbodyShops = document.getElementById('tbody-top-shops');
  tbodyShops.innerHTML = !top_shops.length
    ? `<tr><td colspan="7" style="text-align:center;color:var(--subtle);padding:24px">Belum ada data toko.</td></tr>`
    : top_shops.map((s, idx) => `
      <tr>
        <td class="col-rank">${String(idx + 1).padStart(2, '0')}</td>
        <td><strong>${escapeHtml(s.nama_toko)}</strong></td>
        <td>${escapeHtml(s.lokasi)}</td>
        <td class="num">${fmtInt(s.total_produk)}</td>
        <td class="num"><strong>${fmtInt(s.total_terjual)}</strong></td>
        <td class="num">${fmtRupiahShort(s.total_gmv)}</td>
        <td class="num"><span class="rating-val">${s.avg_rating.toFixed(2).replace('.', ',')}</span></td>
      </tr>
    `).join('');
}

// ==========================================
// PAGE 3: WAKTU BELANJA PUNCAK
// ==========================================
function renderWaktuPage() {
  const tt = state.data.time_trends;
  document.getElementById('tx-total-badge').textContent = `${fmtInt(tt.total_transactions)} log transaksi`;

  document.getElementById('waktu-kpis').innerHTML = `
    <article class="kpi">
      <div class="kpi-label">Jam Belanja Tersibuk</div>
      <div class="kpi-value">${String(tt.peak_hour).padStart(2, '0')}:00 WIB</div>
      <div class="kpi-note">${fmtInt(tt.peak_hour_count)} item tercatat pada jam puncak</div>
    </article>
    <article class="kpi">
      <div class="kpi-label">Hari Paling Aktif</div>
      <div class="kpi-value">${escapeHtml(tt.peak_day)}</div>
      <div class="kpi-note">Intensitas keranjang belanja tertinggi mingguan</div>
    </article>
    <article class="kpi">
      <div class="kpi-label">Lonjakan Tanggal Tertinggi</div>
      <div class="kpi-value">${escapeHtml(tt.peak_date)}</div>
      <div class="kpi-note">${fmtInt(tt.peak_date_count)} item dalam satu hari</div>
    </article>
  `;

  document.getElementById('waktu-insight').innerHTML =
    `<b>Temuan Operasional:</b> Lonjakan aktivitas transaksi terkonsentrasi pada pukul <b>${String(tt.peak_hour).padStart(2, '0')}:00 WIB</b> dan hari <b>${escapeHtml(tt.peak_day)}</b> (puncak harian pada <b>${escapeHtml(tt.peak_date)}</b>). Rekomendasi: siapkan autoscaling pada pipeline Apache Kafka dan Spark Structured Streaming menjelang jendela jam sibuk tersebut.`;

  // Daily Trend
  getChart('chart-daily-trend').setOption({
    tooltip: { ...TOOLTIP_THEME, trigger: 'axis' },
    grid: { top: 24, left: 10, right: 16, bottom: 52, containLabel: true },
    xAxis: {
      type: 'category',
      data: tt.daily.map((d) => d.date),
      axisLine: { lineStyle: { color: PALETTE.border } },
      axisLabel: { color: PALETTE.subtle, fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: PALETTE.grid } },
      axisLabel: { color: PALETTE.subtle, fontSize: 11 },
    },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', height: 20, bottom: 8, borderColor: PALETTE.border, fillerColor: 'rgba(82, 107, 155, 0.14)', handleStyle: { color: PALETTE.primary } },
    ],
    series: [{
      name: 'Item Masuk Keranjang',
      type: 'line',
      smooth: 0.2,
      showSymbol: false,
      lineStyle: { color: PALETTE.primary, width: 2 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(82, 107, 155, 0.18)' },
          { offset: 1, color: 'rgba(82, 107, 155, 0.01)' },
        ]),
      },
      markPoint: {
        symbolSize: 40,
        itemStyle: { color: PALETTE.secondary },
        label: { fontSize: 10 },
        data: [{ type: 'max', name: 'Puncak' }],
      },
      data: tt.daily.map((d) => d.count),
    }],
  }, true);

  // Hourly Bar
  const maxH = Math.max(...tt.hourly.map((h) => h.count), 1);
  getChart('chart-hourly').setOption({
    tooltip: { ...TOOLTIP_THEME, trigger: 'axis', formatter: (p) => `Jam <b>${p[0].name}:00 WIB</b><br/>Volume: <b>${fmtInt(p[0].value)} item</b>` },
    grid: { top: 14, left: 10, right: 12, bottom: 16, containLabel: true },
    xAxis: { type: 'category', data: tt.hourly.map((h) => String(h.hour).padStart(2, '0')), axisLine: { lineStyle: { color: PALETTE.border } }, axisTick: { show: false }, axisLabel: { color: PALETTE.muted, fontSize: 11 } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: PALETTE.grid } }, axisLabel: { color: PALETTE.subtle, fontSize: 11 } },
    series: [{
      type: 'bar',
      barMaxWidth: 24,
      data: tt.hourly.map((h) => ({
        value: h.count,
        itemStyle: { color: h.count >= maxH * 0.85 ? PALETTE.secondary : PALETTE.primaryBar, borderRadius: [4, 4, 0, 0] },
      })),
    }],
  }, true);

  // Day of Week Bar
  const maxD = Math.max(...tt.day_of_week.map((d) => d.count), 1);
  getChart('chart-dow').setOption({
    tooltip: { ...TOOLTIP_THEME, trigger: 'axis', formatter: (p) => `Hari <b>${escapeHtml(p[0].name)}</b><br/>Volume: <b>${fmtInt(p[0].value)} item</b>` },
    grid: { top: 14, left: 10, right: 12, bottom: 16, containLabel: true },
    xAxis: { type: 'category', data: tt.day_of_week.map((d) => d.day_id), axisLine: { lineStyle: { color: PALETTE.border } }, axisTick: { show: false }, axisLabel: { color: PALETTE.muted, fontSize: 11.5 } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: PALETTE.grid } }, axisLabel: { color: PALETTE.subtle, fontSize: 11 } },
    series: [{
      type: 'bar',
      barMaxWidth: 34,
      data: tt.day_of_week.map((d) => ({
        value: d.count,
        itemStyle: { color: d.count >= maxD * 0.96 ? PALETTE.primary : PALETTE.primaryLight, borderRadius: [4, 4, 0, 0] },
      })),
    }],
  }, true);
}

// ==========================================
// PAGE 4: SEBARAN WILAYAH
// ==========================================
function renderGeografiPage() {
  const { locations, geo_summary, kpis } = state.data;
  const metric = state.geoMetric;
  const sorted = [...locations].sort((a, b) => a[metric] - b[metric]);

  document.getElementById('geo-kpis').innerHTML = `
    <article class="kpi">
      <div class="kpi-label">Kontribusi Jabodetabek</div>
      <div class="kpi-value">${String(geo_summary.jabodetabek_share_pct).replace('.', ',')}%</div>
      <div class="kpi-note">Jakarta, Bogor, Depok, Tangerang &amp; Bekasi</div>
    </article>
    <article class="kpi">
      <div class="kpi-label">Wilayah Non-Jabodetabek</div>
      <div class="kpi-value">${String(geo_summary.non_jabo_share_pct || 0).replace('.', ',')}%</div>
      <div class="kpi-note">Kota hub regional di luar Jabodetabek</div>
    </article>
    <article class="kpi">
      <div class="kpi-label">Kota Volume Tertinggi</div>
      <div class="kpi-value">${escapeHtml(geo_summary.top_city)}</div>
      <div class="kpi-note">${fmtUnitShort(geo_summary.top_city_volume)} unit · dari ${fmtInt(kpis.total_cities)} kota</div>
    </article>
  `;

  // Geo Horizontal Bar
  const chGeo = getChart('chart-geo-bar');
  chGeo.setOption({
    tooltip: {
      ...TOOLTIP_THEME,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (p) => {
        const l = sorted[p[0].dataIndex];
        return `
          <div style="font-weight:600;margin-bottom:4px">${escapeHtml(l.lokasi)}</div>
          <div>Unit Terjual: <b>${fmtInt(l.total_terjual)}</b></div>
          <div>Estimasi GMV: <b>${fmtRupiahShort(l.total_gmv)}</b></div>
          <div>Produk Aktif: <b>${fmtInt(l.total_produk)}</b> · Rating: <b>${l.avg_rating.toFixed(2)}</b></div>
        `;
      },
    },
    grid: { top: 8, left: 10, right: 62, bottom: 14, containLabel: true },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: PALETTE.grid } },
      axisLabel: { color: PALETTE.subtle, fontSize: 11, formatter: (v) => (metric === 'total_gmv' ? fmtRupiahShort(v) : fmtUnitShort(v)) },
    },
    yAxis: { type: 'category', data: sorted.map((l) => l.lokasi), axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: PALETTE.ink, fontSize: 11.5 } },
    series: [{
      type: 'bar',
      barMaxWidth: 19,
      cursor: 'pointer',
      label: {
        show: true,
        position: 'right',
        distance: 6,
        color: PALETTE.muted,
        fontSize: 10.5,
        formatter: (p) => (metric === 'total_gmv' ? fmtRupiahShort(p.value) : fmtUnitShort(p.value)),
      },
      data: sorted.map((l, idx) => ({
        value: l[metric],
        itemStyle: { color: idx === sorted.length - 1 ? PALETTE.secondary : PALETTE.primaryBar, borderRadius: [0, 4, 4, 0] },
      })),
    }],
  }, true);

  chGeo.off('click');
  chGeo.on('click', (p) => {
    const clicked = sorted[p.dataIndex];
    if (clicked) {
      setFilter('city', state.filters.city === clicked.lokasi ? 'ALL' : clicked.lokasi);
    }
  });

  // Geo Bubble Scatter
  const maxVol = Math.max(...locations.map((l) => l.total_terjual), 1);
  getChart('chart-geo-bubble').setOption({
    tooltip: {
      ...TOOLTIP_THEME,
      formatter: (p) => {
        const d = p.data.raw;
        return `<b>${escapeHtml(d.lokasi)}</b><br/>Produk: ${fmtInt(d.total_produk)}<br/>Rating: ${d.avg_rating.toFixed(2)}<br/>Unit Terjual: ${fmtInt(d.total_terjual)}`;
      },
    },
    grid: { top: 22, left: 12, right: 20, bottom: 26, containLabel: true },
    xAxis: { type: 'value', name: 'Produk Aktif', nameLocation: 'middle', nameGap: 24, nameTextStyle: { color: PALETTE.muted, fontSize: 11 }, splitLine: { lineStyle: { color: PALETTE.grid } }, axisLabel: { color: PALETTE.subtle, fontSize: 11 } },
    yAxis: { type: 'value', name: 'Rating', scale: true, nameTextStyle: { color: PALETTE.muted, fontSize: 11 }, splitLine: { lineStyle: { color: PALETTE.grid } }, axisLabel: { color: PALETTE.subtle, fontSize: 11 } },
    series: [{
      type: 'scatter',
      symbolSize: (val) => Math.max(11, Math.sqrt(val[2] / maxVol) * 46),
      label: { show: true, position: 'top', formatter: (p) => (p.dataIndex < 5 ? p.data.raw.lokasi : ''), fontSize: 10.5, color: PALETTE.ink, fontWeight: 500 },
      data: locations.map((l, idx) => ({
        value: [l.total_produk, l.avg_rating, l.total_terjual],
        raw: l,
        itemStyle: { color: idx === 0 ? PALETTE.secondary : CHART_PALETTE[idx % CHART_PALETTE.length], opacity: 0.82, borderColor: '#FFF', borderWidth: 1.5 },
      })),
    }],
  }, true);

  // Geo Table
  const tbodyGeo = document.getElementById('tbody-geo');
  tbodyGeo.innerHTML = !locations.length
    ? `<tr><td colspan="6" style="text-align:center;color:var(--subtle);padding:24px">Tidak ada data wilayah.</td></tr>`
    : locations.map((l, idx) => `
      <tr>
        <td class="col-rank">${String(idx + 1).padStart(2, '0')}</td>
        <td><strong>${escapeHtml(l.lokasi)}</strong></td>
        <td class="num">${fmtInt(l.total_produk)}</td>
        <td class="num"><strong>${fmtInt(l.total_terjual)}</strong></td>
        <td class="num">${fmtRupiahShort(l.total_gmv)}</td>
        <td class="num"><span class="rating-val">${l.avg_rating.toFixed(2).replace('.', ',')}</span></td>
      </tr>
    `).join('');
}

// ==========================================
// PAGE 5: SEGMENTASI PRODUK (ML — K-MEANS)
// ==========================================
function renderKlasterPage() {
  const { clusters, demographics } = state.data;
  const { summary, scatter } = clusters;

  document.getElementById('ml-sample-count').textContent = `${fmtInt(scatter.length)} titik aktif`;

  const names = summary.map((c) => c.cluster_label);
  const grouped = {};
  names.forEach((n) => (grouped[n] = []));
  scatter.forEach((pt) => {
    if (!grouped[pt.cluster]) grouped[pt.cluster] = [];
    grouped[pt.cluster].push(pt);
  });

  // Scatter Plot
  getChart('chart-cluster-scatter').setOption({
    tooltip: {
      ...TOOLTIP_THEME,
      formatter: (p) => {
        const d = p.data.raw;
        return `
          <div style="font-weight:600;max-width:260px;white-space:normal;margin-bottom:4px">${escapeHtml(d.nama)}</div>
          <div style="color:#B4C1D6;margin-bottom:4px">${escapeHtml(d.cluster)}</div>
          <div>Harga: <b>${fmtRupiahFull(d.harga)}</b> · Terjual: <b>${fmtInt(d.terjual)}</b></div>
          <div>Rating: <b>${d.rating}</b> · Toko: ${escapeHtml(d.toko)}</div>
        `;
      },
    },
    legend: { type: 'scroll', bottom: 0, icon: 'circle', itemWidth: 8, itemHeight: 8, textStyle: { color: PALETTE.muted, fontSize: 11 } },
    grid: { top: 14, left: 14, right: 16, bottom: 52, containLabel: true },
    xAxis: { type: 'log', name: 'Harga (IDR, Log)', nameLocation: 'middle', nameGap: 25, nameTextStyle: { color: PALETTE.muted, fontSize: 11 }, splitLine: { lineStyle: { color: PALETTE.grid } }, axisLabel: { color: PALETTE.subtle, fontSize: 10.5, formatter: fmtRupiahShort } },
    yAxis: { type: 'log', name: 'Unit Terjual (Log)', nameTextStyle: { color: PALETTE.muted, fontSize: 11 }, splitLine: { lineStyle: { color: PALETTE.grid } }, axisLabel: { color: PALETTE.subtle, fontSize: 10.5, formatter: fmtUnitShort } },
    color: CLUSTER_COLORS,
    series: names.map((name) => ({
      name,
      type: 'scatter',
      symbolSize: 6.5,
      itemStyle: { opacity: 0.72 },
      data: (grouped[name] || []).map((pt) => ({ value: [pt.harga, pt.terjual], raw: pt })),
    })),
  }, true);

  // Cluster Donut
  getChart('chart-cluster-donut').setOption({
    tooltip: { ...TOOLTIP_THEME, trigger: 'item', formatter: (p) => `<b>${escapeHtml(p.name)}</b><br/>${fmtInt(p.value)} produk (${p.percent}%)` },
    legend: { type: 'scroll', bottom: 0, icon: 'circle', itemWidth: 8, itemHeight: 8, textStyle: { color: PALETTE.muted, fontSize: 11 } },
    color: CLUSTER_COLORS,
    series: [{
      type: 'pie',
      radius: ['54%', '74%'],
      center: ['50%', '43%'],
      itemStyle: { borderColor: '#FFF', borderWidth: 2 },
      label: { show: false },
      data: summary.map((c) => ({ name: c.cluster_label, value: c.jumlah_produk })),
    }],
  }, true);

  // Cluster Summary Table
  const tbody = document.getElementById('tbody-clusters');
  tbody.innerHTML = !summary.length
    ? `<tr><td colspan="8" style="text-align:center;color:var(--subtle);padding:24px">Tidak ada data klaster pada filter ini.</td></tr>`
    : summary.map((c) => `
      <tr>
        <td><strong>${escapeHtml(c.cluster_label)}</strong></td>
        <td class="num">${fmtInt(c.jumlah_produk)}</td>
        <td class="num">${String(c.share_pct).replace('.', ',')}%</td>
        <td class="num">${fmtRupiahFull(c.rata_harga)}</td>
        <td class="num">${fmtInt(c.rata_terjual)}</td>
        <td class="num"><span class="rating-val">${c.rata_rating.toFixed(2).replace('.', ',')}</span></td>
        <td class="num">${String(c.rata_diskon.toFixed(1)).replace('.', ',')}%</td>
        <td class="num"><strong>${fmtRupiahShort(c.total_gmv)}</strong></td>
      </tr>
    `).join('');

  // Demographics Age & Gender
  getChart('chart-demo-age').setOption({
    tooltip: { ...TOOLTIP_THEME, trigger: 'axis' },
    grid: { top: 14, left: 10, right: 12, bottom: 16, containLabel: true },
    xAxis: { type: 'category', data: demographics.age_stats.map((a) => a.group), axisLine: { lineStyle: { color: PALETTE.border } }, axisTick: { show: false }, axisLabel: { color: PALETTE.muted, fontSize: 11.5 } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: PALETTE.grid } }, axisLabel: { color: PALETTE.subtle, fontSize: 11 } },
    series: [{
      name: 'Item Dibeli',
      type: 'bar',
      barMaxWidth: 42,
      data: demographics.age_stats.map((a, i) => ({
        value: a.items,
        itemStyle: { color: i === 2 ? PALETTE.primary : PALETTE.primaryBar, borderRadius: [4, 4, 0, 0] },
      })),
    }],
  }, true);

  getChart('chart-demo-gender').setOption({
    tooltip: { ...TOOLTIP_THEME, trigger: 'item', formatter: (p) => `<b>${escapeHtml(p.name)}</b><br/>${fmtInt(p.value)} item dibeli (${p.percent}%)` },
    legend: { bottom: 4, icon: 'circle', itemWidth: 8, itemHeight: 8, textStyle: { color: PALETTE.muted, fontSize: 12 } },
    color: [PALETTE.primary, PALETTE.secondary],
    series: [{
      type: 'pie',
      radius: ['54%', '74%'],
      center: ['50%', '45%'],
      itemStyle: { borderColor: '#FFF', borderWidth: 2 },
      label: { show: true, formatter: '{d}%', fontSize: 12, fontWeight: 600, color: PALETTE.ink },
      data: demographics.gender_stats.map((g) => ({ name: g.gender, value: g.items })),
    }],
  }, true);
}

// ==========================================
// UPLOAD CSV, PROMPT BUILDER & SYNTAX HIGHLIGHT
// ==========================================
function updateAIPromptText() {
  const rows = document.getElementById('prompt-rows').value || 50;
  const cats = document.getElementById('prompt-cats').value.trim() || 'Elektronik, Fashion, Makanan & Minuman, Kecantikan';

  document.getElementById('ai-prompt-output').textContent =
`Tolong buatkan dataset e-commerce dalam format file CSV dengan header kolom PERSIS seperti berikut:
Nama Produk,Nama Toko,Lokasi Toko,Terjual,Jumlah Ulasan,Rating,Harga (IDR),Diskon (%),Produk URL

Ketentuan pembuatan data:
1. Buatkan sebanyak ${rows} baris data produk e-commerce Indonesia yang realistis.
2. Variasikan kategori produk mencakup: ${cats}.
3. Format setiap kolom:
   - 'Nama Produk': Judul barang yang realistis.
   - 'Nama Toko': Nama merchant / penjual.
   - 'Lokasi Toko': Nama kota di Indonesia (misal: Jakarta Selatan, Bandung, Surabaya, Medan).
   - 'Terjual': Format teks kuantitas (contoh: '1.5rb+ terjual', '850 terjual', atau '50 terjual').
   - 'Jumlah Ulasan': Format ulasan (contoh: '250 ulasan' atau '15 ulasan').
   - 'Rating': Angka desimal titik antara 3.8 sampai 5.0 (contoh: 4.8).
   - 'Harga (IDR)': Angka bulat Rupiah tanpa titik/Rp (contoh: 85000).
   - 'Diskon (%)': Angka persentase diskon 0 sampai 50 (contoh: 15.0).
   - 'Produk URL': Link dummy (contoh: https://www.tokopedia.com/toko/nama-produk).
4. PENTING: Tampilkan HANYA blok kode teks CSV mentah (raw CSV) tanpa teks pengantar atau penutup agar langsung bisa disimpan sebagai file .csv.`;
}

function renderHighlightedSparkCode() {
  const raw = document.getElementById('spark-code-raw').value;
  const lines = raw.split('\n').map((line) => {
    const escaped = escapeHtml(line);
    if (escaped.trim().startsWith('#')) {
      return `<span class="tok-cmt">${escaped}</span>`;
    }
    return escaped
      .replace(/(&quot;.*?&quot;)/g, '<span class="tok-str">$1</span>')
      .replace(/\b(from|import|print|True|False)\b/g, '<span class="tok-kw">$1</span>')
      .replace(/\b(\d+(?:\.\d+)?)\b/g, '<span class="tok-num">$1</span>');
  });
  document.getElementById('spark-code-highlighted').innerHTML = lines.join('\n');
}

async function handleCSVUpload(file) {
  const feedback = document.getElementById('upload-feedback');
  const gotoBtn = document.getElementById('btn-goto-overview');
  feedback.classList.remove('hidden', 'ok', 'err');
  feedback.textContent = `Memproses "${file.name}" (cleaning, kategorisasi, dan K-Means)...`;

  const formData = new FormData();
  formData.append('file', file);

  setLoading(true);
  try {
    const res = await fetch('/api/upload', { method: 'POST', body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Gagal memproses file CSV');

    feedback.classList.add('ok');
    feedback.textContent = data.message;
    gotoBtn.classList.remove('hidden');

    resetAllFilters(false);
    populateFilterOptions(data.meta);
    await fetchDashboard();
    showToast(`Dataset baru aktif: ${file.name}`);
  } catch (err) {
    feedback.classList.add('err');
    feedback.textContent = err.message;
    gotoBtn.classList.add('hidden');
    showToast(err.message, true);
  } finally {
    setLoading(false);
  }
}

// ==========================================
// EVENT BINDINGS & INIT
// ==========================================
function bindEvents() {
  document.querySelectorAll('.nav[data-page]').forEach((btn) => {
    btn.addEventListener('click', () => navigateTo(btn.dataset.page));
  });

  document.querySelectorAll('[data-goto]').forEach((btn) => {
    btn.addEventListener('click', () => navigateTo(btn.dataset.goto));
  });

  document.getElementById('btn-top-dataset').addEventListener('click', () => navigateTo('unggah'));
  document.getElementById('btn-goto-overview').addEventListener('click', () => navigateTo('ringkasan'));

  document.getElementById('btn-mobile-menu').addEventListener('click', openMobileSidebar);
  document.getElementById('sidebar-backdrop').addEventListener('click', closeMobileSidebar);

  // Unified Filter Controls
  document.getElementById('filter-category').addEventListener('change', (e) => setFilter('category', e.target.value));
  document.getElementById('filter-city').addEventListener('change', (e) => setFilter('city', e.target.value));
  document.getElementById('filter-price').addEventListener('change', (e) => setFilter('priceKey', e.target.value));
  document.getElementById('filter-rating').addEventListener('change', (e) => setFilter('min_rating', e.target.value));
  document.getElementById('global-search').addEventListener('input', (e) => {
    state.filters.search = e.target.value;
    clearTimeout(state.debounceTimer);
    state.debounceTimer = setTimeout(fetchDashboard, 250);
  });
  document.getElementById('btn-reset-filters').addEventListener('click', () => resetAllFilters(true));

  // Metric switches
  document.querySelectorAll('#cat-metric-toggle .seg-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#cat-metric-toggle .seg-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      state.catMetric = btn.dataset.metric;
      renderMarketOverview();
    });
  });

  document.querySelectorAll('#geo-metric-toggle .seg-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#geo-metric-toggle .seg-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      state.geoMetric = btn.dataset.metric;
      renderGeografiPage();
    });
  });

  // Produk sort & limit
  document.getElementById('product-sort').addEventListener('change', (e) => {
    state.filters.sort_by = e.target.value;
    fetchDashboard();
  });
  document.getElementById('product-limit').addEventListener('change', (e) => {
    state.filters.top_n = parseInt(e.target.value, 10);
    fetchDashboard();
  });

  // Upload Dropzone
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('csv-file-input');
  dropzone.addEventListener('click', () => fileInput.click());
  dropzone.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') fileInput.click(); });
  fileInput.addEventListener('change', () => {
    if (fileInput.files && fileInput.files[0]) {
      handleCSVUpload(fileInput.files[0]);
      fileInput.value = '';
    }
  });
  ['dragenter', 'dragover'].forEach((ev) => {
    dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
  });
  ['dragleave', 'drop'].forEach((ev) => {
    dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.remove('dragover'); });
  });
  dropzone.addEventListener('drop', (e) => {
    const file = e.dataTransfer.files && e.dataTransfer.files[0];
    if (file) handleCSVUpload(file);
  });

  // Reset dataset
  document.getElementById('btn-reset-dataset').addEventListener('click', async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/reset', { method: 'POST' });
      const data = await res.json();
      resetAllFilters(false);
      populateFilterOptions(data.meta);
      await fetchDashboard();
      document.getElementById('upload-feedback').classList.add('hidden');
      document.getElementById('btn-goto-overview').classList.add('hidden');
      showToast('Dataset dikembalikan ke katalog bawaan Tokopedia.');
    } catch (_) {
      showToast('Gagal mengembalikan dataset bawaan', true);
    } finally {
      setLoading(false);
    }
  });

  // Prompt Builder & Code Copy
  document.getElementById('prompt-rows').addEventListener('input', updateAIPromptText);
  document.getElementById('prompt-cats').addEventListener('input', updateAIPromptText);
  document.getElementById('btn-copy-prompt').addEventListener('click', async () => {
    await copyTextSafe(document.getElementById('ai-prompt-output').textContent);
    showToast('Prompt AI berhasil disalin.');
  });
  document.getElementById('btn-copy-spark').addEventListener('click', async () => {
    await copyTextSafe(document.getElementById('spark-code-raw').value);
    showToast('Kode PySpark berhasil disalin.');
  });

  window.addEventListener('resize', resizeCharts);
}

async function init() {
  bindEvents();
  updateAIPromptText();
  renderHighlightedSparkCode();
  try {
    const metaRes = await fetch('/api/meta');
    const meta = await metaRes.json();
    populateFilterOptions(meta);
    await fetchDashboard();
  } catch (_) {
    showToast('Gagal terhubung ke server FastAPI', true);
  }
}

document.addEventListener('DOMContentLoaded', init);
