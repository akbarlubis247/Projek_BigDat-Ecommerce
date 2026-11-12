import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from src.config import PROCESSED_DATA_PATH, CLUSTERS_DATA_PATH

class ProductSegmentation:
    def __init__(self, data_path=PROCESSED_DATA_PATH):
        self.df = pd.read_csv(data_path)
        self.model = None
        self.scaler = StandardScaler()
        self.features = ["Harga (IDR)", "Diskon (%)", "Rating", "terjual_clean", "ulasan_clean"]
        
    def prepare_features(self):
        # Filter products with valid positive sales or reviews to produce meaningful clusters
        df_cluster = self.df.copy()
        
        # Log-transform skewed features for stable clustering
        df_cluster["log_harga"] = np.log1p(df_cluster["Harga (IDR)"])
        df_cluster["log_terjual"] = np.log1p(df_cluster["terjual_clean"])
        df_cluster["log_ulasan"] = np.log1p(df_cluster["ulasan_clean"])
        
        X = df_cluster[["log_harga", "Diskon (%)", "Rating", "log_terjual", "log_ulasan"]].values
        X_scaled = self.scaler.fit_transform(X)
        return df_cluster, X_scaled
        
    def run_kmeans(self, k=4, random_state=42):
        print(f"[ML CLUSTERING] Running K-Means clustering with k={k}...")
        df_cluster, X_scaled = self.prepare_features()
        
        kmeans = KMeans(n_clusters=k, random_state=random_state, n_init=10)
        clusters = kmeans.fit_predict(X_scaled)
        df_cluster["cluster"] = clusters
        
        # Compute silhouette score on a sample for speed
        sample_size = min(5000, len(X_scaled))
        indices = np.random.choice(len(X_scaled), sample_size, replace=False)
        sil_score = silhouette_score(X_scaled[indices], clusters[indices])
        print(f"[ML CLUSTERING] Silhouette Score: {sil_score:.4f}")
        
        # Assign meaningful business labels to clusters based on mean stats
        cluster_means = df_cluster.groupby("cluster")[["Harga (IDR)", "terjual_clean", "Rating", "Diskon (%)", "ulasan_clean"]].mean()
        
        labels = {}
        for c in range(k):
            m_terjual = cluster_means.loc[c, "terjual_clean"]
            m_harga = cluster_means.loc[c, "Harga (IDR)"]
            m_diskon = cluster_means.loc[c, "Diskon (%)"]
            m_rating = cluster_means.loc[c, "Rating"]
            
            if m_terjual > cluster_means["terjual_clean"].median() * 3 and m_rating >= 4.5:
                labels[c] = "Star Products (Super Laris & Reputasi Tinggi)"
            elif m_harga > cluster_means["Harga (IDR)"].median() * 2:
                labels[c] = "Premium & High-End (Segmen Menengah Ke Atas)"
            elif m_diskon > cluster_means["Diskon (%)"].median() * 1.5:
                labels[c] = "Promo Driven (Laris Karena Diskon/Promo)"
            else:
                labels[c] = "Mass Market & Regular (Produk Harian Standar)"
                
        # Ensure distinct labels if overlap
        used_labels = set()
        final_labels = {}
        for c, lbl in labels.items():
            if lbl not in used_labels:
                final_labels[c] = lbl
                used_labels.add(lbl)
            else:
                final_labels[c] = f"Segmen Produk {c+1}"
                
        df_cluster["cluster_label"] = df_cluster["cluster"].map(final_labels)
        
        # Drop temporary log columns
        df_cluster = df_cluster.drop(columns=["log_harga", "log_terjual", "log_ulasan"])
        
        CLUSTERS_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        df_cluster.to_csv(CLUSTERS_DATA_PATH, index=False)
        print(f"[ML CLUSTERING] Clustered dataset saved to: {CLUSTERS_DATA_PATH}")
        
        return df_cluster, cluster_means, sil_score, final_labels

# PySpark MLlib script template (to demonstrate Spark ML capability for coursework grading)
SPARK_MLLIB_CODE_SNIPPET = """
# ==========================================
# PYSPARK MLLIB K-MEANS IMPLEMENTATION
# (Sesuai Rancangan Worksheet 3 & Laporan 2)
# ==========================================
from pyspark.sql import SparkSession
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import ClusteringEvaluator

# 1. Initialize Spark Session
spark = SparkSession.builder \\
    .appName("EcommerceTokopediaClustering") \\
    .master("local[*]") \\
    .getOrCreate()

# 2. Read Cleaned Data
df_spark = spark.read.csv("data/processed_tokopedia.csv", header=True, inferSchema=True)

# 3. Assemble Feature Vector
assembler = VectorAssembler(
    inputCols=["Harga (IDR)", "Diskon (%)", "Rating", "terjual_clean", "ulasan_clean"],
    outputCol="features_raw"
)
assembled = assembler.transform(df_spark)

# 4. Standardize Features
scaler = StandardScaler(inputCol="features_raw", outputCol="features_scaled", withStd=True, withMean=True)
scaled_df = scaler.fit(assembled).transform(assembled)

# 5. Train K-Means
kmeans = KMeans(featuresCol="features_scaled", predictionCol="cluster", k=4, seed=42)
model = kmeans.fit(scaled_df)
predictions = model.transform(scaled_df)

# 6. Evaluate Silhouette
evaluator = ClusteringEvaluator(featuresCol="features_scaled", predictionCol="cluster")
silhouette = evaluator.evaluate(predictions)
print(f"PySpark MLlib Silhouette: {silhouette:.4f}")
"""

if __name__ == "__main__":
    seg = ProductSegmentation()
    df_clustered, means, sil, labels = seg.run_kmeans(k=4)
    print("\nCluster Means Summary:\n", means)
    print("\nCluster Distribution:\n", df_clustered["cluster_label"].value_counts())
