import os
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

# Edit these two lines before running
PASSWORD = "PASTE_PASSWORD_HERE"
folder = "PATH_TO_OLIST_CSVS/"  # e.g. "E:/DatasetDataanalytics/"

engine = create_engine(URL.create(
    "mysql+pymysql", username="root", password=PASSWORD,
    host="localhost", port=3306, database="olist_analytics",
))
out = folder + "powerbi/"
os.makedirs(out, exist_ok=True)

orders = pd.read_sql("SELECT * FROM orders", engine)
payments = pd.read_sql("SELECT order_id, payment_value FROM payments", engine)
reviews = pd.read_sql("SELECT order_id, review_score FROM reviews", engine)
customers = pd.read_sql(
    "SELECT customer_id, customer_unique_id, customer_state FROM customers", engine)
items = pd.read_sql("SELECT order_id, product_id, price FROM order_items", engine)
products = pd.read_sql(
    "SELECT product_id, product_category_name FROM products", engine)
rfm = pd.read_sql("SELECT * FROM rfm_segments", engine)
trans = pd.read_csv(folder + "product_category_name_translation.csv")

pay = payments.groupby("order_id").payment_value.sum().reset_index()
rev = reviews.groupby("order_id").review_score.mean().reset_index()

df = orders.merge(customers, on="customer_id", how="left")
df = df.merge(pay, on="order_id", how="left")
df = df.merge(rev, on="order_id", how="left")

df["order_date"] = df.order_purchase_timestamp.dt.date
deliv = df.order_delivered_customer_date
df["delivery_days"] = (deliv - df.order_purchase_timestamp).dt.days
df["delay_days"] = (deliv - df.order_estimated_delivery_date).dt.days
late = deliv.dt.normalize() > df.order_estimated_delivery_date.dt.normalize()
df["is_late"] = late.astype(float)
df.loc[deliv.isna(), "is_late"] = None

cols = ["order_id", "customer_unique_id", "customer_state", "order_status",
        "order_date", "payment_value", "review_score",
        "delivery_days", "delay_days", "is_late"]
df[cols].to_csv(out + "orders_flat.csv", index=False)

cat = items.merge(products, on="product_id", how="left")
cat = cat.merge(trans, on="product_category_name", how="left")
cat["category"] = cat["product_category_name_english"].fillna("unknown")
cat_rev = cat.groupby("category")["price"].sum().reset_index()
cat_rev.to_csv(out + "category_revenue.csv", index=False)

rfm.to_csv(out + "rfm_segments.csv", index=False)
print("Done:", os.listdir(out))