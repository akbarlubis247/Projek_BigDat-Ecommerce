/* ==========================================================================
   Analitik Pasar — Intuitive Controller & Apache ECharts Visuals
   ========================================================================== */

const PALETTE = {
  emerald: '#0E6641',
  terracotta: '#C95B2B',
  prussian: '#1C4E6F',
  amber: '#B68523',
  slate: '#5B6360',
  sage: '#6E8F7B',
  clay: '#9E6B52',
  steel: '#4F6D85',
  ink: '#161A17',
  muted: '#7A807B',
  grid: '#ECEAE1',
};

const SERIES_COLORS = [
  PALETTE.emerald,
  PALETTE.prussian,
  PALETTE.terracotta,
  PALETTE.amber,
  PALETTE.slate,
  PALETTE.sage,
  PALETTE.clay,
  PALETTE.steel,
  '#8C7A5B',
  '#465950',
];

const PAGE_INFO = {
  ringkasan: {
    title: 'Ringkasan Pasar',
    subtitle: 'Gambaran performa penjualan, kategori paling laris, dan kelompok harga yang paling diminati.',
    showFilter: true,
  },
  produk: {
    title: 'Produk & Toko Terlaris',
    subtitle: 'Cari barang tertentu, bandingkan produk unggulan, dan lihat 10 toko paling berpengaruh.',
    showFilter: true,
  },
  waktu: {
    title: 'Waktu Belanja Puncak',
    subtitle: 'Mengetahui jam, hari, dan tanggal dengan lonjakan transaksi tertinggi untuk persiapan kapasitas server.',
    showFilter: false,
  },
  geografi: {
    title: 'Sebaran Wilayah Penjualan',
    subtitle: 'Pemetaan kota-kota di Indonesia yang menjadi pusat volume penjualan dan merchant terbanyak.',
    showFilter: true,
  },
  klaster: {
    title: 'Segmentasi Produk (Machine Learning)',
    subtitle: 'Pengelompokan otomatis produk ke dalam 4 segmen bisnis menggunakan algoritma K-Means Clustering.',
    showFilter: true,
  },
  unggah: {
    title: 'Unggah Data CSV & Generator Prompt AI',
    subtitle: 'Ganti dataset dengan file CSV baru milik Anda atau buat contoh dataset instan menggunakan bantuan AI.',
    showFilter: false,
  },
  arsitektur: {
    title: 'Arsitektur Big Data (Lambda)',
    subtitle: 'Penjelasan alur pemrosesan data dari Kafka, MongoDB, Apache Spark, hingga dashboard web.',
    showFilter: false,
  },
};

const PRICE_LABELS = {
  ALL: 'Semua Harga',
  '0-100000': '< Rp 100rb',
  '100000-500000': 'Rp 100rb – 500rb',
  '500000-2000000': 'Rp 500rb – 2jt',
  '2000000-': '> Rp 2jt',
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
};

// ==========================================
// FORMATTERS
// ==========================================
function fmtInt(n) {
  return new Intl.NumberFormat('id-ID').format(Math.round(Number(n) || 0));
}

function fmtRupiahShort(val) {
  const n = Number(val) || 0;
  if (n >= 1e12) return `Rp ${(n / 1e12).toFixed(2).replace('.', ',')} T`;
  if (n >= 1e9) return `Rp ${(n / 1e9).toFixed(2).replace('.', ',')} M`;
  if (n >= 1e6) return `Rp ${(n / 1e6).toFixed(1).replace('.', ',')} Jt`;
  if (n >= 1e3) return `Rp ${(n / 1e3).toFixed(0)} rb`;
  return `Rp ${fmtInt(n)}`;
}

