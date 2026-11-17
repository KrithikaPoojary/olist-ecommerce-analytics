import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

# Edit these two lines before running
PASSWORD = "PASTE_PASSWORD_HERE"
folder = "PATH_TO_OLIST_CSVS/"  # e.g. "E:/DatasetDataanalytics/"

engine = create_engine(URL.create(
    "mysql+pymysql",
    username="root",
    password=PASSWORD,
    host="localhost",
    port=3306,
    database="olist_analytics",
))

tables = {
    "customers":   ("olist_customers_dataset.csv", []),
    "orders":      ("olist_orders_dataset.csv", ["order_purchase_timestamp", "order_approved_at",
                    "order_delivered_carrier_date", "order_delivered_customer_date",
                    "order_estimated_delivery_date"]),
    "order_items": ("olist_order_items_dataset.csv", ["shipping_limit_date"]),
    "payments":    ("olist_order_payments_dataset.csv", []),
    "reviews":     ("olist_order_reviews_dataset.csv", ["review_creation_date", "review_answer_timestamp"]),
    "products":    ("olist_products_dataset.csv", []),
    "sellers":     ("olist_sellers_dataset.csv", []),
}

zip_cols = {"customer_zip_code_prefix": str, "seller_zip_code_prefix": str}

for name, (file, dates) in tables.items():
    df = pd.read_csv(folder + file, dtype=zip_cols, parse_dates=dates)
    df.to_sql(name, engine, if_exists="replace", index=False, chunksize=5000)
    print(name, len(df))