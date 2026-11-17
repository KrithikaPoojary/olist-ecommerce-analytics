import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

# Edit these two lines before running
PASSWORD = "PASTE_PASSWORD_HERE"
folder = "PATH_TO_OLIST_CSVS/"  # e.g. "E:/DatasetDataanalytics/"

engine = create_engine(URL.create(
    "mysql+pymysql", username="root", password=PASSWORD,
    host="localhost", port=3306, database="olist_analytics",
))
out = folder + "images/"
os.makedirs(out, exist_ok=True)
sns.set_theme(style="whitegrid")

# ---------- Load ----------
orders = pd.read_sql("SELECT * FROM orders", engine)
items = pd.read_sql("SELECT * FROM order_items", engine)
payments = pd.read_sql("SELECT * FROM payments", engine)
reviews = pd.read_sql("SELECT * FROM reviews", engine)
customers = pd.read_sql("SELECT * FROM customers", engine)
products = pd.read_sql("SELECT * FROM products", engine)
rfm = pd.read_sql("SELECT * FROM rfm_segments", engine)
trans = pd.read_csv(folder + "product_category_name_translation.csv")

# ---------- Cleaning checks ----------
print("Missing values in orders:\n", orders.isna().sum(), "\n")
print("Duplicate order_ids:", orders.order_id.duplicated().sum())
print("Orders with >1 review:", reviews.order_id.duplicated().sum())
print("Products with missing category:", products.product_category_name.isna().sum(), "\n")

# One review score per order (some orders have several)
rev1 = reviews.groupby("order_id").review_score.mean().reset_index()

# ---------- Delivery metrics ----------
d = orders[(orders.order_status == "delivered") & orders.order_delivered_customer_date.notna()].copy()
d["delay_days"] = (d.order_delivered_customer_date - d.order_estimated_delivery_date).dt.days
d["delivery_days"] = (d.order_delivered_customer_date - d.order_purchase_timestamp).dt.days
d["is_late"] = d.delay_days > 0
d = d.merge(rev1, on="order_id").merge(customers[["customer_id", "customer_state"]], on="customer_id")
print("Late delivery %:", round(100 * d.is_late.mean(), 2))
print("Avg delivery days:", round(d.delivery_days.mean(), 1))
print(d.groupby("is_late").review_score.mean().round(2), "\n")

# ---------- Chart 1: Monthly revenue ----------
pay = payments.groupby("order_id").payment_value.sum().reset_index()
m = orders[orders.order_status == "delivered"].merge(pay, on="order_id")
m["month"] = m.order_purchase_timestamp.dt.to_period("M").astype(str)
monthly = m.groupby("month").payment_value.sum()
monthly = monthly["2017-01":"2018-08"]
plt.figure(figsize=(12, 5))
monthly.plot(marker="o")
plt.title("Monthly Revenue (R$)"); plt.xlabel(""); plt.xticks(rotation=45)
plt.tight_layout(); plt.savefig(out + "1_monthly_revenue.png", dpi=150); plt.close()

# ---------- Chart 2: Review score, late vs on time ----------
plt.figure(figsize=(5, 5))
sns.barplot(x=d.is_late.map({False: "On time", True: "Late"}), y=d.review_score, errorbar=None)
plt.title("Avg Review Score: On-time vs Late"); plt.xlabel(""); plt.ylabel("Avg score")
plt.tight_layout(); plt.savefig(out + "2_review_vs_late.png", dpi=150); plt.close()

# ---------- Chart 3: Late % by state ----------
st = d.groupby("customer_state").agg(orders=("order_id", "count"), late_pct=("is_late", "mean"))
st = st[st.orders > 500].sort_values("late_pct", ascending=False)
st["late_pct"] *= 100
plt.figure(figsize=(10, 5))
sns.barplot(x=st.index, y=st.late_pct, color="tomato")
plt.title("Late Delivery % by State"); plt.xlabel(""); plt.ylabel("% late")
plt.tight_layout(); plt.savefig(out + "3_late_by_state.png", dpi=150); plt.close()

# ---------- Chart 4: Top 10 categories ----------
prod_cols = products[["product_id", "product_category_name"]]
cat = items.merge(prod_cols, on="product_id", how="left")
cat = cat.merge(trans, on="product_category_name", how="left")
cat["category"] = cat["product_category_name_english"].fillna("unknown")
top = cat.groupby("category")["price"].sum().nlargest(10).sort_values()
plt.figure(figsize=(9, 5))
top.plot(kind="barh")
plt.title("Top 10 Categories by Revenue (R$)")
plt.ylabel("")
plt.tight_layout()
plt.savefig(out + "4_top_categories.png", dpi=150)
plt.close()

# ---------- Chart 5: RFM segment revenue ----------
seg = rfm.groupby("segment").monetary.sum().sort_values()
plt.figure(figsize=(8, 4))
seg.plot(kind="barh", color="seagreen")
plt.title("Revenue by RFM Segment (R$)"); plt.ylabel("")
plt.tight_layout(); plt.savefig(out + "5_rfm_segments.png", dpi=150); plt.close()

print("Done. Charts saved in", out)