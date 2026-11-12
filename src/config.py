import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_PATH = BASE_DIR / "tokopedia" / "produk_tokopedia.csv"
PROCESSED_DATA_PATH = DATA_DIR / "processed_tokopedia.csv"
TRANSACTIONS_DATA_PATH = DATA_DIR / "transactions_simulated.csv"
CUSTOMERS_DATA_PATH = DATA_DIR / "customers_simulated.csv"
CLUSTERS_DATA_PATH = DATA_DIR / "products_clustered.csv"

# MongoDB connection settings (default local)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = "ecommerce_bigdata"
MONGO_COLLECTION_PRODUCTS = "tokopedia_products"
MONGO_COLLECTION_TRANSACTIONS = "basket_details"
MONGO_COLLECTION_CUSTOMERS = "customer_details"
