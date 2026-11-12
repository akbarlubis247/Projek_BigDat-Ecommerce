import re
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
from src.config import RAW_DATA_PATH, PROCESSED_DATA_PATH, TRANSACTIONS_DATA_PATH, CUSTOMERS_DATA_PATH

def parse_terjual(val):
    if pd.isna(val):
        return 0
    s = str(val).lower().replace("terjual", "").replace("+", "").strip()
    s = s.replace(",", ".")
    if "rb" in s:
        s = s.replace("rb", "").strip()
        try:
            return int(float(s) * 1000)
        except Exception:
            return 0
    elif "jt" in s:
        s = s.replace("jt", "").strip()
        try:
            return int(float(s) * 1000000)
        except Exception:
            return 0
    else:
        try:
            return int(float(s))
        except Exception:
            return 0

def parse_ulasan(val):
    if pd.isna(val):
        return 0
    s = str(val).lower().replace("ulasan", "").replace("+", "").replace(".", "").replace(",", "").strip()
    if "rb" in s:
        s = s.replace("rb", "").strip()
        try:
            return int(float(s) * 1000)
        except Exception:
            return 0
    try:
        return int(float(s))
    except Exception:
        return 0

def extract_category(title):
    if not isinstance(title, str):
        return "Lainnya"
    t = title.lower()
    
    if any(k in t for k in ["dog food", "cat food", "kucing", "anjing", "pakan", "pet food", "raw food", "whiskas", "royal canin", "proplan", "pasir kucing", "aquarium", "ikan"]):
        return "Hewan Peliharaan"
    elif any(k in t for k in ["skintific", "serum", "moisturizer", "toner", "facial", "sunscreen", "skincare", "shampoo", "sabun", "parfum", "lip", "bedak", "masker wajah", "lotion", "originote", "kosmetik", "eyelash", "lipstick"]):
        return "Kecantikan & Perawatan"
    elif any(k in t for k in ["kaos", "baju", "kemeja", "celana", "jaket", "hoodie", "gamis", "hijab", "sepatu", "sandal", "tas", "dompet", "dress", "sorban", "sajadah", "jersey", "combed", "pakaian", "outfit"]):
        return "Fashion & Pakaian"
    elif any(k in t for k in ["dimsum", "sosis", "daging", "kopi", "teh", "snack", "biskuit", "cokelat", "mie", "sambal", "keripik", "beras", "minuman", "makanan", "bumbu", "keju", "susu", "sayur", "buah"]):
        return "Makanan & Minuman"
    elif any(k in t for k in ["panci", "wajan", "sendok", "garpu", "piring", "lemari", "meja", "kursi", "kasur", "sprei", "bantal", "sapu", "wadah", "gelas", "botol", "kotak", "rak", "dapur", "pisau"]):
        return "Perlengkapan Rumah & Dapur"
    elif any(k in t for k in ["lampu", "kabel", "charger", "hp", "case", "earphone", "headset", "tws", "speaker", "baterai", "led", "keyboard", "mouse", "powerbank", "elektronik", "usb", "laptop"]):
        return "Elektronik & Gadget"
    elif any(k in t for k in ["joyko", "kenko", "pulpen", "pensil", "kertas", "buku", "map", "spidol", "binder", "lakban", "stiker", "alat tulis", "nomor"]):
        return "Alat Tulis & Kantor"
    elif any(k in t for k in ["emas", "logam mulia", "galeri 24", 'antam', 'perhiasan']):
        return "Logam Mulia & Investasi"
    elif any(k in t for k in ["motor", "mobil", "oli", "ban", "helm", "sepeda", "bola", "poster", "mainan", "figure", "one piece", "bounty", "koleksi"]):
        return "Hobi, Olahraga & Otomotif"
    else:
        return "Kebutuhan Harian & Lainnya"

def normalize_location(loc):
    if pd.isna(loc) or not str(loc).strip():
        return "Jakarta"
    s = str(loc).strip()
    s_low = s.lower()
    
    if "jakarta" in s_low:
        if "barat" in s_low: return "Jakarta Barat"
        if "selatan" in s_low: return "Jakarta Selatan"
        if "pusat" in s_low: return "Jakarta Pusat"
        if "utara" in s_low: return "Jakarta Utara"
        if "timur" in s_low: return "Jakarta Timur"
        return "DKI Jakarta"
    elif "tangerang" in s_low:
        return "Tangerang"
    elif "bandung" in s_low:
        return "Bandung"
    elif "surabaya" in s_low:
        return "Surabaya"
    elif "semarang" in s_low:
        return "Semarang"
    elif "bekasi" in s_low:
        return "Bekasi"
    elif "depok" in s_low:
        return "Depok"
    elif "bogor" in s_low:
        return "Bogor"
    elif "medan" in s_low:
        return "Medan"
    elif "yogyakarta" in s_low or "jogja" in s_low:
        return "Yogyakarta"
    elif "malang" in s_low:
        return "Malang"
    elif "indonesia" in s_low:
        return "Nasional / Indonesia"
    else:
        return s.title()