function fmtRupiahFull(val) {
  return `Rp ${fmtInt(val)}`;
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

function truncate(str, maxLen = 38) {
  const s = String(str || '');
  return s.length > maxLen ? s.slice(0, maxLen - 1) + '…' : s;
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
// UI FEEDBACK (LOADER & TOAST)
// ==========================================
function setLoading(loading) {
  const el = document.getElementById('top-loader');
  if (loading) {
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

// ==========================================
// ECHARTS HELPERS
// ==========================================
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

const TOOLTIP_STYLE = {
  backgroundColor: '#161A17',
  borderWidth: 0,
  padding: [10, 14],
  textStyle: { color: '#F5F4EE', fontFamily: 'Plus Jakarta Sans, sans-serif', fontSize: 12 },
};

// ==========================================
// NAVIGATION
// ==========================================
function navigateTo(pageKey) {
  const info = PAGE_INFO[pageKey] || PAGE_INFO.ringkasan;
  state.activePage = pageKey;

  document.getElementById('page-title').textContent = info.title;
  document.getElementById('page-subtitle').textContent = info.subtitle;
  document.getElementById('filter-bar').classList.toggle('hidden', !info.showFilter);

  document.querySelectorAll('.nav-item').forEach((btn) => {
    const active = btn.dataset.page === pageKey;
    btn.classList.toggle('active', active);
    btn.setAttribute('aria-selected', String(active));
  });

  document.querySelectorAll('.page-view').forEach((view) => {
    view.classList.toggle('active', view.id === `page-${pageKey}`);
  });

  // Close mobile sidebar if open
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
// DATA FETCHING & FILTER UI
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
    if (!res.ok) throw new Error('Gagal memuat data dashboard.');
    state.data = await res.json();

    syncSourceUI(state.data.meta);
    renderFilterStatus();
    renderCurrentPage();
  } catch (err) {
    showToast(err.message || 'Gagal terhubung ke server', true);
  } finally {
    setLoading(false);
  }
}

function populateFilterDropdowns(meta) {
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
  document.getElementById('sidebar-source-dot').classList.toggle('custom', isCustom);
  document.getElementById('top-source-dot').classList.toggle('custom', isCustom);

  document.getElementById('sidebar-source-title').textContent = isCustom ? 'Data Kustom Aktif' : 'Data Bawaan Aktif';
  document.getElementById('sidebar-source-sub').textContent = isCustom
    ? `${meta.filename} · ${fmtInt(meta.total_rows)} produk`
    : `Tokopedia · ${fmtInt(meta.total_rows)} produk`;

  document.getElementById('top-source-label').textContent = isCustom
    ? `${truncate(meta.filename, 20)} (${fmtInt(meta.total_rows)} produk)`
    : `Katalog Tokopedia (${fmtInt(meta.total_rows)} produk)`;

  document.getElementById('upload-current-status').innerHTML = isCustom
    ? `Saat ini dashboard menampilkan data unggahan Anda: <strong>${escapeHtml(meta.filename)}</strong> (${fmtInt(meta.total_rows)} produk, ${fmtInt(meta.total_merchants)} toko).`
    : `Saat ini dashboard menampilkan <strong>Dataset Bawaan Tokopedia</strong> (${fmtInt(meta.total_rows)} produk, ${fmtInt(meta.total_merchants)} toko).`;

  document.getElementById('btn-reset-dataset').classList.toggle('hidden', !isCustom);
}

function renderFilterStatus() {
  if (!state.data) return;
  const k = state.data.kpis;
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

  document.getElementById('filter-status-text').innerHTML =
    `Menampilkan <strong>${fmtInt(k.total_products)}</strong> dari ${fmtInt(k.total_catalog_raw)} produk`;
  document.getElementById('btn-reset-filters').classList.toggle('hidden', chips.length === 0);

  const chipRow = document.getElementById('active-filter-chips');
  if (chips.length === 0) {
    chipRow.classList.add('hidden');
    chipRow.innerHTML = '';
  } else {
    chipRow.classList.remove('hidden');
    chipRow.innerHTML = '';
    chips.forEach((c) => {
      const span = document.createElement('span');
      span.className = 'filter-chip';
      span.innerHTML = `${escapeHtml(c.label)} <button type="button" aria-label="Hapus filter">&times;</button>`;
      span.querySelector('button').addEventListener('click', c.clear);
      chipRow.appendChild(span);
    });
  }
}

function setFilter(key, value) {
  if (key === 'category') {
    state.filters.category = value;
    document.getElementById('filter-category').value = value;
  } else if (key === 'city') {
    state.filters.city = value;
    document.getElementById('filter-city').value = value;
  } else if (key === 'priceKey') {
    state.filters.priceKey = value;
    document.getElementById('filter-price').value = value;
    if (value === 'ALL') {
      state.filters.min_price = '';
      state.filters.max_price = '';
    } else {
      const [mn, mx] = value.split('-');
      state.filters.min_price = mn;
      state.filters.max_price = mx;
    }
  } else if (key === 'min_rating') {
    state.filters.min_rating = Number(value);
    document.getElementById('filter-rating').value = String(value);
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
  document.getElementById('product-search').value = '';

  if (shouldFetch) fetchDashboard();
}

// ==========================================
// PAGE RENDERERS
// ==========================================
function renderCurrentPage() {
  if (!state.data) return;
  switch (state.activePage) {
    case 'ringkasan': renderPageRingkasan(); break;
    case 'produk': renderPageProduk(); break;
    case 'waktu': renderPageWaktu(); break;
    case 'geografi': renderPageGeografi(); break;
    case 'klaster': renderPageKlaster(); break;
    default: break;
  }
  requestAnimationFrame(resizeCharts);
}

// ---------- PAGE 1: RINGKASAN PASAR ----------
function renderPageRingkasan() {
  const { kpis, categories, price_tiers } = state.data;

  // KPIs
  document.getElementById('kpi-products').textContent = fmtInt(kpis.total_products);
  document.getElementById('kpi-products-sub').textContent = `Dari ${fmtInt(kpis.total_merchants)} toko di ${fmtInt(kpis.total_cities)} kota`;

  document.getElementById('kpi-volume').textContent = fmtUnitShort(kpis.total_volume_sold);
  document.getElementById('kpi-volume-sub').textContent = `Total ${fmtInt(kpis.total_volume_sold)} unit terjual`;

  document.getElementById('kpi-gmv').textContent = fmtRupiahShort(kpis.total_gmv);
  document.getElementById('kpi-gmv-sub').textContent = `Median harga ${fmtRupiahFull(kpis.median_price)}`;

  document.getElementById('kpi-rating').textContent = `${kpis.avg_rating.toFixed(2)} / 5`;
  document.getElementById('kpi-discount-sub').textContent = `Rata-rata diskon ${kpis.avg_discount.toFixed(1)}%`;

  // Plain-Indonesian Takeaway
  const takeaway = document.getElementById('ringkasan-takeaway');
  if (!categories.length) {
    takeaway.innerHTML = 'Tidak ada produk yang cocok dengan filter yang Anda pilih. Silakan klik <strong>Hapus Filter</strong> di atas untuk melihat seluruh data.';
  } else {
    const topCat = categories[0];
    const topTier = [...price_tiers].sort((a, b) => b.total_terjual - a.total_terjual)[0];
    takeaway.innerHTML =
      `Kesimpulan utama: Kategori <strong>${escapeHtml(topCat.kategori)}</strong> memimpin penjualan dengan <strong>${fmtUnitShort(topCat.total_terjual)} unit</strong> terjual (${fmtRupiahShort(topCat.total_gmv)}), sementara rentang harga paling diminati pembeli berada di <strong>${escapeHtml(topTier ? topTier.price_tier : '-')}</strong>.`;
  }

  // Category Horizontal Bar (Interactive Click-to-Filter!)
  const metric = state.catMetric;
  const sorted = [...categories].sort((a, b) => a[metric] - b[metric]);
  const chCat = getChart('chart-category-bar');
  chCat.setOption({
    tooltip: {
      ...TOOLTIP_STYLE,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (p) => {
        const c = sorted[p[0].dataIndex];
        return `
          <div style="font-weight:700;margin-bottom:5px">${escapeHtml(c.kategori)}</div>
          <div>Terjual: <b style="font-family:JetBrains Mono">${fmtInt(c.total_terjual)} unit</b></div>
          <div>Estimasi Omzet: <b style="font-family:JetBrains Mono">${fmtRupiahShort(c.total_gmv)}</b></div>
          <div>Jumlah Produk: <b style="font-family:JetBrains Mono">${fmtInt(c.total_produk)}</b></div>
          <div style="color:#A6B5AC;margin-top:4px;font-size:11px">Klik batang untuk memfilter kategori ini</div>
        `;
      },
    },
    grid: { top: 8, left: 10, right: 68, bottom: 12, containLabel: true },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: PALETTE.grid } },
      axisLabel: {
        color: PALETTE.muted,
        fontFamily: 'JetBrains Mono',
        fontSize: 11,
        formatter: (v) => (metric === 'total_gmv' ? fmtRupiahShort(v) : fmtUnitShort(v)),
      },
    },
    yAxis: {
      type: 'category',
      data: sorted.map((c) => c.kategori),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: PALETTE.ink, fontSize: 12, fontWeight: 500 },
    },
    series: [{
      type: 'bar',
      barMaxWidth: 22,
      cursor: 'pointer',
      label: {
        show: true,
        position: 'right',
        distance: 6,
        color: PALETTE.muted,
        fontFamily: 'JetBrains Mono',
        fontSize: 10.5,
        formatter: (p) => (metric === 'total_gmv' ? fmtRupiahShort(p.value) : fmtUnitShort(p.value)),
      },
      data: sorted.map((c, i) => ({
        value: c[metric],
        itemStyle: {
          color: i === sorted.length - 1 ? PALETTE.emerald : i >= sorted.length - 3 ? '#2B7A56' : '#8DB39F',
          borderRadius: [0, 4, 4, 0],
        },
      })),
    }],
  }, true);

  chCat.off('click');
  chCat.on('click', (params) => {
    const clicked = sorted[params.dataIndex];
    if (clicked) {
      const next = state.filters.category === clicked.kategori ? 'ALL' : clicked.kategori;
      setFilter('category', next);
    }
  });

  // Category Donut
  const chDonut = getChart('chart-category-donut');
  chDonut.setOption({
    tooltip: {
      ...TOOLTIP_STYLE,
      trigger: 'item',
      formatter: (p) => `<b>${escapeHtml(p.name)}</b><br/>${fmtInt(p.value)} produk (${p.percent}%)`,
    },
    legend: {
      type: 'scroll',
      bottom: 0,
      icon: 'circle',
      itemWidth: 8,
      itemHeight: 8,
      pageIconColor: PALETTE.emerald,
      textStyle: { color: PALETTE.muted, fontSize: 11 },
    },
    color: SERIES_COLORS,
    series: [{
      type: 'pie',
      radius: ['52%', '74%'],
      center: ['50%', '43%'],
      itemStyle: { borderColor: '#FFF', borderWidth: 2 },
      label: { show: false },
      data: categories.map((c) => ({ name: c.kategori, value: c.total_produk })),
    }],
    graphic: [
      { type: 'text', left: 'center', top: '38%', style: { text: fmtInt(kpis.total_products), font: '700 21px JetBrains Mono, monospace', fill: PALETTE.ink } },
      { type: 'text', left: 'center', top: '45.5%', style: { text: 'PRODUK', font: '600 10px Plus Jakarta Sans, sans-serif', fill: PALETTE.muted } },
    ],
  }, true);

  // Price Tier Combo Chart
  const chTier = getChart('chart-price-tier');
  chTier.setOption({
    tooltip: {
      ...TOOLTIP_STYLE,
      trigger: 'axis',
      formatter: (p) => {
        const t = price_tiers[p[0].dataIndex];
        return `
          <div style="font-weight:700;margin-bottom:5px">${escapeHtml(t.price_tier)}</div>
          <div>Unit Terjual: <b style="font-family:JetBrains Mono">${fmtInt(t.total_terjual)}</b></div>
          <div>Estimasi Omzet: <b style="font-family:JetBrains Mono">${fmtRupiahShort(t.total_gmv)}</b></div>
          <div>Jumlah Produk: <b style="font-family:JetBrains Mono">${fmtInt(t.total_produk)}</b></div>
        `;
      },
    },
    legend: { top: 0, right: 10, textStyle: { color: PALETTE.muted, fontSize: 12 } },
    grid: { top: 36, left: 12, right: 14, bottom: 14, containLabel: true },
    xAxis: {
      type: 'category',
      data: price_tiers.map((t) => t.short_label),
      axisLine: { lineStyle: { color: '#CCC8B8' } },
      axisTick: { show: false },
      axisLabel: { color: PALETTE.ink, fontSize: 12, fontWeight: 500 },
    },
    yAxis: [
      {
        type: 'value',
        name: 'Unit Terjual',
        nameTextStyle: { color: PALETTE.muted, fontSize: 11 },
        splitLine: { lineStyle: { color: PALETTE.grid } },
        axisLabel: { color: PALETTE.muted, fontFamily: 'JetBrains Mono', fontSize: 11, formatter: fmtUnitShort },
      },
      {
        type: 'value',
        name: 'Estimasi Omzet',
        nameTextStyle: { color: PALETTE.terracotta, fontSize: 11 },
        splitLine: { show: false },
        axisLabel: { color: PALETTE.terracotta, fontFamily: 'JetBrains Mono', fontSize: 11, formatter: fmtRupiahShort },
      },
    ],
    series: [
      {
        name: 'Unit Terjual',
        type: 'bar',
        barMaxWidth: 48,
        itemStyle: { color: PALETTE.emerald, borderRadius: [4, 4, 0, 0] },
        data: price_tiers.map((t) => t.total_terjual),
      },
      {
        name: 'Estimasi Omzet (GMV)',
        type: 'line',
        yAxisIndex: 1,
        smooth: 0.25,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: { color: PALETTE.terracotta, width: 2.5 },
        itemStyle: { color: PALETTE.terracotta, borderColor: '#FFF', borderWidth: 2 },
        data: price_tiers.map((t) => t.total_gmv),
      },
    ],
  }, true);
}

