import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import PROCESSED_DATA_PATH, TRANSACTIONS_DATA_PATH, CUSTOMERS_DATA_PATH

def run_spark_analysis():
    """
    Executes distributed Big Data processing and Spark SQL queries
    matching the specifications in Laporan Praktikum 2 & Worksheet 3.
    """
    try:
        from pyspark.sql import SparkSession
        from pyspark.sql import functions as F
    except ImportError:
        print("[SPARK PIPELINE] PySpark is not installed or Java path not found. Skipping Spark execution.")
        return False
        
    print("[SPARK PIPELINE] Initializing Apache Spark Session...")
    spark = SparkSession.builder \
        .appName("TokopediaBigDataAnalytics") \
        .master("local[*]") \
        .config("spark.driver.memory", "2g") \
        .getOrCreate()
        
    spark.sparkContext.setLogLevel("ERROR")
    print(f"[SPARK PIPELINE] Spark Version: {spark.version}")
    
    # 1. Load Processed Products Data into Spark DataFrame
    print(f"[SPARK PIPELINE] Reading dataset: {PROCESSED_DATA_PATH}")
    df_products = spark.read \
        .option("header", "true") \
        .option("inferSchema", "true") \
        .option("quote", "\"") \
        .option("escape", "\"") \
        .csv(str(PROCESSED_DATA_PATH))
        
    # Cast numerical columns safely to ensure robust types
    df_products = df_products \
        .withColumn("terjual_clean", F.col("terjual_clean").cast("long")) \
        .withColumn("Harga (IDR)", F.col("Harga (IDR)").cast("long")) \
        .withColumn("estimasi_gmv", F.col("estimasi_gmv").cast("double")) \
        .withColumn("Rating", F.col("Rating").cast("double")) \
        .withColumn("Diskon (%)", F.col("Diskon (%)").cast("double"))
        
    df_products.createOrReplaceTempView("tokopedia_products")
    
    # 2. Spark SQL: Top 10 Best Selling Products
    print("\n[SPARK SQL] Top 5 Best Selling Products:")
    top_5 = spark.sql("""
        SELECT product_id, `Nama Produk`, kategori, `Harga (IDR)`, terjual_clean, estimasi_gmv
        FROM tokopedia_products
        ORDER BY terjual_clean DESC
        LIMIT 5
    """)
    top_5.show(truncate=50)
    
    # 3. Spark SQL: Revenue & Volume per Kategori
    print("[SPARK SQL] Kategori Aggregasi (Volume & Omzet):")
    cat_agg = spark.sql("""
        SELECT 
            kategori,
            COUNT(product_id) as total_produk,
            SUM(terjual_clean) as total_volume_terjual,
            SUM(estimasi_gmv) as total_estimasi_gmv,
            ROUND(AVG(Rating), 2) as avg_rating,
            ROUND(AVG(`Diskon (%)`), 1) as avg_diskon
        FROM tokopedia_products
        GROUP BY kategori
        ORDER BY total_volume_terjual DESC
    """)
    cat_agg.show(truncate=False)
    
    # 4. Read Transactions & Customer Demographics (Lambda Batch Layer)
    if Path(TRANSACTIONS_DATA_PATH).exists() and Path(CUSTOMERS_DATA_PATH).exists():
        print("[SPARK PIPELINE] Loading Transaction & Customer Demographics...")
        df_tx = spark.read.csv(str(TRANSACTIONS_DATA_PATH), header=True, inferSchema=True)
        df_cust = spark.read.csv(str(CUSTOMERS_DATA_PATH), header=True, inferSchema=True)
        
        df_tx.createOrReplaceTempView("basket_details")
        df_cust.createOrReplaceTempView("customer_details")
        
        # Batch Layer JOIN: basket_details + customer_details
        print("[SPARK SQL] Batch Join: Transaksi berdasarkan Kelompok Umur & Gender:")
        cust_tx_analysis = spark.sql("""
            SELECT 
                c.sex,
                CASE 
                    WHEN c.customer_age < 25 THEN '18-24 (Gen Z)'
                    WHEN c.customer_age <= 35 THEN '25-35 (Millennial)'
                    WHEN c.customer_age <= 50 THEN '36-50 (Gen X)'
                    ELSE '> 50 (Boomers)'
                END as age_group,
                COUNT(b.product_id) as total_transaksi,
                SUM(b.basket_count) as total_item_terbeli
            FROM basket_details b
            JOIN customer_details c ON b.customer_id = c.customer_id
            GROUP BY c.sex, age_group
            ORDER BY total_item_terbeli DESC
        """)
        cust_tx_analysis.show(truncate=False)
        
    spark.stop()
    print("[SPARK PIPELINE] Spark processing finished successfully!")
    return True

if __name__ == "__main__":
    run_spark_analysis()
