# E-Commerce Big Data Analytics & Customer Intelligence System
**Mata Kuliah: Teknologi Big Data (Semester 5)**

Sistem analisis data skala besar (*Big Data Analytics Pipeline*) untuk menganalisis pola dan tren penjualan pada platform e-commerce (Tokopedia) berdasarkan data transaksi, katalog produk, dan profil pelanggan menggunakan **Arsitektur Lambda (Apache Kafka, MongoDB, Apache Spark, dan Streamlit)**.

---

## 📌 Ringkasan Proyek & Pemetaan Worksheet

Sistem ini dibangun untuk memenuhi seluruh spesifikasi pada **LAPORAN PRAKTIKUM 2** dan **WORKSHEET PRAKTIKUM 3**:

| Komponen Dokumen | Implementasi Sistem | File Kode |
| :--- | :--- | :--- |
| **Dataset** | 29.519 Produk Tokopedia + Log Transaksi (basket_details) + Profil Konsumen (customer_details) | `src/data_cleaner.py` |
| **Ingestion & Storage** | Apache Kafka (Event Streaming) & MongoDB (NoSQL Document Store / Data Lake) | `src/config.py`, `src/data_cleaner.py` |
| **Processing Layer** | Apache Spark (PySpark) – Data Cleaning, Parsing Regex, Spark SQL Aggregation | `src/spark_pipeline.py` |
| **Analisis Pertanyaan 1** | Identifikasi Produk Terlaris (*Top Selling Products*) & Estimasi Omzet (*GMV*) | `src/analytics_engine.py` (Tab 2) |
| **Analisis Pertanyaan 2** | Deteksi Periode / Waktu Puncak (*Peak Hours*, *Peak Days*, Tren Harian) | `src/analytics_engine.py` (Tab 3) |
| **Analisis Pertanyaan 3** | Pola Segmentasi Produk & Profil Demografi Pengguna (K-Means Clustering) | `src/ml_clustering.py` (Tab 5) |
| **Visualisasi / Output** | Interactive Web Dashboard berbasis Streamlit & Plotly | `dashboard/app.py` |

---

## 🏛️ Arsitektur Sistem (Lambda Architecture)

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                                1. DATA SOURCES                                 │
│  • Streaming Data  : basket_details (Log Transaksi Pembelian Real-Time)        │
│  • Batch Data      : customer_details (Demografi) & Katalog Produk Tokopedia   │
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

---

## 📂 Struktur Folder Proyek

```
d:\semester 5\Teknologi Big Data\projek\
├── dashboard/
│   └── app.py                      # Aplikasi Web Dashboard Interaktif Streamlit
├── data/
│   ├── processed_tokopedia.csv     # Data 29.519 produk bersih (terjual, rating, kategori)
│   ├── products_clustered.csv      # Hasil segmentasi K-Means Machine Learning
│   ├── transactions_simulated.csv  # Log transaksi keranjang (basket_details)
│   └── customers_simulated.csv     # Profil demografi pelanggan (customer_details)
├── src/
│   ├── __init__.py
│   ├── config.py                   # Konfigurasi path & koneksi database
│   ├── data_cleaner.py             # Script pembersihan data, parsing regex, ekstraksi NLP
│   ├── spark_pipeline.py           # Pipeline Apache Spark terdistribusi & Spark SQL
│   ├── ml_clustering.py            # Model K-Means Clustering (PySpark MLlib / Scikit)
│   └── analytics_engine.py         # Engine analitik bisnis & agregasi metrik
├── tokopedia/
│   └── produk_tokopedia.csv        # Dataset mentah scraping Tokopedia
├── requirements.txt                # Dependensi pustaka Python
├── run_pipeline.bat                # 1-Click script untuk menjalankan pipeline
├── run_dashboard.bat               # 1-Click script untuk membuka web dashboard
└── run_pipeline.py                 # Runner eksekusi end-to-end
```

---

## 🚀 Cara Menjalankan Sistem

### 1. Menjalankan Pipeline Big Data
Untuk memproses data mentah Tokopedia, mengeksekusi Spark SQL, dan melatih model K-Means:
- **Cara 1 (Windows Explorer):** Klik dua kali file `run_pipeline.bat`.
- **Cara 2 (Terminal):**
  ```powershell
  python run_pipeline.py
  ```

### 2. Membuka Dashboard Visualisasi Streamlit
Untuk melihat dashboard interaktif di browser web:
- **Cara 1 (Windows Explorer):** Klik dua kali file `run_dashboard.bat`.
- **Cara 2 (Terminal):**
  ```powershell
  streamlit run dashboard/app.py
  ```
Dashboard akan otomatis terbuka di browser pada alamat: `http://localhost:8501`.

---

## 📊 Fitur-Fitur Dashboard

1. **Ringkasan Pasar & KPI**:
   - Total Produk Terkatalog (29.519 produk).
   - Estimasi Total Unit Terjual (63+ Juta item).
   - Estimasi Nilai Transaksi / GMV (Rp 17+ Triliun).
   - Komposisi Kategori Produk & Distribusi Rentang Harga.
2. **Pola Produk & Toko Terlaris**:
   - Peringkat Top 10 Produk Penjualan Tertinggi.
   - Analisis Merchant / Toko Penguasa Pasar.
   - Filter Interaktif berdasarkan Kategori, Wilayah Kota, dan Harga.
3. **Analisis Waktu Transaksi (Peak Time Analysis)**:
   - Grafik Time-Series fluktuasi harian pesanan.
   - Deteksi *Peak Hours* (jam istirahat siang 12.00-13.00 & malam 19.00-21.00).
   - Pola belanja hari dalam seminggu (*Weekend vs Weekday*).
4. **Sebaran Geografis (Lokasi)**:
   - Pemetaan konsentrasi penjualan antarkota (Jabodetabek, Surabaya, Bandung, dll.).
   - Hubungan kerapatan toko dengan tingkat rating toko di setiap kota.
5. **Segmentasi K-Means (Machine Learning)**:
   - Visualisasi scatter klaster produk (Harga vs Terjual vs Rating).
   - 4 Klaster: *Star Products*, *Mass Market Regular*, *Promo Driven*, dan *Premium High-End*.
   - Rencana aksi bisnis (*marketing action plan*) untuk masing-masing klaster.
   - Demografi profil pembeli (Kelompok Usia & Gender).
6. **Arsitektur Big Data**:
   - Diagram alur data end-to-end Arsitektur Lambda.