// ---------- PAGE 2: PRODUK & TOKO TERLARIS ----------
function renderPageProduk() {
  const { top_products, top_shops, top_products_total_match } = state.data;
  const sortField = state.filters.sort_by === 'estimasi_gmv' ? 'gmv' : state.filters.sort_by === 'Harga (IDR)' ? 'harga' : state.filters.sort_by === 'Rating' ? 'rating' : 'terjual';

  document.getElementById('product-match-count').textContent = state.filters.search.trim()
    ? `Ditemukan ${fmtInt(top_products_total_match)} produk cocok dengan "${state.filters.search.trim()}"`
    : `Menampilkan ${top_products.length} produk teratas dari ${fmtInt(top_products_total_match)} produk aktif`;

  const chartSlice = [...top_products].slice(0, 10).reverse();
  const chTop = getChart('chart-top-products');
  chTop.setOption({
    tooltip: {
      ...TOOLTIP_STYLE,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (p) => {
        const item = chartSlice[p[0].dataIndex];
        return `
          <div style="font-weight:700;max-width:290px;white-space:normal;margin-bottom:5px">${escapeHtml(item.nama_produk)}</div>
          <div>Toko: ${escapeHtml(item.nama_toko)} (${escapeHtml(item.lokasi)})</div>
          <div>Harga: <b style="font-family:JetBrains Mono">${fmtRupiahFull(item.harga)}</b></div>
          <div>Terjual: <b style="font-family:JetBrains Mono">${fmtInt(item.terjual)} unit</b></div>
          <div>Omzet: <b style="font-family:JetBrains Mono">${fmtRupiahShort(item.gmv)}</b></div>
        `;
      },
    },
    grid: { top: 8, left: 10, right: 64, bottom: 14, containLabel: true },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: PALETTE.grid } },
      axisLabel: {
        color: PALETTE.muted,
        fontFamily: 'JetBrains Mono',
        fontSize: 11,
        formatter: (v) => (sortField === 'gmv' || sortField === 'harga' ? fmtRupiahShort(v) : fmtUnitShort(v)),
      },
    },
    yAxis: {
      type: 'category',
      data: chartSlice.map((p) => truncate(p.nama_produk, 40)),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: PALETTE.ink, fontSize: 11.5 },
    },
    series: [{
      type: 'bar',
      barMaxWidth: 20,
      itemStyle: { color: PALETTE.prussian, borderRadius: [0, 4, 4, 0] },
      label: {
        show: true,
        position: 'right',
        distance: 6,
        color: PALETTE.muted,
        fontFamily: 'JetBrains Mono',
        fontSize: 10.5,
        formatter: (p) => (sortField === 'gmv' || sortField === 'harga' ? fmtRupiahShort(p.value) : sortField === 'rating' ? Number(p.value).toFixed(1) : fmtUnitShort(p.value)),
      },
      data: chartSlice.map((p) => p[sortField]),
    }],
  }, true);

  const tbody = document.getElementById('tbody-top-products');
  tbody.innerHTML = !top_products.length
    ? `<tr><td colspan="9" style="text-align:center;color:var(--ink-muted);padding:24px">Tidak ada produk yang cocok dengan pencarian atau filter.</td></tr>`
    : top_products.map((p, idx) => `
      <tr>
        <td class="col-rank">${idx + 1}</td>
        <td>
          <a class="prod-link" href="${escapeHtml(p.url)}" target="_blank" rel="noopener" title="${escapeHtml(p.nama_produk)}">${escapeHtml(p.nama_produk)}</a>
          <div class="prod-sub">${escapeHtml(p.nama_toko)}</div>
        </td>
        <td><span class="cat-tag">${escapeHtml(p.kategori)}</span></td>
        <td>${escapeHtml(p.lokasi)}</td>
        <td class="num">${fmtRupiahFull(p.harga)}</td>
        <td class="num">${p.diskon > 0 ? `${p.diskon}%` : '—'}</td>
        <td class="num"><span class="rating-pill">${p.rating.toFixed(1)}</span></td>
        <td class="num"><strong>${fmtInt(p.terjual)}</strong></td>
        <td class="num">${fmtRupiahShort(p.gmv)}</td>
      </tr>
    `).join('');

  const tbodyShops = document.getElementById('tbody-top-shops');
  tbodyShops.innerHTML = !top_shops.length
    ? `<tr><td colspan="7" style="text-align:center;color:var(--ink-muted);padding:24px">Belum ada data toko.</td></tr>`
    : top_shops.map((s, idx) => `
      <tr>
        <td class="col-rank">${idx + 1}</td>
        <td><strong>${escapeHtml(s.nama_toko)}</strong></td>
        <td>${escapeHtml(s.lokasi)}</td>
        <td class="num">${fmtInt(s.total_produk)}</td>
        <td class="num"><strong>${fmtInt(s.total_terjual)}</strong></td>
        <td class="num">${fmtRupiahShort(s.total_gmv)}</td>
        <td class="num"><span class="rating-pill">${s.avg_rating.toFixed(2)}</span></td>
      </tr>
    `).join('');
}

