# data_gen.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# ------------------------
# 1. Basic configuration
# ------------------------
np.random.seed(42)
random.seed(42)

dates = pd.date_range("2024-01-01", "2024-12-31", freq="D")
channels = ["Online", "Retail", "Partner"]
regions = ["Northeast", "Southeast", "Midwest", "West"]

products = [
    ("Echo Earbuds", 79, 45),
    ("Volt Power Bank", 49, 25),
    ("Cloud Pillow", 35, 18),
    ("Aurora Lamp", 39, 22),
    ("Trail Backpack", 69, 35),
    ("Breeze Purifier", 129, 75),
]

# ------------------------
# 2. Simulate daily orders
# ------------------------
rows = []
for d in dates:
    for ch in channels:
        for _ in range(np.random.randint(60, 120)):
            prod = random.choice(products)
            price = prod[1] * np.random.uniform(0.9, 1.1)
            qty = np.random.randint(1, 4)
            discount = np.random.uniform(0, 0.2)
            net_price = price * (1 - discount)
            revenue = net_price * qty
            cost = prod[2] * qty
            region = random.choice(regions)
            rows.append([d, prod[0], ch, region, price, qty, discount, revenue, cost])

df = pd.DataFrame(rows, columns=[
    "date", "product", "channel", "region",
    "unit_price", "quantity", "discount_pct", "revenue", "cost"
])

df.to_csv("ba_orders_2024.csv", index=False)
df.head()  # (optional: no output when run as a script)