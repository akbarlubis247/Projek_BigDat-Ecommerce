import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_cleaner import clean_tokopedia_data, generate_transactions_and_customers
from src.ml_clustering import ProductSegmentation
from src.analytics_engine import EcommerceAnalytics

def main():
    print("=" * 70)
    print("   END-TO-END BIG DATA PIPELINE - E-COMMERCE TOKOPEDIA")
    print("   Teknologi Big Data - Sistem Pemantauan Tren & Segmentasi")
    print("=" * 70)
    start_time = time.time()
    
    # Step 1: Cleaning & Ingestion
    print("\n>>> TAHAP 1: DATA INGESTION, PARSING & ENRICHMENT")
    clean_df = clean_tokopedia_data()
    df_cust, df_tx = generate_transactions_and_customers(clean_df)
    
    # Step 2: Spark Processing (if available)
    print("\n>>> TAHAP 2: DISTRIBUTED PROCESSING (APACHE SPARK)")
    try:
        from src.spark_pipeline import run_spark_analysis
        run_spark_analysis()
    except Exception as e:
        print(f"[SPARK NOTICE] Spark execution skipped or fallback used: {e}")
        
    # Step 3: Machine Learning Clustering (K-Means)
    print("\n>>> TAHAP 3: ADVANCED ANALYTICS & MACHINE LEARNING (K-MEANS)")
    seg = ProductSegmentation()
    df_clustered, means, sil, labels = seg.run_kmeans(k=4)
    print(f"Hasil Evaluasi Clustering Silhouette: {sil:.4f}")
    
    # Step 4: Generate Analytics Metrics
    print("\n>>> TAHAP 4: GENERATING ANALYTICS & BUSINESS INSIGHTS")
    analytics = EcommerceAnalytics(products_df=df_clustered, transactions_df=df_tx, customers_df=df_cust)
    kpis = analytics.get_kpi_summary()
    print("Ringkasan Metrik Bisnis:")
    print(f" - Total Produk Terkatalog  : {kpis['total_products']:,}")
    print(f" - Total Estimasi Unit Terjual : {kpis['total_volume_sold']:,} item")
    print(f" - Total Estimasi GMV          : Rp {kpis['total_gmv']:,}")
    print(f" - Rata-rata Rating Produk    : {kpis['avg_rating']} / 5.0")
    print(f" - Rata-rata Diskon           : {kpis['avg_discount']}%")
    print(f" - Jumlah Merchant / Toko     : {kpis['total_merchants']:,}")
    print(f" - Cakupan Kota / Wilayah     : {kpis['total_cities']}")
    
    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print(f" PIPELINE SELESAI DALAM {elapsed:.2f} DETIK!")
    print(" Data siap disajikan ke Dashboard Interaktif Streamlit.")
    print(" Untuk menjalankan Dashboard, ketik: streamlit run dashboard/app.py")
    print("=" * 70)

if __name__ == "__main__":
    main()