def clean_tokopedia_data(input_path=RAW_DATA_PATH, output_path=PROCESSED_DATA_PATH):
    print(f"[DATA CLEANER] Loading raw data from: {input_path}")
    df = pd.read_csv(input_path)
    
    # Strip whitespace from column names
    df.columns = [c.strip() for c in df.columns]
    
    # Sanitize strings to prevent CSV misalignment across distributed parsers (Spark/Hadoop)
    for str_col in ["Nama Produk", "Nama Toko", "Lokasi Toko", "Produk URL"]:
        if str_col in df.columns:
            df[str_col] = df[str_col].astype(str).str.replace('"', "'").str.replace("\n", " ").str.replace("\r", " ").str.strip()
    
    # Generate structured product_id
    df["product_id"] = [f"PROD_{i+1:05d}" for i in range(len(df))]
    
    # Fill missing basic columns
    df["Nama Toko"] = df["Nama Toko"].fillna("Official/Verified Seller")
    df["Lokasi Toko"] = df["Lokasi Toko"].fillna("Jakarta")
    df["Rating"] = df["Rating"].fillna(0.0)
    df["Harga (IDR)"] = pd.to_numeric(df["Harga (IDR)"], errors="coerce").fillna(0).astype(int)
    df["Diskon (%)"] = pd.to_numeric(df["Diskon (%)"], errors="coerce").fillna(0.0)
    
    # Clean fields
    print("[DATA CLEANER] Parsing numeric 'Terjual' and 'Jumlah Ulasan'...")
    df["terjual_clean"] = df["Terjual"].apply(parse_terjual)
    df["ulasan_clean"] = df["Jumlah Ulasan"].apply(parse_ulasan)
    
    # Categorization
    print("[DATA CLEANER] Categorizing products via NLP keyword mapping...")
    df["kategori"] = df["Nama Produk"].apply(extract_category)
    
    # Normalize Location
    df["lokasi_clean"] = df["Lokasi Toko"].apply(normalize_location)
    
    # Calculate Estimated GMV (Gross Merchandise Value)
    df["estimasi_gmv"] = df["Harga (IDR)"] * df["terjual_clean"]
    
    # Price Tiering for business insights
    def get_price_tier(price):
        if price < 25000: return "< Rp 25 Ribu (Budget)"
        elif price <= 100000: return "Rp 25k - 100k (Ekonomis)"
        elif price <= 500000: return "Rp 100k - 500k (Menengah)"
        elif price <= 2000000: return "Rp 500k - 2 Juta (Premium)"
        else: return "> Rp 2 Juta (Luxury/Investasi)"
        
    df["price_tier"] = df["Harga (IDR)"].apply(get_price_tier)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"[DATA CLEANER] Cleaned dataset saved to: {output_path} ({len(df)} rows)")
    return df

def generate_transactions_and_customers(df_clean, n_customers=1000, n_transactions=15000,
                                       tx_output_path=TRANSACTIONS_DATA_PATH,
                                       cust_output_path=CUSTOMERS_DATA_PATH):
    """
    Generates synthetic transaction logs (basket_details) and customer profiles (customer_details)
    anchored to the real 29,519 Tokopedia products, ensuring full compliance with Worksheet 3 and Laporan 2.
    """
    np.random.seed(42)
    print(f"[DATA GENERATOR] Generating {n_customers} customer profiles and {n_transactions} basket transactions...")
    
    # Customer Details: customer_id, sex, customer_age, tenure
    genders = ["Male", "Female"]
    ages = np.random.randint(18, 65, size=n_customers)
    tenures = np.random.randint(1, 60, size=n_customers) # in months
    sex_list = np.random.choice(genders, size=n_customers, p=[0.48, 0.52])
    customer_ids = [f"CUST_{i+1:04d}" for i in range(n_customers)]
    
    df_customers = pd.DataFrame({
        "customer_id": customer_ids,
        "sex": sex_list,
        "customer_age": ages,
        "tenure": tenures
    })
    
    # Basket Details: customer_id, product_id, basket_date, basket_count, hour, day_of_week
    # Pick products weighted by their sales popularity
    top_products = df_clean.sort_values(by="terjual_clean", ascending=False).head(500)
    top_prod_ids = top_products["product_id"].tolist()
    
    sampled_cust_ids = np.random.choice(customer_ids, size=n_transactions)
    sampled_prod_ids = np.random.choice(top_prod_ids, size=n_transactions)
    
    # Generate realistic dates across 2026 (or past 6 months)
    start_date = pd.Timestamp("2026-01-01")
    date_offsets = np.random.randint(0, 180, size=n_transactions)
    basket_dates = [start_date + pd.Timedelta(days=int(d)) for d in date_offsets]
    
    # Peak hours simulation: higher traffic around lunch (12-14) and evening (19-22)
    hours_pool = [8, 9, 10, 11, 12, 12, 13, 13, 14, 15, 16, 17, 18, 19, 20, 20, 21, 21, 22, 23]
    hours = np.random.choice(hours_pool, size=n_transactions)
    
    # basket_count (1 to 5 items)
    basket_counts = np.random.choice([1, 2, 3, 4, 5], size=n_transactions, p=[0.65, 0.20, 0.08, 0.04, 0.03])
    
    df_transactions = pd.DataFrame({
        "customer_id": sampled_cust_ids,
        "product_id": sampled_prod_ids,
        "basket_date": [d.strftime("%Y-%m-%d") for d in basket_dates],
        "basket_hour": hours,
        "day_of_week": [d.strftime("%A") for d in basket_dates],
        "basket_count": basket_counts
    })
    
    # Save both
    tx_output_path.parent.mkdir(parents=True, exist_ok=True)
    df_customers.to_csv(cust_output_path, index=False)
    df_transactions.to_csv(tx_output_path, index=False)
    
    print(f"[DATA GENERATOR] Customer details saved to: {cust_output_path}")
    print(f"[DATA GENERATOR] Basket transactions saved to: {tx_output_path}")
    return df_customers, df_transactions

if __name__ == "__main__":
    clean_df = clean_tokopedia_data()
    generate_transactions_and_customers(clean_df)