// ---------- PAGE 3: WAKTU BELANJA PUNCAK ----------
function renderPageWaktu() {
  const tt = state.data.time_trends;
  document.getElementById('tx-total-badge').textContent = `${fmtInt(tt.total_transactions)} catatan transaksi`;

  document.getElementById('waktu-takeaway').innerHTML =
    `Kesimpulan utama: Transaksi paling ramai terjadi pada jam <strong>${String(tt.peak_hour).padStart(2, '0')}:00 WIB</strong> dan memuncak pada hari <strong>${escapeHtml(tt.peak_day)}</strong>. Lonjakan harian tertinggi tercatat pada tanggal <strong>${escapeHtml(tt.peak_date)}</strong> (${fmtInt(tt.peak_date_count)} item).`;

  document.getElementById('waktu-kpis').innerHTML = `
    <article class="kpi-card kpi-highlight">
      <div class="kpi-label">Jam Belanja Paling Ramai</div>
      <div class="kpi-value mono">${String(tt.peak_hour).padStart(2, '0')}:00 WIB</div>
      <div class="kpi-hint">${fmtInt(tt.peak_hour_count)} item masuk keranjang</div>
    </article>
    <article class="kpi-card">
      <div class="kpi-label">Hari Paling Aktif</div>
      <div class="kpi-value">${escapeHtml(tt.peak_day)}</div>
      <div class="kpi-hint">Waktu ideal menjalankan promo &amp; flash sale</div>
    </article>
    <article class="kpi-card">
      <div class="kpi-label">Tanggal Lonjakan Tertinggi</div>
      <div class="kpi-value mono">${escapeHtml(tt.peak_date)}</div>
      <div class="kpi-hint">Tercatat ${fmtInt(tt.peak_date_count)} item dalam satu hari</div>
    </article>
  `;

  const chDaily = getChart('chart-daily-trend');
  chDaily.setOption({
    tooltip: { ...TOOLTIP_STYLE, trigger: 'axis' },
    grid: { top: 24, left: 14, right: 20, bottom: 52, containLabel: true },
    xAxis: {
      type: 'category',
      data: tt.daily.map((d) => d.date),
      axisLine: { lineStyle: { color: '#CCC8B8' } },
      axisLabel: { color: PALETTE.muted, fontFamily: 'JetBrains Mono', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: PALETTE.grid } },
      axisLabel: { color: PALETTE.muted, fontFamily: 'JetBrains Mono', fontSize: 11 },
    },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', height: 20, bottom: 8, borderColor: '#E4E1D6', fillerColor: 'rgba(14, 102, 65, 0.14)', handleStyle: { color: PALETTE.emerald } },
    ],
    series: [{
      name: 'Item Dibeli',
      type: 'line',
      smooth: 0.2,
      showSymbol: false,
      lineStyle: { color: PALETTE.emerald, width: 2 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(14, 102, 65, 0.2)' },
          { offset: 1, color: 'rgba(14, 102, 65, 0.01)' },
        ]),
      },
      markPoint: {
        symbolSize: 42,
        itemStyle: { color: PALETTE.terracotta },
        label: { fontSize: 10, fontFamily: 'JetBrains Mono' },
        data: [{ type: 'max', name: 'Puncak' }],
      },
      data: tt.daily.map((d) => d.count),
    }],
  }, true);

  const maxH = Math.max(...tt.hourly.map((h) => h.count), 1);
  getChart('chart-hourly').setOption({
    tooltip: { ...TOOLTIP_STYLE, trigger: 'axis', formatter: (p) => `Jam <b>${p[0].name}:00 WIB</b><br/>Volume: <b>${fmtInt(p[0].value)} item</b>` },
    grid: { top: 16, left: 10, right: 14, bottom: 14, containLabel: true },
    xAxis: { type: 'category', data: tt.hourly.map((h) => String(h.hour).padStart(2, '0')), axisLine: { lineStyle: { color: '#CCC8B8' } }, axisLabel: { color: PALETTE.ink, fontFamily: 'JetBrains Mono', fontSize: 11 } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: PALETTE.grid } }, axisLabel: { color: PALETTE.muted, fontFamily: 'JetBrains Mono', fontSize: 11 } },
    series: [{
      type: 'bar',
      barMaxWidth: 26,
      data: tt.hourly.map((h) => ({
        value: h.count,
        itemStyle: { color: h.count >= maxH * 0.82 ? PALETTE.terracotta : '#9BB5A6', borderRadius: [4, 4, 0, 0] },
      })),
    }],
  }, true);

  const maxDow = Math.max(...tt.day_of_week.map((d) => d.count), 1);
  getChart('chart-dow').setOption({
    tooltip: { ...TOOLTIP_STYLE, trigger: 'axis', formatter: (p) => `Hari <b>${escapeHtml(p[0].name)}</b><br/>Volume: <b>${fmtInt(p[0].value)} item</b>` },
    grid: { top: 16, left: 10, right: 14, bottom: 14, containLabel: true },
    xAxis: { type: 'category', data: tt.day_of_week.map((d) => d.day_id), axisLine: { lineStyle: { color: '#CCC8B8' } }, axisLabel: { color: PALETTE.ink, fontSize: 12 } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: PALETTE.grid } }, axisLabel: { color: PALETTE.muted, fontFamily: 'JetBrains Mono', fontSize: 11 } },
    series: [{
      type: 'bar',
      barMaxWidth: 38,
      data: tt.day_of_week.map((d) => ({
        value: d.count,
        itemStyle: { color: d.count >= maxDow * 0.96 ? PALETTE.emerald : '#7DA2B8', borderRadius: [4, 4, 0, 0] },
      })),
    }],
  }, true);
}

