import io
import math
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
import uvicorn
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from src.config import (
    CLUSTERS_DATA_PATH,
    CUSTOMERS_DATA_PATH,
    PROCESSED_DATA_PATH,
    TRANSACTIONS_DATA_PATH,
)
from src.data_cleaner import (
    extract_category,
    normalize_location,
    parse_terjual,
    parse_ulasan,
)

WEB_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"
TEMPLATE_CSV_PATH = PROJECT_ROOT / "data" / "template_dataset_ecommerce.csv"

app = FastAPI(
    title="PASAR.DATA — E-Commerce Big Data Analytics",
    description="Custom FastAPI + ECharts Big Data Intelligence Platform",
    version="2.0.0",
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ==========================================
# SAFE SERIALIZATION HELPERS
# ==========================================
def safe_int(val, default: int = 0) -> int:
    try:
        if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
            return default
        if pd.isna(val):
            return default
        return int(round(float(val)))
    except Exception:
        return default


def safe_float(val, digits: int = 2, default: float = 0.0) -> float:
    try:
        if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
            return default
        if pd.isna(val):
            return default
        return round(float(val), digits)
    except Exception:
        return default


def safe_str(val, default: str = "") -> str:
    if val is None or pd.isna(val):
        return default
    return str(val).strip()


# ==========================================
# DATA PROCESSING & ON-THE-FLY PIPELINE
# ==========================================
def get_price_tier(price: int) -> str:
    if price < 25000:
        return "< Rp 25 Ribu (Budget)"
    elif price <= 100000:
        return "Rp 25k - 100k (Ekonomis)"
    elif price <= 500000:
        return "Rp 100k - 500k (Menengah)"
    elif price <= 2000000:
        return "Rp 500k - 2 Juta (Premium)"
    else:
        return "> Rp 2 Juta (Luxury/Investasi)"


def process_custom_dataset(uploaded_df: pd.DataFrame) -> pd.DataFrame:
    """Cleans, categorizes, and clusters any uploaded CSV dataset on-the-fly."""
    df = uploaded_df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    col_mapping = {
        "Nama": "Nama Produk",
        "Product Name": "Nama Produk",
        "produk": "Nama Produk",
        "Produk": "Nama Produk",
        "Toko": "Nama Toko",
        "Shop": "Nama Toko",
        "Merchant": "Nama Toko",
        "Lokasi": "Lokasi Toko",
        "Kota": "Lokasi Toko",
        "Location": "Lokasi Toko",
        "City": "Lokasi Toko",
        "Sold": "Terjual",
        "terjual": "Terjual",
        "Sales": "Terjual",
        "Ulasan": "Jumlah Ulasan",
        "Review": "Jumlah Ulasan",
        "Reviews": "Jumlah Ulasan",
        "Stars": "Rating",
        "Score": "Rating",
        "rating": "Rating",
        "Harga": "Harga (IDR)",
        "Price": "Harga (IDR)",
        "harga": "Harga (IDR)",
        "Price (IDR)": "Harga (IDR)",
        "Diskon": "Diskon (%)",
        "Discount": "Diskon (%)",
        "Discount (%)": "Diskon (%)",
        "URL": "Produk URL",
        "Link": "Produk URL",
        "url": "Produk URL",
    }
    for old_col, new_col in col_mapping.items():
        if old_col in df.columns and new_col not in df.columns:
            df.rename(columns={old_col: new_col}, inplace=True)

    if "Nama Produk" not in df.columns:
        raise ValueError("Kolom 'Nama Produk' wajib ada dalam file CSV.")
    if "Harga (IDR)" not in df.columns:
        raise ValueError("Kolom 'Harga (IDR)' wajib ada dalam file CSV.")

    if len(df) == 0:
        raise ValueError("File CSV tidak memiliki baris data.")

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

    df["Nama Produk"] = df["Nama Produk"].fillna("Produk Tanpa Nama").astype(str)
    df["Nama Toko"] = df["Nama Toko"].fillna("Official / Toko Mitra").astype(str)
    df["Lokasi Toko"] = df["Lokasi Toko"].fillna("Jakarta").astype(str)
    df["Produk URL"] = df["Produk URL"].fillna("https://www.tokopedia.com").astype(str)
    df["Rating"] = pd.to_numeric(df["Rating"], errors="coerce").fillna(0.0).clip(0.0, 5.0)
    df["Harga (IDR)"] = pd.to_numeric(df["Harga (IDR)"], errors="coerce").fillna(0).clip(lower=0).astype(int)
    df["Diskon (%)"] = pd.to_numeric(df["Diskon (%)"], errors="coerce").fillna(0.0).clip(0.0, 100.0)

    if "terjual_clean" not in df.columns:
        df["terjual_clean"] = df["Terjual"].apply(parse_terjual)
    else:
        df["terjual_clean"] = pd.to_numeric(df["terjual_clean"], errors="coerce").fillna(0).astype(int)

    if "ulasan_clean" not in df.columns:
        df["ulasan_clean"] = df["Jumlah Ulasan"].apply(parse_ulasan)
    else:
        df["ulasan_clean"] = pd.to_numeric(df["ulasan_clean"], errors="coerce").fillna(0).astype(int)

    if "kategori" not in df.columns:
        df["kategori"] = df["Nama Produk"].apply(extract_category)
    if "lokasi_clean" not in df.columns:
        df["lokasi_clean"] = df["Lokasi Toko"].apply(normalize_location)
    if "estimasi_gmv" not in df.columns:
        df["estimasi_gmv"] = df["Harga (IDR)"] * df["terjual_clean"]
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
            df_cluster["log_harga"] = np.log1p(df_cluster["Harga (IDR)"].clip(lower=0))
            df_cluster["log_terjual"] = np.log1p(df_cluster["terjual_clean"].clip(lower=0))
            df_cluster["log_ulasan"] = np.log1p(df_cluster["ulasan_clean"].clip(lower=0))

            X = df_cluster[["log_harga", "Diskon (%)", "Rating", "log_terjual", "log_ulasan"]].values
            X_scaled = StandardScaler().fit_transform(X)

            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            clusters = kmeans.fit_predict(X_scaled)
            df["cluster"] = clusters

            cluster_means = df.groupby("cluster")[
                ["Harga (IDR)", "terjual_clean", "Rating", "Diskon (%)", "ulasan_clean"]
            ].mean()
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


def generate_synthetic_tx_in_memory(df_prod: pd.DataFrame):
    """Generates matching synthetic transactions and demographics for uploaded datasets."""
    rng = np.random.default_rng(42)
    n_cust = min(500, max(50, len(df_prod) * 2))
    n_tx = min(3000, max(200, len(df_prod) * 5))

    cust_df = pd.DataFrame(
        {
            "customer_id": [f"CUST_{i+1:04d}" for i in range(n_cust)],
            "sex": rng.choice(["Male", "Female"], size=n_cust, p=[0.48, 0.52]),
            "customer_age": rng.integers(18, 65, size=n_cust),
            "tenure": rng.integers(1, 60, size=n_cust),
        }
    )

    prod_pool = df_prod["product_id"].tolist()
    sampled_cust = rng.choice(cust_df["customer_id"], size=n_tx)
    sampled_prod = rng.choice(prod_pool, size=n_tx)

    start_date = pd.Timestamp("2026-01-01")
    date_offsets = rng.integers(0, 180, size=n_tx)
    basket_dates = [start_date + pd.Timedelta(days=int(d)) for d in date_offsets]
    hours_pool = [8, 9, 10, 11, 12, 12, 13, 13, 14, 15, 16, 17, 18, 19, 20, 20, 21, 21, 22, 23]
    hours = rng.choice(hours_pool, size=n_tx)
    counts = rng.choice([1, 2, 3, 4, 5], size=n_tx, p=[0.65, 0.20, 0.08, 0.04, 0.03])

    tx_df = pd.DataFrame(
        {
            "customer_id": sampled_cust,
            "product_id": sampled_prod,
            "basket_date": [d.strftime("%Y-%m-%d") for d in basket_dates],
            "basket_hour": hours,
            "day_of_week": [d.strftime("%A") for d in basket_dates],
            "basket_count": counts,
        }
    )
    return tx_df, cust_df


# ==========================================
# IN-MEMORY DATA STORE
# ==========================================
class DataStore:
    def __init__(self):
        self.df_prod: pd.DataFrame = pd.DataFrame()
        self.df_tx: Optional[pd.DataFrame] = None
        self.df_cust: Optional[pd.DataFrame] = None
        self.source: str = "default"
        self.filename: str = "products_clustered.csv"
        self.load_default()

    def load_default(self):
        if Path(CLUSTERS_DATA_PATH).exists():
            self.df_prod = pd.read_csv(CLUSTERS_DATA_PATH)
            self.filename = Path(CLUSTERS_DATA_PATH).name
        elif Path(PROCESSED_DATA_PATH).exists():
            self.df_prod = pd.read_csv(PROCESSED_DATA_PATH)
            self.filename = Path(PROCESSED_DATA_PATH).name
        elif TEMPLATE_CSV_PATH.exists():
            raw = pd.read_csv(TEMPLATE_CSV_PATH)
            self.df_prod = process_custom_dataset(raw)
            self.filename = TEMPLATE_CSV_PATH.name
        else:
            raise RuntimeError("Dataset tidak ditemukan. Jalankan `python run_pipeline.py` terlebih dahulu.")

        # Guarantee clean numeric types
        self.df_prod["Harga (IDR)"] = pd.to_numeric(self.df_prod["Harga (IDR)"], errors="coerce").fillna(0).astype(int)
        self.df_prod["Rating"] = pd.to_numeric(self.df_prod["Rating"], errors="coerce").fillna(0.0)
        self.df_prod["Diskon (%)"] = pd.to_numeric(self.df_prod["Diskon (%)"], errors="coerce").fillna(0.0)
        self.df_prod["terjual_clean"] = pd.to_numeric(self.df_prod["terjual_clean"], errors="coerce").fillna(0).astype(int)
        self.df_prod["estimasi_gmv"] = pd.to_numeric(self.df_prod["estimasi_gmv"], errors="coerce").fillna(0).astype(int)
        if "Produk URL" not in self.df_prod.columns:
            self.df_prod["Produk URL"] = "https://www.tokopedia.com"

        self.df_tx = pd.read_csv(TRANSACTIONS_DATA_PATH) if Path(TRANSACTIONS_DATA_PATH).exists() else None
        self.df_cust = pd.read_csv(CUSTOMERS_DATA_PATH) if Path(CUSTOMERS_DATA_PATH).exists() else None
        self.source = "default"

    def set_custom(self, raw_df: pd.DataFrame, filename: str):
        processed = process_custom_dataset(raw_df)
        tx_df, cust_df = generate_synthetic_tx_in_memory(processed)
        self.df_prod = processed
        self.df_tx = tx_df
        self.df_cust = cust_df
        self.source = "custom"
        self.filename = filename

    def get_meta(self) -> dict:
        df = self.df_prod
        categories = sorted(df["kategori"].dropna().astype(str).unique().tolist())
        cities = df["lokasi_clean"].dropna().astype(str).value_counts().head(25).index.tolist()
        min_p = safe_int(df["Harga (IDR)"].min()) if len(df) > 0 else 0
        max_p = safe_int(df["Harga (IDR)"].max()) if len(df) > 0 else 1000000
        q98_p = safe_int(df["Harga (IDR)"].quantile(0.98)) if len(df) > 0 else max_p
        return {
            "source": self.source,
            "filename": self.filename,
            "total_rows": int(len(df)),
            "total_merchants": int(df["Nama Toko"].nunique()) if len(df) > 0 else 0,
            "categories": categories,
            "cities": cities,
            "price_bounds": {
                "min": min_p,
                "max": max(min_p + 1000, max_p),
                "q98": max(min_p + 1000, q98_p),
            },
            "has_clusters": "cluster_label" in df.columns,
            "has_transactions": self.df_tx is not None and len(self.df_tx) > 0,
        }


store = DataStore()


# ==========================================
# ROUTES
# ==========================================
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = TEMPLATES_DIR / "index.html"
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"))


@app.get("/api/meta")
async def get_meta():
    return store.get_meta()


@app.get("/api/template")
async def download_template():
    if not TEMPLATE_CSV_PATH.exists():
        raise HTTPException(status_code=404, detail="File template CSV tidak ditemukan.")
    return FileResponse(
        path=str(TEMPLATE_CSV_PATH),
        filename="template_dataset_ecommerce.csv",
        media_type="text/csv",
    )


@app.post("/api/upload")
async def upload_dataset(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Format file harus .csv")
    try:
        raw_bytes = await file.read()
        # Handle UTF-8 BOM or latin-1 fallback
        try:
            text_stream = io.StringIO(raw_bytes.decode("utf-8-sig"))
        except UnicodeDecodeError:
            text_stream = io.StringIO(raw_bytes.decode("latin-1"))

        raw_df = pd.read_csv(text_stream)
        store.set_custom(raw_df, file.filename)
        return {
            "status": "ok",
            "message": f"Berhasil memuat dan memproses {len(store.df_prod):,} produk dari {file.filename}",
            "meta": store.get_meta(),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Gagal memproses CSV: {exc}")


@app.post("/api/reset")
async def reset_dataset():
    store.load_default()
    return {
        "status": "ok",
        "message": "Dataset dikembalikan ke katalog bawaan Tokopedia.",
        "meta": store.get_meta(),
    }


@app.get("/api/dashboard")
async def get_dashboard_data(
    category: str = Query("ALL"),
    city: str = Query("ALL"),
    min_price: Optional[int] = Query(None),
    max_price: Optional[int] = Query(None),
    min_rating: float = Query(0.0),
    top_n: int = Query(15, ge=5, le=50),
    sort_by: str = Query("terjual_clean"),
    search: str = Query(""),
):
    df_all = store.df_prod
    df = df_all

    if category and category != "ALL":
        df = df[df["kategori"] == category]
    if city and city != "ALL":
        df = df[df["lokasi_clean"] == city]
    if min_price is not None:
        df = df[df["Harga (IDR)"] >= min_price]
    if max_price is not None:
        df = df[df["Harga (IDR)"] <= max_price]
    if min_rating > 0:
        df = df[df["Rating"] >= min_rating]

    total_products = int(len(df))
    total_raw = int(len(df_all))

    # 1. KPIs
    if total_products > 0:
        positive_ratings = df[df["Rating"] > 0]["Rating"]
        avg_rating = safe_float(positive_ratings.mean() if len(positive_ratings) > 0 else 0.0, 2)
        kpis = {
            "total_products": total_products,
            "total_catalog_raw": total_raw,
            "coverage_pct": safe_float((total_products / max(1, total_raw)) * 100, 1),
            "total_volume_sold": safe_int(df["terjual_clean"].sum()),
            "total_gmv": safe_int(df["estimasi_gmv"].sum()),
            "avg_rating": avg_rating,
            "avg_discount": safe_float(df["Diskon (%)"].mean(), 1),
            "total_merchants": int(df["Nama Toko"].nunique()),
            "total_cities": int(df["lokasi_clean"].nunique()),
            "avg_price": safe_int(df["Harga (IDR)"].mean()),
            "median_price": safe_int(df["Harga (IDR)"].median()),
        }
    else:
        kpis = {
            "total_products": 0,
            "total_catalog_raw": total_raw,
            "coverage_pct": 0.0,
            "total_volume_sold": 0,
            "total_gmv": 0,
            "avg_rating": 0.0,
            "avg_discount": 0.0,
            "total_merchants": 0,
            "total_cities": 0,
            "avg_price": 0,
            "median_price": 0,
        }

    # 2. Category Breakdown
    categories_out = []
    if total_products > 0:
        cat_stats = (
            df.groupby("kategori")
            .agg(
                total_produk=("product_id", "count"),
                total_terjual=("terjual_clean", "sum"),
                total_gmv=("estimasi_gmv", "sum"),
                avg_harga=("Harga (IDR)", "mean"),
                avg_rating=("Rating", "mean"),
                avg_diskon=("Diskon (%)", "mean"),
            )
            .reset_index()
            .sort_values(by="total_terjual", ascending=False)
        )
        for _, r in cat_stats.iterrows():
            categories_out.append(
                {
                    "kategori": safe_str(r["kategori"]),
                    "total_produk": safe_int(r["total_produk"]),
                    "total_terjual": safe_int(r["total_terjual"]),
                    "total_gmv": safe_int(r["total_gmv"]),
                    "avg_harga": safe_int(r["avg_harga"]),
                    "avg_rating": safe_float(r["avg_rating"], 2),
                    "avg_diskon": safe_float(r["avg_diskon"], 1),
                }
            )

    # 3. Price Tier Distribution
    tier_order = [
        "< Rp 25 Ribu (Budget)",
        "Rp 25k - 100k (Ekonomis)",
        "Rp 100k - 500k (Menengah)",
        "Rp 500k - 2 Juta (Premium)",
        "> Rp 2 Juta (Luxury/Investasi)",
    ]
    short_tier_labels = {
        "< Rp 25 Ribu (Budget)": "< 25rb",
        "Rp 25k - 100k (Ekonomis)": "25rb–100rb",
        "Rp 100k - 500k (Menengah)": "100rb–500rb",
        "Rp 500k - 2 Juta (Premium)": "500rb–2jt",
        "> Rp 2 Juta (Luxury/Investasi)": "> 2jt",
    }
    price_tiers_out = []
    if total_products > 0:
        tier_stats = (
            df.groupby("price_tier")
            .agg(
                total_produk=("product_id", "count"),
                total_terjual=("terjual_clean", "sum"),
                total_gmv=("estimasi_gmv", "sum"),
            )
            .reindex(tier_order)
            .fillna(0)
            .reset_index()
        )
        for _, r in tier_stats.iterrows():
            tier_name = safe_str(r["price_tier"])
            price_tiers_out.append(
                {
                    "price_tier": tier_name,
                    "short_label": short_tier_labels.get(tier_name, tier_name),
                    "total_produk": safe_int(r["total_produk"]),
                    "total_terjual": safe_int(r["total_terjual"]),
                    "total_gmv": safe_int(r["total_gmv"]),
                }
            )

    # 4. Top Products (with optional search & sort)
    valid_sorts = {"terjual_clean", "estimasi_gmv", "Harga (IDR)", "Rating"}
    sort_col = sort_by if sort_by in valid_sorts else "terjual_clean"

    df_prod_table = df
    if search.strip():
        q = search.strip().lower()
        mask = (
            df_prod_table["Nama Produk"].astype(str).str.lower().str.contains(q, regex=False)
            | df_prod_table["Nama Toko"].astype(str).str.lower().str.contains(q, regex=False)
            | df_prod_table["kategori"].astype(str).str.lower().str.contains(q, regex=False)
        )
        df_prod_table = df_prod_table[mask]

    top_products_out = []
    if len(df_prod_table) > 0:
        top_df = df_prod_table.sort_values(by=[sort_col, "terjual_clean"], ascending=False).head(top_n)
        for _, r in top_df.iterrows():
            top_products_out.append(
                {
                    "product_id": safe_str(r.get("product_id")),
                    "nama_produk": safe_str(r.get("Nama Produk")),
                    "kategori": safe_str(r.get("kategori")),
                    "nama_toko": safe_str(r.get("Nama Toko")),
                    "lokasi": safe_str(r.get("lokasi_clean")),
                    "harga": safe_int(r.get("Harga (IDR)")),
                    "diskon": safe_float(r.get("Diskon (%)"), 1),
                    "rating": safe_float(r.get("Rating"), 1),
                    "terjual": safe_int(r.get("terjual_clean")),
                    "gmv": safe_int(r.get("estimasi_gmv")),
                    "url": safe_str(r.get("Produk URL"), "https://www.tokopedia.com"),
                    "cluster": safe_str(r.get("cluster_label"), "-"),
                }
            )

    # 5. Top Merchants
    top_shops_out = []
    if total_products > 0:
        shops = (
            df.groupby("Nama Toko")
            .agg(
                total_produk=("product_id", "count"),
                total_terjual=("terjual_clean", "sum"),
                total_gmv=("estimasi_gmv", "sum"),
                avg_rating=("Rating", "mean"),
                lokasi=("lokasi_clean", "first"),
            )
            .sort_values(by="total_terjual", ascending=False)
            .head(10)
            .reset_index()
        )
        for _, r in shops.iterrows():
            top_shops_out.append(
                {
                    "nama_toko": safe_str(r["Nama Toko"]),
                    "lokasi": safe_str(r["lokasi"]),
                    "total_produk": safe_int(r["total_produk"]),
                    "total_terjual": safe_int(r["total_terjual"]),
                    "total_gmv": safe_int(r["total_gmv"]),
                    "avg_rating": safe_float(r["avg_rating"], 2),
                }
            )

    # 6. Locations / Geographic Distribution
    locations_out = []
    geo_summary = {"jabodetabek_share_pct": 0.0, "top_city": "-", "top_city_volume": 0}
    if total_products > 0:
        loc_all = (
            df.groupby("lokasi_clean")
            .agg(
                total_produk=("product_id", "count"),
                total_terjual=("terjual_clean", "sum"),
                total_gmv=("estimasi_gmv", "sum"),
                avg_rating=("Rating", "mean"),
            )
            .reset_index()
            .sort_values(by="total_terjual", ascending=False)
        )
        total_vol = max(1, safe_int(loc_all["total_terjual"].sum()))
        jabo_keywords = ["jakarta", "tangerang", "bekasi", "bogor", "depok"]
        jabo_mask = loc_all["lokasi_clean"].astype(str).str.lower().apply(
            lambda x: any(k in x for k in jabo_keywords)
        )
        jabo_vol = safe_int(loc_all[jabo_mask]["total_terjual"].sum())
        geo_summary = {
            "jabodetabek_share_pct": safe_float((jabo_vol / total_vol) * 100, 1),
            "non_jabo_share_pct": safe_float(((total_vol - jabo_vol) / total_vol) * 100, 1),
            "top_city": safe_str(loc_all.iloc[0]["lokasi_clean"]) if len(loc_all) > 0 else "-",
            "top_city_volume": safe_int(loc_all.iloc[0]["total_terjual"]) if len(loc_all) > 0 else 0,
        }

        for _, r in loc_all.head(15).iterrows():
            locations_out.append(
                {
                    "lokasi": safe_str(r["lokasi_clean"]),
                    "total_produk": safe_int(r["total_produk"]),
                    "total_terjual": safe_int(r["total_terjual"]),
                    "total_gmv": safe_int(r["total_gmv"]),
                    "avg_rating": safe_float(r["avg_rating"], 2),
                }
            )

    # 7. Time Trends (from transactions)
    time_trends_out = {
        "daily": [],
        "hourly": [],
        "day_of_week": [],
        "peak_hour": 20,
        "peak_hour_count": 0,
        "peak_day": "Sabtu",
        "peak_date": "-",
        "peak_date_count": 0,
        "total_transactions": 0,
    }
    if store.df_tx is not None and len(store.df_tx) > 0:
        tx = store.df_tx
        time_trends_out["total_transactions"] = int(len(tx))

        daily = tx.groupby("basket_date")["basket_count"].sum().reset_index()
        daily = daily.sort_values("basket_date")
        time_trends_out["daily"] = [
            {"date": safe_str(r["basket_date"]), "count": safe_int(r["basket_count"])}
            for _, r in daily.iterrows()
        ]
        if len(daily) > 0:
            peak_d = daily.loc[daily["basket_count"].idxmax()]
            time_trends_out["peak_date"] = safe_str(peak_d["basket_date"])
            time_trends_out["peak_date_count"] = safe_int(peak_d["basket_count"])

        hourly = tx.groupby("basket_hour")["basket_count"].sum().reset_index().sort_values("basket_hour")
        time_trends_out["hourly"] = [
            {"hour": safe_int(r["basket_hour"]), "count": safe_int(r["basket_count"])}
            for _, r in hourly.iterrows()
        ]
        if len(hourly) > 0:
            peak_h = hourly.loc[hourly["basket_count"].idxmax()]
            time_trends_out["peak_hour"] = safe_int(peak_h["basket_hour"])
            time_trends_out["peak_hour_count"] = safe_int(peak_h["basket_count"])

        dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        dow_id_map = {
            "Monday": "Senin",
            "Tuesday": "Selasa",
            "Wednesday": "Rabu",
            "Thursday": "Kamis",
            "Friday": "Jumat",
            "Saturday": "Sabtu",
            "Sunday": "Minggu",
        }
        dow = tx.groupby("day_of_week")["basket_count"].sum().reindex(dow_order).fillna(0).reset_index()
        time_trends_out["day_of_week"] = [
            {
                "day": safe_str(r["day_of_week"]),
                "day_id": dow_id_map.get(safe_str(r["day_of_week"]), safe_str(r["day_of_week"])),
                "count": safe_int(r["basket_count"]),
            }
            for _, r in dow.iterrows()
        ]
        if len(dow) > 0:
            peak_w = dow.loc[dow["basket_count"].idxmax()]
            time_trends_out["peak_day"] = dow_id_map.get(safe_str(peak_w["day_of_week"]), "-")

    # 8. K-Means Clusters
    clusters_summary = []
    clusters_scatter = []
    if total_products > 0 and "cluster_label" in df.columns:
        csum = (
            df.groupby("cluster_label")
            .agg(
                jumlah_produk=("product_id", "count"),
                rata_harga=("Harga (IDR)", "mean"),
                rata_terjual=("terjual_clean", "mean"),
                rata_rating=("Rating", "mean"),
                rata_diskon=("Diskon (%)", "mean"),
                total_gmv=("estimasi_gmv", "sum"),
            )
            .reset_index()
            .sort_values(by="jumlah_produk", ascending=False)
        )
        for _, r in csum.iterrows():
            clusters_summary.append(
                {
                    "cluster_label": safe_str(r["cluster_label"]),
                    "jumlah_produk": safe_int(r["jumlah_produk"]),
                    "share_pct": safe_float((safe_int(r["jumlah_produk"]) / total_products) * 100, 1),
                    "rata_harga": safe_int(r["rata_harga"]),
                    "rata_terjual": safe_int(r["rata_terjual"]),
                    "rata_rating": safe_float(r["rata_rating"], 2),
                    "rata_diskon": safe_float(r["rata_diskon"], 1),
                    "total_gmv": safe_int(r["total_gmv"]),
                }
            )

        # Sample points with positive values for crisp log-log scatter
        valid_scatter = df[(df["Harga (IDR)"] > 0) & (df["terjual_clean"] > 0)]
        sample_df = valid_scatter.sample(min(1200, len(valid_scatter)), random_state=42) if len(valid_scatter) > 0 else valid_scatter
        for _, r in sample_df.iterrows():
            clusters_scatter.append(
                {
                    "harga": safe_int(r["Harga (IDR)"]),
                    "terjual": safe_int(r["terjual_clean"]),
                    "rating": safe_float(r["Rating"], 1),
                    "nama": safe_str(r["Nama Produk"])[:70],
                    "toko": safe_str(r["Nama Toko"])[:40],
                    "cluster": safe_str(r["cluster_label"]),
                }
            )

    # 9. Customer Demographics
    demographics_out = {"age_stats": [], "gender_stats": []}
    if store.df_tx is not None and store.df_cust is not None and len(store.df_tx) > 0:
        merged = store.df_tx.merge(store.df_cust, on="customer_id", how="left")
        g_stats = merged.groupby("sex")["basket_count"].agg(["count", "sum"]).reset_index()
        gender_id_map = {"Male": "Laki-laki", "Female": "Perempuan"}
        demographics_out["gender_stats"] = [
            {
                "gender": gender_id_map.get(safe_str(r["sex"]), safe_str(r["sex"])),
                "transactions": safe_int(r["count"]),
                "items": safe_int(r["sum"]),
            }
            for _, r in g_stats.iterrows()
        ]

        def get_age_group(age):
            if pd.isna(age):
                return "25-35 (Millennial)"
            if age < 25:
                return "18-24 (Gen Z)"
            elif age <= 35:
                return "25-35 (Millennial)"
            elif age <= 50:
                return "36-50 (Gen X)"
            else:
                return "> 50 (Boomers)"

        merged["age_group"] = merged["customer_age"].apply(get_age_group)
        age_order = ["18-24 (Gen Z)", "25-35 (Millennial)", "36-50 (Gen X)", "> 50 (Boomers)"]
        a_stats = merged.groupby("age_group")["basket_count"].sum().reindex(age_order).fillna(0).reset_index()
        demographics_out["age_stats"] = [
            {"group": safe_str(r["age_group"]), "items": safe_int(r["basket_count"])}
            for _, r in a_stats.iterrows()
        ]

    return {
        "meta": store.get_meta(),
        "kpis": kpis,
        "categories": categories_out,
        "price_tiers": price_tiers_out,
        "top_products": top_products_out,
        "top_products_total_match": int(len(df_prod_table)),
        "top_shops": top_shops_out,
        "locations": locations_out,
        "geo_summary": geo_summary,
        "time_trends": time_trends_out,
        "clusters": {
            "summary": clusters_summary,
            "scatter": clusters_scatter,
        },
        "demographics": demographics_out,
    }


if __name__ == "__main__":
    print("=" * 64)
    print("  PASAR.DATA — Custom E-Commerce Big Data Analytics Dashboard")
    print("  Buka di Browser: http://localhost:8000")
    print("=" * 64)
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
