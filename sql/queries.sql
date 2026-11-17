-- Olist E-commerce Analytics: MySQL queries
USE olist_analytics;

-- 1. Monthly revenue
SELECT DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m') AS month,
       COUNT(DISTINCT o.order_id) AS orders,
       ROUND(SUM(p.payment_value), 2) AS revenue
FROM orders o
JOIN payments p ON o.order_id = p.order_id
WHERE o.order_status = 'delivered'
GROUP BY month
ORDER BY month;

-- 2. Top 10 product categories by revenue
SELECT pr.product_category_name, ROUND(SUM(oi.price), 2) AS revenue
FROM order_items oi
JOIN products pr ON oi.product_id = pr.product_id
GROUP BY pr.product_category_name
ORDER BY revenue DESC
LIMIT 10;

-- 3. Average delivery delay vs estimate (days, negative = early)
SELECT ROUND(AVG(DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date)), 2) AS avg_delay_days
FROM orders
WHERE order_status = 'delivered'
  AND order_delivered_customer_date IS NOT NULL;

-- 4. Repeat customer rate
SELECT ROUND(100 * SUM(order_count > 1) / COUNT(*), 2) AS repeat_rate_pct
FROM (
  SELECT c.customer_unique_id, COUNT(DISTINCT o.order_id) AS order_count
  FROM customers c
  JOIN orders o ON c.customer_id = o.customer_id
  GROUP BY c.customer_unique_id
) t;

-- 5. Review score: on-time vs late (one score per order, date-level comparison)
WITH r1 AS (
  SELECT order_id, AVG(review_score) AS score
  FROM reviews GROUP BY order_id
)
SELECT (DATE(o.order_delivered_customer_date) > DATE(o.order_estimated_delivery_date)) AS is_late,
       ROUND(AVG(r1.score), 2) AS avg_score,
       COUNT(*) AS orders
FROM orders o
JOIN r1 ON o.order_id = r1.order_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
GROUP BY is_late;

-- 6. Late delivery % and review score by state
WITH r1 AS (
  SELECT order_id, AVG(review_score) AS score
  FROM reviews GROUP BY order_id
)
SELECT c.customer_state,
       COUNT(*) AS orders,
       ROUND(100 * AVG(DATE(o.order_delivered_customer_date) > DATE(o.order_estimated_delivery_date)), 2) AS late_pct,
       ROUND(AVG(r1.score), 2) AS avg_score
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN r1 ON o.order_id = r1.order_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
GROUP BY c.customer_state
HAVING orders > 500
ORDER BY late_pct DESC;

-- 7. Month-over-month growth and running total (window functions)
WITH monthly AS (
  SELECT DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m') AS month,
         SUM(p.payment_value) AS revenue
  FROM orders o
  JOIN payments p ON o.order_id = p.order_id
  WHERE o.order_status = 'delivered'
  GROUP BY month
)
SELECT month,
       ROUND(revenue, 2) AS revenue,
       ROUND(100 * (revenue - LAG(revenue) OVER (ORDER BY month))
             / LAG(revenue) OVER (ORDER BY month), 2) AS mom_growth_pct,
       ROUND(SUM(revenue) OVER (ORDER BY month), 2) AS running_total
FROM monthly
ORDER BY month;

-- 8. Cohort retention (customers returning by months since first order)
WITH orders_m AS (
  SELECT c.customer_unique_id,
         EXTRACT(YEAR_MONTH FROM o.order_purchase_timestamp) AS ym
  FROM orders o
  JOIN customers c ON o.customer_id = c.customer_id
  WHERE o.order_status = 'delivered'
),
cohort AS (
  SELECT customer_unique_id, MIN(ym) AS cohort_ym
  FROM orders_m
  GROUP BY customer_unique_id
)
SELECT ch.cohort_ym,
       PERIOD_DIFF(om.ym, ch.cohort_ym) AS month_index,
       COUNT(DISTINCT om.customer_unique_id) AS customers
FROM orders_m om
JOIN cohort ch ON om.customer_unique_id = ch.customer_unique_id
GROUP BY ch.cohort_ym, month_index
ORDER BY ch.cohort_ym, month_index;

-- 9. RFM segmentation (saved as a table for Power BI)
DROP TABLE IF EXISTS rfm_segments;
CREATE TABLE rfm_segments AS
WITH cust AS (
  SELECT c.customer_unique_id,
         DATEDIFF((SELECT MAX(order_purchase_timestamp) FROM orders),
                  MAX(o.order_purchase_timestamp)) AS recency_days,
         COUNT(DISTINCT o.order_id) AS frequency,
         SUM(p.payment_value) AS monetary
  FROM customers c
  JOIN orders o ON c.customer_id = o.customer_id
  JOIN payments p ON o.order_id = p.order_id
  WHERE o.order_status = 'delivered'
  GROUP BY c.customer_unique_id
),
scored AS (
  SELECT *,
         NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
         CASE WHEN frequency >= 3 THEN 3 WHEN frequency = 2 THEN 2 ELSE 1 END AS f_score,
         NTILE(5) OVER (ORDER BY monetary) AS m_score
  FROM cust
)
SELECT *,
       CASE WHEN f_score >= 2 THEN 'Loyal'
            WHEN r_score >= 4 AND m_score >= 4 THEN 'Champions'
            WHEN r_score <= 2 AND m_score >= 4 THEN 'At Risk'
            WHEN r_score <= 2 THEN 'Lost'
            ELSE 'Regular' END AS segment
FROM scored;

-- 9b. Segment summary
SELECT segment, COUNT(*) AS customers,
       ROUND(SUM(monetary), 2) AS revenue,
       ROUND(100 * SUM(monetary) / (SELECT SUM(monetary) FROM rfm_segments), 2) AS revenue_pct
FROM rfm_segments
GROUP BY segment
ORDER BY revenue DESC;