// ---------- PAGE 4: SEBARAN WILAYAH ----------
function renderPageGeografi() {
  const { locations, geo_summary, kpis } = state.data;
  const metric = state.geoMetric;
  const sorted = [...locations].sort((a, b) => a[metric] - b[metric]);

  document.getElementById('geo-takeaway').innerHTML = locations.length
    ? `Kesimpulan utama: Wilayah <strong>Jabodetabek</strong> menyumbang <strong>${geo_summary.jabodetabek_share_pct}%</strong> dari total penjualan, dengan <strong>${escapeHtml(geo_summary.top_city)}</strong> sebagai kota penyumbang volume terbesar (${fmtUnitShort(geo_summary.top_city_volume)} unit).`
    : 'Tidak ada data wilayah untuk filter yang dipilih.';

  document.getElementById('geo-kpis').innerHTML = `
    <article class="kpi-card kpi-highlight">
      <div class="kpi-label">Porsi Wilayah Jabodetabek</div>
      <div class="kpi-value mono">${geo_summary.jabodetabek_share_pct}%</div>
      <div class="kpi-hint">Jakarta, Bogor, Depok, Tangerang &amp; Bekasi</div>
    </article>
    <article class="kpi-card">
      <div class="kpi-label">Wilayah Non-Jabodetabek</div>
      <div class="kpi-value mono">${geo_summary.non_jabo_share_pct || 0}%</div>
      <div class="kpi-hint">Surabaya, Bandung, Semarang, Medan, dll.</div>
    </article>
    <article class="kpi-card">
      <div class="kpi-label">Kota Penjualan #1</div>
      <div class="kpi-value">${escapeHtml(geo_summary.top_city)}</div>
      <div class="kpi-hint">Dari total ${fmtInt(kpis.total_cities)} kota aktif</div>
    </article>
  `;

  const chGeo = getChart('chart-geo-bar');
  chGeo.setOption({
    tooltip: {
      ...TOOLTIP_STYLE,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (p) => {
        const l = sorted[p[0].dataIndex];
        return `
          <div style="font-weight:700;margin-bottom:5px">${escapeHtml(l.lokasi)}</div>
          <div>Terjual: <b style="font-family:JetBrains Mono">${fmtInt(l.total_terjual)} unit</b></div>
          <div>Omzet: <b style="font-family:JetBrains Mono">${fmtRupiahShort(l.total_gmv)}</b></div>
          <div>Produk Aktif: <b style="font-family:JetBrains Mono">${fmtInt(l.total_produk)}</b></div>
          <div style="color:#A6B5AC;margin-top:4px;font-size:11px">Klik batang untuk memfilter kota ini</div>
        `;
      },
    },
    grid: { top: 8, left: 10, right: 66, bottom: 14, containLabel: true },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: PALETTE.grid } },
      axisLabel: { color: PALETTE.muted, fontFamily: 'JetBrains Mono', fontSize: 11, formatter: (v) => (metric === 'total_gmv' ? fmtRupiahShort(v) : fmtUnitShort(v)) },
    },
    yAxis: { type: 'category', data: sorted.map((l) => l.lokasi), axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: PALETTE.ink, fontSize: 12 } },
    series: [{
      type: 'bar',
      barMaxWidth: 20,
      cursor: 'pointer',
      label: {
        show: true,
        position: 'right',
        distance: 6,
        color: PALETTE.muted,
        fontFamily: 'JetBrains Mono',
        fontSize: 10.5,
        formatter: (p) => (metric === 'total_gmv' ? fmtRupiahShort(p.value) : fmtUnitShort(p.value)),
      },
      data: sorted.map((l, i) => ({
        value: l[metric],
        itemStyle: { color: i >= sorted.length - 3 ? PALETTE.emerald : '#84AA96', borderRadius: [0, 4, 4, 0] },
      })),
    }],
  }, true);

  chGeo.off('click');
  chGeo.on('click', (params) => {
    const clicked = sorted[params.dataIndex];
    if (clicked) {
      const next = state.filters.city === clicked.lokasi ? 'ALL' : clicked.lokasi;
      setFilter('city', next);
    }
  });

  const maxVol = Math.max(...locations.map((l) => l.total_terjual), 1);
  getChart('chart-geo-bubble').setOption({
    tooltip: {
      ...TOOLTIP_STYLE,
      formatter: (p) => {
        const d = p.data.raw;
        return `<b>${escapeHtml(d.lokasi)}</b><br/>Produk: ${fmtInt(d.total_produk)}<br/>Rating: ${d.avg_rating.toFixed(2)}<br/>Terjual: ${fmtInt(d.total_terjual)} unit`;
      },
    },
    grid: { top: 24, left: 14, right: 24, bottom: 26, containLabel: true },
    xAxis: { type: 'value', name: 'Jumlah Produk', nameLocation: 'middle', nameGap: 26, nameTextStyle: { color: PALETTE.muted, fontSize: 11 }, splitLine: { lineStyle: { color: PALETTE.grid } }, axisLabel: { color: PALETTE.muted, fontFamily: 'JetBrains Mono', fontSize: 11 } },
    yAxis: { type: 'value', name: 'Rating', scale: true, nameTextStyle: { color: PALETTE.muted, fontSize: 11 }, splitLine: { lineStyle: { color: PALETTE.grid } }, axisLabel: { color: PALETTE.muted, fontFamily: 'JetBrains Mono', fontSize: 11 } },
    series: [{
      type: 'scatter',
      symbolSize: (val) => Math.max(12, Math.sqrt(val[2] / maxVol) * 50),
      label: { show: true, position: 'top', formatter: (p) => (p.dataIndex < 5 ? p.data.raw.lokasi : ''), fontSize: 10.5, color: PALETTE.ink, fontWeight: 600 },
      data: locations.map((l, idx) => ({
        value: [l.total_produk, l.avg_rating, l.total_terjual],
        raw: l,
        itemStyle: { color: SERIES_COLORS[idx % SERIES_COLORS.length], opacity: 0.82, borderColor: '#FFF', borderWidth: 1.5 },
      })),
    }],
  }, true);
}

