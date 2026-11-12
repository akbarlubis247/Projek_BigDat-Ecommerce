import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np
from src.config import PROCESSED_DATA_PATH, TRANSACTIONS_DATA_PATH, CUSTOMERS_DATA_PATH

class EcommerceAnalytics:
    def __init__(self, products_df=None, transactions_df=None, customers_df=None):
        if products_df is not None:
            self.products = products_df
        else:
            self.products = pd.read_csv(PROCESSED_DATA_PATH)
            
        if transactions_df is not None:
            self.transactions = transactions_df
        else:
            self.transactions = pd.read_csv(TRANSACTIONS_DATA_PATH)
            
        if customers_df is not None:
            self.customers = customers_df
        else:
            self.customers = pd.read_csv(CUSTOMERS_DATA_PATH)
            
    def get_kpi_summary(self):
        total_products = len(self.products)
        total_volume_sold = int(self.products["terjual_clean"].sum())
        total_gmv = int(self.products["estimasi_gmv"].sum())
        avg_rating = round(self.products[self.products["Rating"] > 0]["Rating"].mean(), 2)
        avg_discount = round(self.products["Diskon (%)"].mean(), 1)
        total_merchants = self.products["Nama Toko"].nunique()
        total_cities = self.products["lokasi_clean"].nunique()
        
        return {
            "total_products": total_products,
            "total_volume_sold": total_volume_sold,
            "total_gmv": total_gmv,
            "avg_rating": avg_rating,
            "avg_discount": avg_discount,
            "total_merchants": total_merchants,
            "total_cities": total_cities
        }
        
    def get_top_products(self, n=10, by="terjual_clean", category=None):
        df = self.products.copy()
        if category and category != "Semua Kategori":
            df = df[df["kategori"] == category]
            
        cols = ["product_id", "Nama Produk", "kategori", "Nama Toko", "lokasi_clean", 
                "Harga (IDR)", "Diskon (%)", "Rating", "terjual_clean", "estimasi_gmv"]
        return df.sort_values(by=by, ascending=False)[cols].head(n)
        
    def get_category_breakdown(self):
        cat_stats = self.products.groupby("kategori").agg(
            total_produk=("product_id", "count"),
            total_terjual=("terjual_clean", "sum"),
            total_gmv=("estimasi_gmv", "sum"),
            avg_harga=("Harga (IDR)", "mean"),
            avg_rating=("Rating", "mean"),
            avg_diskon=("Diskon (%)", "mean")
        ).reset_index()
        return cat_stats.sort_values(by="total_terjual", ascending=False)
        
    def get_location_distribution(self, top_n=12):
        loc_stats = self.products.groupby("lokasi_clean").agg(
            total_produk=("product_id", "count"),
            total_terjual=("terjual_clean", "sum"),
            total_gmv=("estimasi_gmv", "sum"),
            avg_rating=("Rating", "mean")
        ).reset_index()
        return loc_stats.sort_values(by="total_terjual", ascending=False).head(top_n)
        
    def get_price_tier_distribution(self):
        order = [
            "< Rp 25 Ribu (Budget)",
            "Rp 25k - 100k (Ekonomis)",
            "Rp 100k - 500k (Menengah)",
            "Rp 500k - 2 Juta (Premium)",
            "> Rp 2 Juta (Luxury/Investasi)"
        ]
        tier_stats = self.products.groupby("price_tier").agg(
            total_produk=("product_id", "count"),
            total_terjual=("terjual_clean", "sum"),
            total_gmv=("estimasi_gmv", "sum")
        ).reindex(order).reset_index()
        return tier_stats
        
    def get_time_trend_analysis(self):
        """
        Answers Worksheet 3 Table 5 Question 2:
        Pada tanggal berapa / waktu apa lonjakan transaksi tertinggi terjadi?
        """
        # Daily trend
        daily = self.transactions.groupby("basket_date")["basket_count"].sum().reset_index()
        daily.columns = ["Tanggal", "Total Item Transaksi"]
        daily["Tanggal"] = pd.to_datetime(daily["Tanggal"])
        daily = daily.sort_values("Tanggal")
        
        # Peak Hours
        hourly = self.transactions.groupby("basket_hour")["basket_count"].sum().reset_index()
        hourly.columns = ["Jam", "Total Item Transaksi"]
        hourly = hourly.sort_values("Jam")
        
        # Day of week
        dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        dow = self.transactions.groupby("day_of_week")["basket_count"].sum().reindex(dow_order).reset_index()
        dow.columns = ["Hari", "Total Item Transaksi"]
        
        return {
            "daily_trend": daily,
            "peak_hours": hourly,
            "day_of_week": dow
        }
        
    def get_customer_demographic_analysis(self):
        """
        Answers Worksheet 3 Table 5 Question 3:
        Karakteristik demografi pelanggan (Umur, Gender, Tenure).
        """
        merged = self.transactions.merge(self.customers, on="customer_id", how="left")
        
        gender_stats = merged.groupby("sex")["basket_count"].agg(["count", "sum"]).reset_index()
        gender_stats.columns = ["Gender", "Frekuensi Transaksi", "Total Item Dibeli"]
        
        # Age brackets
        def get_age_group(age):
            if age < 25: return "18-24 (Gen Z)"
            elif age <= 35: return "25-35 (Millennial)"
            elif age <= 50: return "36-50 (Gen X)"
            else: return "> 50 (Boomers)"
            
        merged["age_group"] = merged["customer_age"].apply(get_age_group)
        age_order = ["18-24 (Gen Z)", "25-35 (Millennial)", "36-50 (Gen X)", "> 50 (Boomers)"]
        age_stats = merged.groupby("age_group")["basket_count"].sum().reindex(age_order).reset_index()
        age_stats.columns = ["Kelompok Usia", "Total Item Dibeli"]
        
        return {
            "gender_stats": gender_stats,
            "age_stats": age_stats,
            "merged_sample": merged.head(100)
        }

if __name__ == "__main__":
    analytics = EcommerceAnalytics()
    kpi = analytics.get_kpi_summary()
    print("KPI Summary:", kpi)
    print("\nTop 5 Products:\n", analytics.get_top_products(5))
    print("\nCategory Breakdown:\n", analytics.get_category_breakdown().head())
