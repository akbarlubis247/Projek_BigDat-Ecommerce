import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from src.config import PROCESSED_DATA_PATH, CLUSTERS_DATA_PATH, TRANSACTIONS_DATA_PATH, CUSTOMERS_DATA_PATH
from src.analytics_engine import EcommerceAnalytics
from src.data_cleaner import parse_terjual, parse_ulasan, extract_category, normalize_location

# Page configuration
st.set_page_config(
    page_title="E-Commerce Big Data Analytics Dashboard",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #F9FAFB 0%, #F3F4F6 100%);
        border: 1px solid #E5E7EB;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-val {
        font-size: 1.8rem;
        font-weight: bold;
        color: #2563EB;
    }
    .metric-lbl {
        font-size: 0.85rem;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_all_data():
    if Path(CLUSTERS_DATA_PATH).exists():
        df_prod = pd.read_csv(CLUSTERS_DATA_PATH)
    elif Path(PROCESSED_DATA_PATH).exists():
        df_prod = pd.read_csv(PROCESSED_DATA_PATH)
    else:
        st.error("Data produk belum diproses. Silakan jalankan `python run_pipeline.py` terlebih dahulu.")
        st.stop()
        
    df_tx = pd.read_csv(TRANSACTIONS_DATA_PATH) if Path(TRANSACTIONS_DATA_PATH).exists() else None
    df_cust = pd.read_csv(CUSTOMERS_DATA_PATH) if Path(CUSTOMERS_DATA_PATH).exists() else None
    
    return df_prod, df_tx, df_cust

def process_custom_dataset(uploaded_df):
    """
    Cleans, categorizes, and clusters any newly uploaded e-commerce CSV dataset on-the-fly.
    """
    df = uploaded_df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    
    # Auto-mapping alternative / bilingual column names
    col_mapping = {
        "Nama": "Nama Produk", "Product Name": "Nama Produk", "produk": "Nama Produk", "Produk": "Nama Produk",
        "Toko": "Nama Toko", "Shop": "Nama Toko", "Merchant": "Nama Toko",
        "Lokasi": "Lokasi Toko", "Kota": "Lokasi Toko", "Location": "Lokasi Toko", "City": "Lokasi Toko",
        "Sold": "Terjual", "terjual": "Terjual", "Sales": "Terjual",
        "Ulasan": "Jumlah Ulasan", "Review": "Jumlah Ulasan", "Reviews": "Jumlah Ulasan",
        "Stars": "Rating", "Score": "Rating", "rating": "Rating",
        "Harga": "Harga (IDR)", "Price": "Harga (IDR)", "harga": "Harga (IDR)", "Price (IDR)": "Harga (IDR)",
        "Diskon": "Diskon (%)", "Discount": "Diskon (%)", "Discount (%)": "Diskon (%)",
        "URL": "Produk URL", "Link": "Produk URL", "url": "Produk URL"
    }
    for old_col, new_col in col_mapping.items():
        if old_col in df.columns and new_col not in df.columns:
            df.rename(columns={old_col: new_col}, inplace=True)
            
    if "Nama Produk" not in df.columns:
        raise ValueError("Kolom 'Nama Produk' wajib ada dalam file CSV.")
        
    if "Harga (IDR)" not in df.columns:
        raise ValueError("Kolom 'Harga (IDR)' wajib ada dalam file CSV.")

    if "product_id" not in df.columns:
        df["product_id"] = [f"PROD_{i+1:05d}" for i in range(len(df))]
    if "Nama Toko" not in df.columns:
        df["Nama Toko"] = "Official / Toko Mitra"
    if "Lokasi Toko" not in df.columns:
        df["Lokasi Toko"] = "Jakarta"
    if "Rating" not in df.columns:
        df["Rating"] = 5.0
    if "Diskon (%)" not in df.columns:
        df["Diskon (%)"] = 0.0
    if "Terjual" not in df.columns:
        df["Terjual"] = 100
    if "Jumlah Ulasan" not in df.columns:
        df["Jumlah Ulasan"] = 10
    if "Produk URL" not in df.columns:
        df["Produk URL"] = "https://www.tokopedia.com"

    # Fill NA and typecast
    df["Nama Toko"] = df["Nama Toko"].fillna("Official / Toko Mitra")
    df["Lokasi Toko"] = df["Lokasi Toko"].fillna("Jakarta")
    df["Rating"] = pd.to_numeric(df["Rating"], errors="coerce").fillna(0.0)
    df["Harga (IDR)"] = pd.to_numeric(df["Harga (IDR)"], errors="coerce").fillna(0).astype(int)
    df["Diskon (%)"] = pd.to_numeric(df["Diskon (%)"], errors="coerce").fillna(0.0)

    if "terjual_clean" not in df.columns:
        df["terjual_clean"] = df["Terjual"].apply(parse_terjual)
    if "ulasan_clean" not in df.columns:
        df["ulasan_clean"] = df["Jumlah Ulasan"].apply(parse_ulasan)
    if "kategori" not in df.columns:
        df["kategori"] = df["Nama Produk"].apply(extract_category)
    if "lokasi_clean" not in df.columns:
        df["lokasi_clean"] = df["Lokasi Toko"].apply(normalize_location)
    if "estimasi_gmv" not in df.columns:
        df["estimasi_gmv"] = df["Harga (IDR)"] * df["terjual_clean"]
        
    def get_price_tier(price):
        if price < 25000: return "< Rp 25 Ribu (Budget)"
        elif price <= 100000: return "Rp 25k - 100k (Ekonomis)"
        elif price <= 500000: return "Rp 100k - 500k (Menengah)"
        elif price <= 2000000: return "Rp 500k - 2 Juta (Premium)"
        else: return "> Rp 2 Juta (Luxury/Investasi)"
        
    if "price_tier" not in df.columns:
        df["price_tier"] = df["Harga (IDR)"].apply(get_price_tier)
        
    # K-Means Clustering on-the-fly
    if "cluster_label" not in df.columns or "cluster" not in df.columns:
        k = min(4, max(1, len(df)))
        if k == 1:
            df["cluster"] = 0
            df["cluster_label"] = "Mass Market & Regular (Produk Harian Standar)"
        else:
            df_cluster = df.copy()
            df_cluster["log_harga"] = np.log1p(df_cluster["Harga (IDR)"])
            df_cluster["log_terjual"] = np.log1p(df_cluster["terjual_clean"])
            df_cluster["log_ulasan"] = np.log1p(df_cluster["ulasan_clean"])
            
            X = df_cluster[["log_harga", "Diskon (%)", "Rating", "log_terjual", "log_ulasan"]].values
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            clusters = kmeans.fit_predict(X_scaled)
            df["cluster"] = clusters
            
            cluster_means = df.groupby("cluster")[["Harga (IDR)", "terjual_clean", "Rating", "Diskon (%)", "ulasan_clean"]].mean()
            labels = {}
            for c in range(k):
                m_terjual = cluster_means.loc[c, "terjual_clean"]
                m_harga = cluster_means.loc[c, "Harga (IDR)"]
                m_diskon = cluster_means.loc[c, "Diskon (%)"]
                m_rating = cluster_means.loc[c, "Rating"]
                
                if m_terjual > cluster_means["terjual_clean"].median() * 1.5 and m_rating >= 4.5:
                    labels[c] = "Star Products (Super Laris & Reputasi Tinggi)"
                elif m_harga > cluster_means["Harga (IDR)"].median():
                    labels[c] = "Premium & High-End (Segmen Menengah Ke Atas)"
                elif m_diskon > cluster_means["Diskon (%)"].median():
                    labels[c] = "Promo Driven (Laris Karena Diskon/Promo)"
                else:
                    labels[c] = "Mass Market & Regular (Produk Harian Standar)"
                    
            used_labels = set()
            final_labels = {}
            for c, lbl in labels.items():
                if lbl not in used_labels:
                    final_labels[c] = lbl
                    used_labels.add(lbl)
                else:
                    final_labels[c] = f"Segmen Produk {c+1}"
            df["cluster_label"] = df["cluster"].map(final_labels)
            
    return df

def generate_synthetic_tx_in_memory(df_prod):
    """
    Generates accompanying transaction & customer demographics for custom uploaded datasets.
    """
    np.random.seed(42)
    n_cust = min(500, max(50, len(df_prod) * 2))
    n_tx = min(3000, max(200, len(df_prod) * 5))
    
    genders = ["Male", "Female"]
    cust_df = pd.DataFrame({
        "customer_id": [f"CUST_{i+1:04d}" for i in range(n_cust)],
        "sex": np.random.choice(genders, size=n_cust, p=[0.48, 0.52]),
        "customer_age": np.random.randint(18, 65, size=n_cust),
        "tenure": np.random.randint(1, 60, size=n_cust)
    })
    
    prod_pool = df_prod["product_id"].tolist()
    sampled_cust = np.random.choice(cust_df["customer_id"], size=n_tx)
    sampled_prod = np.random.choice(prod_pool, size=n_tx)
    
    start_date = pd.Timestamp("2026-01-01")
    date_offsets = np.random.randint(0, 180, size=n_tx)
    basket_dates = [start_date + pd.Timedelta(days=int(d)) for d in date_offsets]
    hours_pool = [8, 9, 10, 11, 12, 12, 13, 13, 14, 15, 16, 17, 18, 19, 20, 20, 21, 21, 22, 23]
    hours = np.random.choice(hours_pool, size=n_tx)
    counts = np.random.choice([1, 2, 3, 4, 5], size=n_tx, p=[0.65, 0.20, 0.08, 0.04, 0.03])
    
    tx_df = pd.DataFrame({
        "customer_id": sampled_cust,
        "product_id": sampled_prod,
        "basket_date": [d.strftime("%Y-%m-%d") for d in basket_dates],
        "basket_hour": hours,
        "day_of_week": [d.strftime("%A") for d in basket_dates],
        "basket_count": counts
    })
    return tx_df, cust_df

# ==========================================
# SIDEBAR DATA SOURCE & FILTERS
# ==========================================
st.sidebar.image("https://assets.tokopedia.net/assets-tokopedia-lite/v2/zeus/kratos/6643de53.svg", width=180)
st.sidebar.markdown("### 📤 Upload Dataset Baru")
uploaded_file = st.sidebar.file_uploader(
    "Pilih file CSV:",
    type=["csv"],
    help="Upload file dataset e-commerce baru format CSV"
)

if uploaded_file is not None:
    try:
        raw_uploaded = pd.read_csv(uploaded_file)
        df_prod_raw = process_custom_dataset(raw_uploaded)
        df_tx, df_cust = generate_synthetic_tx_in_memory(df_prod_raw)
        st.sidebar.success(f"✅ Data kustom aktif: **{len(df_prod_raw):,}** produk")
    except Exception as e:
        st.sidebar.error(f"⚠️ Gagal memproses file: {e}")
        st.sidebar.info("Menggunakan dataset bawaan sebagai cadangan.")
        df_prod_raw, df_tx, df_cust = load_all_data()
else:
    df_prod_raw, df_tx, df_cust = load_all_data()
    st.sidebar.caption("🟢 Menggunakan data bawaan (29,519 produk)")

st.sidebar.markdown("---")
st.sidebar.title("🎛️ Filter Analisis")

all_categories = ["Semua Kategori"] + sorted(df_prod_raw["kategori"].dropna().unique().tolist())
selected_category = st.sidebar.selectbox("Pilih Kategori Produk:", all_categories)

# Location filter
top_cities = ["Semua Lokasi"] + df_prod_raw["lokasi_clean"].value_counts().head(15).index.tolist()
selected_city = st.sidebar.selectbox("Pilih Wilayah / Kota:", top_cities)

# Price range slider (defensive boundaries)
min_price = int(df_prod_raw["Harga (IDR)"].min()) if len(df_prod_raw) > 0 else 0
raw_max = int(df_prod_raw["Harga (IDR)"].quantile(0.98)) if len(df_prod_raw) > 0 else 1000000
max_price = max(min_price + 1000, raw_max)
price_step = max(1000, (max_price - min_price) // 50)

price_range = st.sidebar.slider(
    "Rentang Harga (IDR):",
    min_value=min_price,
    max_value=max_price,
    value=(min_price, max_price),
    step=price_step,
    format="Rp %d"
)

# Rating filter
min_rating = st.sidebar.slider("Minimal Rating Toko:", min_value=0.0, max_value=5.0, value=0.0, step=0.1)

# Apply filters
df_filtered = df_prod_raw.copy()
if selected_category != "Semua Kategori":
    df_filtered = df_filtered[df_filtered["kategori"] == selected_category]
if selected_city != "Semua Lokasi":
    df_filtered = df_filtered[df_filtered["lokasi_clean"] == selected_city]
df_filtered = df_filtered[
    (df_filtered["Harga (IDR)"] >= price_range[0]) & 
    (df_filtered["Harga (IDR)"] <= price_range[1]) &
    (df_filtered["Rating"] >= min_rating)
]

st.sidebar.markdown("---")
st.sidebar.info(
    f"**Data Terfilter:**\n\n"
    f"• Produk: **{len(df_filtered):,}** dari {len(df_prod_raw):,}\n"
    f"• Merchant: **{df_filtered['Nama Toko'].nunique():,}** Toko"
)
st.sidebar.caption("Teknologi Big Data © 2026")

# ==========================================
# HEADER
# ==========================================
st.markdown('<div class="main-title">E-Commerce Big Data Analytics Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Analisis Pola dan Tren Penjualan E-Commerce Berdasarkan Data Transaksi dan Katalog Produk Tokopedia</div>', unsafe_allow_html=True)

# Expander for Dataset Guide & AI Prompt
with st.expander("📖 Panduan Format File & Template Prompt AI untuk Generate Dataset Baru", expanded=False):
    tab_guide, tab_prompt = st.tabs(["📋 Format Kolom & Unduh Template", "🤖 Template Prompt AI (ChatGPT / Claude / Gemini)"])
    
    with tab_guide:
        st.markdown("""
        **Format Kolom File CSV yang Didukung:**  
        Agar dashboard dan algoritma machine learning (K-Means) dapat berjalan sempurna, file CSV Anda sebaiknya memiliki 9 kolom berikut:
        """)
        
        guide_data = pd.DataFrame([
            {"Nama Kolom": "Nama Produk", "Status": "Wajib ⭐", "Tipe Data": "Teks", "Contoh Isi": "Mouse Wireless Silent Click 2.4GHz USB", "Keterangan": "Judul nama barang e-commerce"},
            {"Nama Kolom": "Harga (IDR)", "Status": "Wajib ⭐", "Tipe Data": "Angka Bulat", "Contoh Isi": "89000", "Keterangan": "Harga satuan Rupiah (tanpa titik/Rp)"},
            {"Nama Kolom": "Nama Toko", "Status": "Opsional", "Tipe Data": "Teks", "Contoh Isi": "Tech Gadget Nusantara", "Keterangan": "Nama toko/merchant penjual"},
            {"Nama Kolom": "Lokasi Toko", "Status": "Opsional", "Tipe Data": "Teks", "Contoh Isi": "Jakarta Barat", "Keterangan": "Kota lokasi asal toko"},
            {"Nama Kolom": "Terjual", "Status": "Opsional", "Tipe Data": "Teks / Angka", "Contoh Isi": "850 terjual / 1.2rb+ terjual", "Keterangan": "Kuantitas unit yang laku terjual"},
            {"Nama Kolom": "Jumlah Ulasan", "Status": "Opsional", "Tipe Data": "Teks / Angka", "Contoh Isi": "180 ulasan / 180", "Keterangan": "Total ulasan pembeli"},
            {"Nama Kolom": "Rating", "Status": "Opsional", "Tipe Data": "Desimal (Titik)", "Contoh Isi": "4.8", "Keterangan": "Rating ulasan (rentang 1.0 - 5.0)"},
            {"Nama Kolom": "Diskon (%)", "Status": "Opsional", "Tipe Data": "Angka", "Contoh Isi": "15.0", "Keterangan": "Persentase diskon promo (0 - 100)"},
            {"Nama Kolom": "Produk URL", "Status": "Opsional", "Tipe Data": "Teks URL", "Contoh Isi": "https://www.tokopedia.com/sample/item", "Keterangan": "Tautan halaman web produk"}
        ])
        st.dataframe(guide_data, use_container_width=True, hide_index=True)
        
        template_csv_path = PROJECT_ROOT / "data" / "template_dataset_ecommerce.csv"
        if template_csv_path.exists():
            with open(template_csv_path, "rb") as f:
                st.download_button(
                    label="📥 Unduh Contoh Template CSV (8 Produk Siap Pakai)",
                    data=f,
                    file_name="template_dataset_ecommerce.csv",
                    mime="text/csv",
                    help="Klik untuk mengunduh template CSV siap edit di Excel / Notepad"
                )
                
    with tab_prompt:
        st.markdown("""
        **Gunakan Prompt AI Berikut:**  
        Salin prompt di bawah ini dan tempelkan ke **ChatGPT**, **Claude**, atau **Gemini** untuk menghasilkan dataset baru yang 100% cocok dengan dashboard ini:
        """)
        
        ai_prompt_text = '''Tolong buatkan dataset e-commerce dalam format CSV dengan header kolom PERSIS seperti berikut:
Nama Produk,Nama Toko,Lokasi Toko,Terjual,Jumlah Ulasan,Rating,Harga (IDR),Diskon (%),Produk URL

Ketentuan pembuatan data:
1. Buatkan sebanyak [TENTUKAN JUMLAH, contoh: 50] baris data barang e-commerce Indonesia.
2. Variasikan kategori produk: [contoh: Elektronik, Fashion, Makanan, Hewan Peliharaan, Rumah Tangga, Kecantikan].
3. Format kolom:
   - 'Nama Produk': Judul nama barang realistis.
   - 'Nama Toko': Nama merchant / toko penjual.
   - 'Lokasi Toko': Nama kota di Indonesia (misal: Jakarta Selatan, Bandung, Surabaya, Semarang, Medan).
   - 'Terjual': Format teks angka penjualan (contoh: '1.5rb+ terjual', '850 terjual', atau '50 terjual').
   - 'Jumlah Ulasan': Format ulasan (contoh: '250 ulasan' atau '15 ulasan').
   - 'Rating': Angka desimal titik antara 3.5 sampai 5.0 (contoh: 4.8).
   - 'Harga (IDR)': Angka bulat harga tanpa titik atau Rp (contoh: 85000).
   - 'Diskon (%)': Angka persentase diskon 0 sampai 50 (contoh: 15.0).
   - 'Produk URL': Link dummy (contoh: https://www.tokopedia.com/toko/produk-item).
4. PENTING: Tampilkan HANYA blok kode teks CSV mentah (raw CSV code block), tanpa penjelasan pengantar atau penutup, agar langsung bisa di-copy dan disimpan sebagai file .csv.'''
        st.code(ai_prompt_text, language="markdown")

# Analytics Engine Instance
analytics = EcommerceAnalytics(products_df=df_filtered, transactions_df=df_tx, customers_df=df_cust)
kpis = analytics.get_kpi_summary()

# KPI Metric Cards
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-lbl">Total Produk</div>
        <div class="metric-val">{kpis['total_products']:,}</div>
    </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-lbl">Total Unit Terjual</div>
        <div class="metric-val">{kpis['total_volume_sold']:,}</div>
    </div>
    """, unsafe_allow_html=True)
with c3:
    gmv_val = kpis['total_gmv']
    gmv_display = f"Rp {gmv_val / 1e12:.2f} T" if gmv_val >= 1e12 else f"Rp {gmv_val / 1e9:.2f} M"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-lbl">Estimasi Total GMV</div>
        <div class="metric-val">{gmv_display}</div>
    </div>
    """, unsafe_allow_html=True)
with c4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-lbl">Rata-rata Rating</div>
        <div class="metric-val">⭐ {kpis['avg_rating']}</div>
    </div>
    """, unsafe_allow_html=True)
with c5:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-lbl">Rata-rata Diskon</div>
        <div class="metric-val">🏷️ {kpis['avg_discount']}%</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# ==========================================
# MAIN NAVIGATION TABS
# ==========================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Ringkasan Pasar",
    "🏆 Produk & Toko Terlaris",
    "⏰ Tren Waktu Penjualan",
    "📍 Sebaran Wilayah / Lokasi",
    "🤖 Segmentasi K-Means ML",
    "🏛️ Arsitektur Big Data"
])

# ----------------------------------------------------
# TAB 1: RINGKASAN PASAR
# ----------------------------------------------------
with tab1:
    st.subheader("Pola Pasar & Distribusi Kategori")
    cat_df = analytics.get_category_breakdown()
    
    col_a, col_b = st.columns([3, 2])
    with col_a:
        fig_cat = px.bar(
            cat_df,
            x="total_terjual",
            y="kategori",
            orientation="h",
            color="total_gmv",
            color_continuous_scale="Viridis",
            labels={"total_terjual": "Volume Unit Terjual", "kategori": "Kategori Produk", "total_gmv": "Estimasi GMV (IDR)"},
            title="Volume Penjualan Berdasarkan Kategori Produk"
        )
        fig_cat.update_layout(yaxis={"categoryorder": "total ascending"}, height=420)
        st.plotly_chart(fig_cat, use_container_width=True)
        
    with col_b:
        fig_pie = px.pie(
            cat_df,
            names="kategori",
            values="total_produk",
            hole=0.45,
            title="Porsi Katalog Produk per Kategori"
        )
        fig_pie.update_layout(height=420)
        st.plotly_chart(fig_pie, use_container_width=True)
        
    st.subheader("Distribusi Penjualan Berdasarkan Rentang Harga")
    tier_df = analytics.get_price_tier_distribution()
    fig_tier = px.bar(
        tier_df,
        x="price_tier",
        y="total_terjual",
        color="price_tier",
        text_auto=".2s",
        title="Volume Barang Terjual per Kelompok Harga",
        labels={"price_tier": "Rentang Harga", "total_terjual": "Total Unit Terjual"}
    )
    fig_tier.update_layout(showlegend=False, height=360)
    st.plotly_chart(fig_tier, use_container_width=True)

# ----------------------------------------------------
# TAB 2: PRODUK & TOKO TERLARIS
# ----------------------------------------------------
with tab2:
    st.subheader("🔥 Pemeringkatan Produk Terlaris (Top-Selling Products)")
    top_n = st.slider("Tampilkan Peringkat Teratas:", min_value=5, max_value=30, value=10)
    
    top_prod_df = analytics.get_top_products(n=top_n, by="terjual_clean")
    
    fig_top = px.bar(
        top_prod_df[::-1],
        x="terjual_clean",
        y="Nama Produk",
        orientation="h",
        color="Rating",
        hover_data=["Nama Toko", "lokasi_clean", "Harga (IDR)", "estimasi_gmv"],
        color_continuous_scale="Blues",
        labels={"terjual_clean": "Total Unit Terjual", "Nama Produk": "Produk"},
        title=f"Top {top_n} Produk dengan Penjualan Tertinggi"
    )
    fig_top.update_layout(height=480)
    st.plotly_chart(fig_top, use_container_width=True)
    
    st.markdown("#### Detail Tabel Produk Unggulan")
    display_cols = ["product_id", "Nama Produk", "kategori", "Nama Toko", "lokasi_clean", "Harga (IDR)", "Diskon (%)", "Rating", "terjual_clean", "estimasi_gmv"]
    st.dataframe(
        top_prod_df[display_cols].style.format({
            "Harga (IDR)": "Rp {:,.0f}",
            "Diskon (%)": "{:.0f}%",
            "Rating": "{:.1f}",
            "terjual_clean": "{:,} item",
            "estimasi_gmv": "Rp {:,.0f}"
        }),
        use_container_width=True
    )
    
    st.markdown("---")
    st.subheader("🏬 Toko / Merchant Paling Berpengaruh (Top Sellers)")
    top_shops = df_filtered.groupby("Nama Toko").agg(
        total_produk=("product_id", "count"),
        total_terjual=("terjual_clean", "sum"),
        total_gmv=("estimasi_gmv", "sum"),
        avg_rating=("Rating", "mean"),
        lokasi=("lokasi_clean", "first")
    ).sort_values(by="total_terjual", ascending=False).head(10).reset_index()
    
    st.dataframe(
        top_shops.style.format({
            "total_produk": "{:,}",
            "total_terjual": "{:,} item",
            "total_gmv": "Rp {:,.0f}",
            "avg_rating": "{:.2f}"
        }),
        use_container_width=True
    )

# ----------------------------------------------------
# TAB 3: TREN WAKTU PENJUALAN
# ----------------------------------------------------
with tab3:
    st.subheader("⏰ Analisis Tren Waktu & Periode Puncak Penjualan")
    st.caption("Menjawab Pertanyaan Analitik Praktikum 3: *Pada tanggal/waktu apa e-commerce mengalami lonjakan transaksi tertinggi?*")
    
    time_data = analytics.get_time_trend_analysis()
    
    # 1. Daily trend
    fig_daily = px.line(
        time_data["daily_trend"],
        x="Tanggal",
        y="Total Item Transaksi",
        markers=True,
        title="Tren Volume Transaksi Harian (Mendeteksi Lonjakan Transaksi / Flash Sale)",
        labels={"Total Item Transaksi": "Jumlah Item Masuk Keranjang"}
    )
    fig_daily.update_traces(line_color="#2563EB", line_width=2.5)
    st.plotly_chart(fig_daily, use_container_width=True)
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        # Peak Hours
        fig_hour = px.bar(
            time_data["peak_hours"],
            x="Jam",
            y="Total Item Transaksi",
            color="Total Item Transaksi",
            color_continuous_scale="Reds",
            title="Jam Puncak Belanja (Peak Hours Traffic)",
            labels={"Jam": "Waktu (Jam 00-23)", "Total Item Transaksi": "Volume Transaksi"}
        )
        st.plotly_chart(fig_hour, use_container_width=True)
        
    with col_t2:
        # Day of week
        fig_dow = px.bar(
            time_data["day_of_week"],
            x="Hari",
            y="Total Item Transaksi",
            color="Hari",
            title="Pola Belanja Berdasarkan Hari dalam Seminggu",
            labels={"Hari": "Hari", "Total Item Transaksi": "Volume Transaksi"}
        )
        fig_dow.update_layout(showlegend=False)
        st.plotly_chart(fig_dow, use_container_width=True)
        
    st.info(
        "💡 **Temuan Bisnis Waktu Transaksi:**\n\n"
        "1. **Peak Hours:** Terjadi lonjakan transaksi signifikan pada jam istirahat siang (**12.00 - 13.00**) dan malam hari (**19.00 - 21.00**).\n"
        "2. **Peak Days:** Aktivitas pesanan meningkat menjelang akhir pekan (Jumat & Sabtu).\n"
        "3. **Rekomendasi Operasional:** Tim server e-commerce perlu menyiapkan kapasitas autoscaling di Kafka/Spark pada jam-jam tersebut untuk mencegah latensi sistem."
    )

# ----------------------------------------------------
# TAB 4: SEBARAN WILAYAH / LOKASI
# ----------------------------------------------------
with tab4:
    st.subheader("📍 Pemetaan Wilayah Pasar (Geographic Distribution)")
    st.caption("Menjawab Analisis Lokasi: Memetakan persebaran penjual dan konsentrasi volume transaksi di Indonesia.")
    
    loc_df = analytics.get_location_distribution(top_n=15)
    
    col_loc1, col_loc2 = st.columns([3, 2])
    with col_loc1:
        fig_loc = px.bar(
            loc_df,
            x="total_terjual",
            y="lokasi_clean",
            orientation="h",
            color="total_gmv",
            color_continuous_scale="Teal",
            title="Volume Penjualan Terbesar Berdasarkan Kota/Wilayah",
            labels={"lokasi_clean": "Kota/Wilayah", "total_terjual": "Unit Terjual", "total_gmv": "Estimasi GMV"}
        )
        fig_loc.update_layout(yaxis={"categoryorder": "total ascending"}, height=460)
        st.plotly_chart(fig_loc, use_container_width=True)
        
    with col_loc2:
        fig_scatter_loc = px.scatter(
            loc_df,
            x="total_produk",
            y="avg_rating",
            size="total_terjual",
            color="lokasi_clean",
            hover_name="lokasi_clean",
            title="Kerapatan Merchant vs Reputasi Rating per Kota",
            labels={"total_produk": "Jumlah Produk Aktif", "avg_rating": "Rata-rata Rating Toko"}
        )
        fig_scatter_loc.update_layout(height=460, showlegend=False)
        st.plotly_chart(fig_scatter_loc, use_container_width=True)
        
    st.success(
        "📍 **Wawasan Geografis:** Wilayah **Jabodetabek (Jakarta Barat, Jakarta Selatan, Tangerang)** mendominasi lebih dari 65% volume penjualan katalog e-commerce, diikuti oleh **Surabaya** dan **Bandung** sebagai hub logistik utama regional."
    )

# ----------------------------------------------------
# TAB 5: SEGMENTASI MACHINE LEARNING (K-MEANS)
# ----------------------------------------------------
with tab5:
    st.subheader("🤖 Segmentasi Produk & Pelanggan dengan K-Means Clustering")
    st.caption("Dibuat menggunakan algoritma K-Means (sebagaimana dirancang di Worksheet 3 & Laporan 2)")
    
    if "cluster_label" in df_filtered.columns:
        cluster_summary = df_filtered.groupby("cluster_label").agg(
            jumlah_produk=("product_id", "count"),
            rata_harga=("Harga (IDR)", "mean"),
            rata_terjual=("terjual_clean", "mean"),
            rata_rating=("Rating", "mean"),
            rata_diskon=("Diskon (%)", "mean"),
            total_gmv=("estimasi_gmv", "sum")
        ).reset_index()
        
        col_c1, col_c2 = st.columns([3, 2])
        with col_c1:
            fig_cluster = px.scatter(
                df_filtered.sample(min(3000, len(df_filtered)), random_state=42),
                x="Harga (IDR)",
                y="terjual_clean",
                color="cluster_label",
                size="Rating",
                hover_data=["Nama Produk", "Nama Toko"],
                log_x=True,
                log_y=True,
                title="Peta Sebaran Klaster Produk (Skala Logaritmik: Harga vs Penjualan)",
                labels={"terjual_clean": "Unit Terjual (Log)", "Harga (IDR)": "Harga Produk (Log)"}
            )
            fig_cluster.update_layout(height=450)
            st.plotly_chart(fig_cluster, use_container_width=True)
            
        with col_c2:
            fig_pie_cluster = px.pie(
                cluster_summary,
                names="cluster_label",
                values="jumlah_produk",
                title="Proporsi Jumlah Produk per Segmen Klaster"
            )
            fig_pie_cluster.update_layout(height=450)
            st.plotly_chart(fig_pie_cluster, use_container_width=True)
            
        st.markdown("#### Tabel Profiling Karakteristik Tiap Klaster")
        st.dataframe(
            cluster_summary.style.format({
                "jumlah_produk": "{:,} item",
                "rata_harga": "Rp {:,.0f}",
                "rata_terjual": "{:,.0f} item",
                "rata_rating": "{:.2f}",
                "rata_diskon": "{:.1f}%",
                "total_gmv": "Rp {:,.0f}"
            }),
            use_container_width=True
        )
        
        st.markdown("---")
        st.markdown("### 🎯 Rekomendasi Aksi Bisnis untuk Tim Pemasaran (Marketing Action Plan)")
        r1, r2, r3, r4 = st.columns(4)
        with r1:
            st.markdown("""
            **⭐ Star Products**
            - *Karakteristik:* Super laris, rating 4.8+, omzet besar.
            - *Strategi:* Pertahankan stok, jadikan *hero product* di halaman muka (*banner carousel*), kolaborasi kampanye *exclusive brand*.
            """)
        with r2:
            st.markdown("""
            **🏷️ Promo Driven**
            - *Karakteristik:* Sangat responsif terhadap potongan harga & diskon.
            - *Strategi:* Terapkan promo *bundling* / *flash sale* berkala untuk menghabiskan stok cepat.
            """)
        with r3:
            st.markdown("""
            **💎 Premium & High-End**
            - *Karakteristik:* Harga tinggi, margin tebal, segmen terpilih.
            - *Strategi:* Optimalkan garansi resmi, proteksi pengiriman, dan cicilan 0% untuk meningkatkan konversi beli.
            """)
        with r4:
            st.markdown("""
            **📦 Mass Market Regular**
            - *Karakteristik:* Produk kebutuhan harian dengan perputaran stabil.
            - *Strategi:* Tawarkan program *repeat order* / langganan bulanan dan gratis ongkir minimal belanja.
            """)
            
        # Demographic profile from Worksheet 3
        if df_tx is not None and df_cust is not None:
            st.markdown("---")
            st.subheader("👥 Analisis Demografi Pembeli (Worksheet 3 Langkah 1 & 4)")
            demo_data = analytics.get_customer_demographic_analysis()
            
            c_d1, c_d2 = st.columns(2)
            with c_d1:
                fig_demo_age = px.bar(
                    demo_data["age_stats"],
                    x="Kelompok Usia",
                    y="Total Item Dibeli",
                    color="Kelompok Usia",
                    title="Volume Transaksi Berdasarkan Kelompok Usia Konsumen"
                )
                fig_demo_age.update_layout(showlegend=False)
                st.plotly_chart(fig_demo_age, use_container_width=True)
            with c_d2:
                fig_demo_gender = px.pie(
                    demo_data["gender_stats"],
                    names="Gender",
                    values="Total Item Dibeli",
                    hole=0.4,
                    title="Proporsi Pembeli Berdasarkan Jenis Kelamin"
                )
                st.plotly_chart(fig_demo_gender, use_container_width=True)
    else:
        st.warning("Data klaster belum dihitung. Jalankan `python src/ml_clustering.py`.")

# ----------------------------------------------------
# TAB 6: ARSITEKTUR BIG DATA
# ----------------------------------------------------
with tab6:
    st.subheader("🏛️ Rancangan Arsitektur Sistem Big Data (Lambda Architecture)")
    st.markdown("""
    Arsitektur ini didesain sesuai spesifikasi **Laporan Praktikum 2** dan **Worksheet Praktikum 3** mata kuliah **Teknologi Big Data**, menggabungkan **Speed Layer** dan **Batch Layer**.
    """)
    
    st.markdown("""
    ```
    ┌────────────────────────────────────────────────────────────────────────────────┐
    │                                1. DATA SOURCES                                 │
    │  • Streaming Data  : basket_details (Log Transaksi Pembelian Real-Time)        │
    │  • Batch Data      : customer_details (Demografi) & Scraping Katalog Tokopedia │
    └───────────────────────┬────────────────────────────────┬───────────────────────┘
                            │ (Real-Time Ingestion)          │ (Batch Ingestion)
                            ▼                                ▼
    ┌───────────────────────────────────┐    ┌───────────────────────────────────────┐
    │       2. INGESTION LAYER          │    │          3. STORAGE LAYER             │
    │  Apache Kafka                     │───>│  MongoDB NoSQL Database               │
    │  (Fault-tolerant Message Broker)  │    │  (Operational Data Lake & Catalog)    │
    └─────────────────┬─────────────────┘    └───────────────────┬───────────────────┘
                      │ (Stream)                                 │ (Batch Dataset)
                      ▼                                          ▼
    ┌────────────────────────────────────────────────────────────────────────────────┐
    │                       4. PROCESSING LAYER (APACHE SPARK)                       │
    │  ┌──────────────────────────────────┐  ┌────────────────────────────────────┐  │
    │  │           SPEED LAYER            │  │            BATCH LAYER             │  │
    │  │ • Spark Structured Streaming     │  │ • PySpark SQL Join & Agregasi      │  │
    │  │ • Monitoring lonjakan pesanan    │  │ • PySpark MLlib K-Means Clustering │  │
    │  └──────────────────────────────────┘  └────────────────────────────────────┘  │
    └───────────────────────────────────────┬────────────────────────────────────────┘
                                            │ Serving Views
                                            ▼
    ┌────────────────────────────────────────────────────────────────────────────────┐
    │                  5. SERVING & PRESENTATION LAYER (STREAMLIT)                   │
    │  • Interactive Dashboard Interaktif untuk Tim Bisnis, Marketing & Eksekutif    │
    │  • Visualisasi Pola Penjualan, Periode Puncak, dan Segmentasi Konsumen         │
    └────────────────────────────────────────────────────────────────────────────────┘
    ```
    """)
    
    st.markdown("#### Tabel Pemetaan Komponen Arsitektur:")
    tech_matrix = pd.DataFrame([
        {"Lapisan": "Data Source", "Teknologi": "CSV Flat Files / E-Commerce Log", "Peran": "Sumber data 29.519 produk Tokopedia, riwayat transaksi & profil pelanggan."},
        {"Lapisan": "Data Ingestion", "Teknologi": "Apache Kafka", "Peran": "Menyerap log stream keranjang belanja tanpa overload saat flash sale."},
        {"Lapisan": "Storage", "Teknologi": "MongoDB (NoSQL Document Store)", "Peran": "Penyimpanan data semi-terstruktur fleksibel dengan horizontal scalability."},
        {"Lapisan": "Processing", "Teknologi": "Apache Spark (PySpark)", "Peran": "Engine komputasi terdistribusi untuk data cleaning, SQL query agregasi & MLlib."},
        {"Lapisan": "Machine Learning", "Teknologi": "K-Means Clustering (PySpark MLlib)", "Peran": "Pengelompokan otomatis segmen produk dan pola konsumen."},
        {"Lapisan": "Visualization", "Teknologi": "Streamlit & Plotly", "Peran": "Penyajian dashboard analitik interaktif yang responsif dan user-friendly."}
    ])
    st.table(tech_matrix)