// ---------- PAGE 5: SEGMENTASI PRODUK (K-MEANS) ----------
function renderPageKlaster() {
  const { clusters, demographics } = state.data;
  const { summary, scatter } = clusters;

  const takeaway = document.getElementById('klaster-takeaway');
  if (!summary.length) {
    takeaway.innerHTML = 'Tidak ada data segmen K-Means untuk filter yang dipilih.';
  } else {
    const biggest = summary[0];
    takeaway.innerHTML =
      `Kesimpulan utama: Algoritma K-Means membagi katalog menjadi <strong>${summary.length} segmen</strong>. Segmen terbesar adalah <strong>${escapeHtml(biggest.cluster_label)}</strong> (${biggest.share_pct}% atau ${fmtInt(biggest.jumlah_produk)} produk) dengan rata-rata harga ${fmtRupiahFull(biggest.rata_harga)}.`;
  }

  const names = summary.map((c) => c.cluster_label);
  const grouped = {};
  names.forEach((n) => (grouped[n] = []));
  scatter.forEach((pt) => {
    if (!grouped[pt.cluster]) grouped[pt.cluster] = [];
    grouped[pt.cluster].push(pt);
  });

  getChart('chart-cluster-scatter').setOption({
    tooltip: {
      ...TOOLTIP_STYLE,
      formatter: (p) => {
        const d = p.data.raw;
        return `
          <div style="font-weight:700;max-width:260px;white-space:normal;margin-bottom:4px">${escapeHtml(d.nama)}</div>
          <div style="color:#A6B5AC;margin-bottom:4px">${escapeHtml(d.cluster)}</div>
          <div>Harga: <b style="font-family:JetBrains Mono">${fmtRupiahFull(d.harga)}</b></div>
          <div>Terjual: <b style="font-family:JetBrains Mono">${fmtInt(d.terjual)} unit</b> · Rating <b>${d.rating}</b></div>
        `;
      },
    },
    legend: { type: 'scroll', bottom: 0, icon: 'circle', itemWidth: 9, itemHeight: 9, pageIconColor: PALETTE.emerald, textStyle: { color: PALETTE.muted, fontSize: 11 } },
    grid: { top: 16, left: 16, right: 18, bottom: 54, containLabel: true },
    xAxis: { type: 'log', name: 'Harga Produk (IDR)', nameLocation: 'middle', nameGap: 26, nameTextStyle: { color: PALETTE.muted, fontSize: 11 }, splitLine: { lineStyle: { color: PALETTE.grid } }, axisLabel: { color: PALETTE.muted, fontFamily: 'JetBrains Mono', fontSize: 10.5, formatter: fmtRupiahShort } },
    yAxis: { type: 'log', name: 'Unit Terjual', nameTextStyle: { color: PALETTE.muted, fontSize: 11 }, splitLine: { lineStyle: { color: PALETTE.grid } }, axisLabel: { color: PALETTE.muted, fontFamily: 'JetBrains Mono', fontSize: 10.5, formatter: fmtUnitShort } },
    color: [PALETTE.prussian, PALETTE.slate, PALETTE.terracotta, PALETTE.emerald],
    series: names.map((name) => ({
      name,
      type: 'scatter',
      symbolSize: 7,
      itemStyle: { opacity: 0.72 },
      data: (grouped[name] || []).map((pt) => ({ value: [pt.harga, pt.terjual], raw: pt })),
    })),
  }, true);

  getChart('chart-cluster-donut').setOption({
    tooltip: { ...TOOLTIP_STYLE, trigger: 'item', formatter: (p) => `<b>${escapeHtml(p.name)}</b><br/>${fmtInt(p.value)} produk (${p.percent}%)` },
    legend: { type: 'scroll', bottom: 0, icon: 'circle', itemWidth: 8, itemHeight: 8, pageIconColor: PALETTE.emerald, textStyle: { color: PALETTE.muted, fontSize: 11 } },
    color: [PALETTE.prussian, PALETTE.slate, PALETTE.terracotta, PALETTE.emerald],
    series: [{ type: 'pie', radius: ['52%', '74%'], center: ['50%', '43%'], itemStyle: { borderColor: '#FFF', borderWidth: 2 }, label: { show: false }, data: summary.map((c) => ({ name: c.cluster_label, value: c.jumlah_produk })) }],
  }, true);

  const tbody = document.getElementById('tbody-clusters');
  tbody.innerHTML = !summary.length
    ? `<tr><td colspan="8" style="text-align:center;color:var(--ink-muted);padding:24px">Belum ada data segmen.</td></tr>`
    : summary.map((c) => `
      <tr>
        <td><strong>${escapeHtml(c.cluster_label)}</strong></td>
        <td class="num">${fmtInt(c.jumlah_produk)}</td>
        <td class="num">${c.share_pct}%</td>
        <td class="num">${fmtRupiahFull(c.rata_harga)}</td>
        <td class="num">${fmtInt(c.rata_terjual)}</td>
        <td class="num"><span class="rating-pill">${c.rata_rating.toFixed(2)}</span></td>
        <td class="num">${c.rata_diskon.toFixed(1)}%</td>
        <td class="num"><strong>${fmtRupiahShort(c.total_gmv)}</strong></td>
      </tr>
    `).join('');

  getChart('chart-demo-age').setOption({
    tooltip: { ...TOOLTIP_STYLE, trigger: 'axis' },
    grid: { top: 16, left: 10, right: 14, bottom: 14, containLabel: true },
    xAxis: { type: 'category', data: demographics.age_stats.map((a) => a.group), axisLine: { lineStyle: { color: '#CCC8B8' } }, axisLabel: { color: PALETTE.ink, fontSize: 12 } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: PALETTE.grid } }, axisLabel: { color: PALETTE.muted, fontFamily: 'JetBrains Mono', fontSize: 11 } },
    series: [{ name: 'Item Dibeli', type: 'bar', barMaxWidth: 46, data: demographics.age_stats.map((a, i) => ({ value: a.items, itemStyle: { color: SERIES_COLORS[i], borderRadius: [4, 4, 0, 0] } })) }],
  }, true);

  getChart('chart-demo-gender').setOption({
    tooltip: { ...TOOLTIP_STYLE, trigger: 'item', formatter: (p) => `<b>${escapeHtml(p.name)}</b><br/>${fmtInt(p.value)} item dibeli (${p.percent}%)` },
    legend: { bottom: 4, icon: 'circle', textStyle: { color: PALETTE.ink, fontSize: 12 } },
    color: [PALETTE.emerald, PALETTE.terracotta],
    series: [{ type: 'pie', radius: ['52%', '74%'], center: ['50%', '45%'], itemStyle: { borderColor: '#FFF', borderWidth: 2 }, label: { show: true, formatter: '{d}%', fontFamily: 'JetBrains Mono', fontSize: 12, fontWeight: 600 }, data: demographics.gender_stats.map((g) => ({ name: g.gender, value: g.items })) }],
  }, true);
}

// ==========================================
// PROMPT BUILDER & UPLOAD HANDLER
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
   - 'Nama Produk': Judul nama barang yang jelas dan realistis.
   - 'Nama Toko': Nama merchant / toko penjual.
   - 'Lokasi Toko': Nama kota di Indonesia (misal: Jakarta Selatan, Bandung, Surabaya, Medan).
   - 'Terjual': Format teks kuantitas (contoh: '1.5rb+ terjual', '850 terjual', atau '50 terjual').
   - 'Jumlah Ulasan': Format ulasan (contoh: '250 ulasan' atau '15 ulasan').
   - 'Rating': Angka desimal titik antara 3.8 sampai 5.0 (contoh: 4.8).
   - 'Harga (IDR)': Angka bulat Rupiah tanpa titik/Rp (contoh: 85000).
   - 'Diskon (%)': Angka persentase diskon 0 sampai 50 (contoh: 15.0).
   - 'Produk URL': Link dummy (contoh: https://www.tokopedia.com/toko/nama-produk).
4. PENTING: Tampilkan HANYA blok kode teks CSV mentah (raw CSV) tanpa teks pengantar atau penutup agar langsung bisa saya simpan sebagai file .csv.`;
}

async function handleCSVUpload(file) {
  const feedback = document.getElementById('upload-feedback');
  const gotoBtn = document.getElementById('btn-goto-ringkasan');
  feedback.classList.remove('hidden', 'ok', 'err');
  feedback.textContent = `Sedang memproses "${file.name}"...`;

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
    populateFilterDropdowns(data.meta);
    await fetchDashboard();
    showToast(`File ${file.name} berhasil dimuat!`);
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
// EVENTS & BOOTSTRAP
// ==========================================
function bindEvents() {
  // Sidebar navigation
  document.querySelectorAll('.nav-item').forEach((btn) => {
    btn.addEventListener('click', () => navigateTo(btn.dataset.page));
  });

  document.getElementById('btn-sidebar-upload').addEventListener('click', () => navigateTo('unggah'));
  document.getElementById('active-dataset-chip').addEventListener('click', () => navigateTo('unggah'));
  document.getElementById('btn-goto-ringkasan').addEventListener('click', () => navigateTo('ringkasan'));

  // Mobile sidebar
  document.getElementById('btn-mobile-menu').addEventListener('click', openMobileSidebar);
  document.getElementById('sidebar-backdrop').addEventListener('click', closeMobileSidebar);

  // Filters
  document.getElementById('filter-category').addEventListener('change', (e) => setFilter('category', e.target.value));
  document.getElementById('filter-city').addEventListener('change', (e) => setFilter('city', e.target.value));
  document.getElementById('filter-price').addEventListener('change', (e) => setFilter('priceKey', e.target.value));
  document.getElementById('filter-rating').addEventListener('change', (e) => setFilter('min_rating', e.target.value));
  document.getElementById('btn-reset-filters').addEventListener('click', () => resetAllFilters(true));

  // Metric switches
  document.querySelectorAll('#cat-metric-toggle .seg-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#cat-metric-toggle .seg-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      state.catMetric = btn.dataset.metric;
      renderPageRingkasan();
    });
  });
  document.querySelectorAll('#geo-metric-toggle .seg-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#geo-metric-toggle .seg-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      state.geoMetric = btn.dataset.metric;
      renderPageGeografi();
    });
  });

  // Product search / sort / limit
  document.getElementById('product-search').addEventListener('input', (e) => {
    state.filters.search = e.target.value;
    clearTimeout(state.debounceTimer);
    state.debounceTimer = setTimeout(fetchDashboard, 250);
  });
  document.getElementById('product-sort').addEventListener('change', (e) => {
    state.filters.sort_by = e.target.value;
    fetchDashboard();
  });
  document.getElementById('product-limit').addEventListener('change', (e) => {
    state.filters.top_n = parseInt(e.target.value, 10);
    fetchDashboard();
  });

  // CSV Dropzone
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

  // Reset to Default Dataset
  document.getElementById('btn-reset-dataset').addEventListener('click', async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/reset', { method: 'POST' });
      const data = await res.json();
      resetAllFilters(false);
      populateFilterDropdowns(data.meta);
      await fetchDashboard();
      document.getElementById('upload-feedback').classList.add('hidden');
      document.getElementById('btn-goto-ringkasan').classList.add('hidden');
      showToast('Dataset dikembalikan ke katalog bawaan Tokopedia.');
    } catch (_) {
      showToast('Gagal mengembalikan data bawaan', true);
    } finally {
      setLoading(false);
    }
  });

  // Prompt Builder & Copy
  document.getElementById('prompt-rows').addEventListener('input', updateAIPromptText);
  document.getElementById('prompt-cats').addEventListener('input', updateAIPromptText);
  document.getElementById('btn-copy-prompt').addEventListener('click', async () => {
    await copyTextSafe(document.getElementById('ai-prompt-output').textContent);
    showToast('Prompt AI berhasil disalin!');
  });
  document.getElementById('btn-copy-spark').addEventListener('click', async () => {
    await copyTextSafe(document.getElementById('spark-code-snippet').textContent);
    showToast('Kode PySpark berhasil disalin!');
  });

  window.addEventListener('resize', resizeCharts);
}

async function init() {
  bindEvents();
  updateAIPromptText();
  try {
    const metaRes = await fetch('/api/meta');
    const meta = await metaRes.json();
    populateFilterDropdowns(meta);
    await fetchDashboard();
  } catch (_) {
    showToast('Gagal terhubung ke server FastAPI', true);
  }
}

document.addEventListener('DOMContentLoaded', init);
