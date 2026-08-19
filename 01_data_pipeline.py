"""FORESIGHT D1: reproducible ingestion + cleaning.
Run: python 01_data_pipeline.py
Input: archive/retail_clean_dataset + retail_contaminated_dataset
"""

from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
ARCHIVE = BASE / "archive"
CLEAN = ARCHIVE / "retail_clean_dataset"
CONTAMINATED = ARCHIVE / "retail_contaminated_dataset"

OUT = BASE / "outputs"
OUT.mkdir(exist_ok=True)

CHUNK = 1_000_000

# -----------------------------
# Check input folders
# -----------------------------
if not CLEAN.exists():
    raise FileNotFoundError(f"Clean dataset folder not found: {CLEAN}")

if not CONTAMINATED.exists():
    raise FileNotFoundError(
        f"Contaminated dataset folder not found: {CONTAMINATED}"
    )

required = [
    "customer_master.csv",
    "inventory_snapshot.csv",
    "promotions.csv",
    "sales_transactions.csv",
    "sku_inventory_flags.csv",
    "sku_master.csv",
    "store_master.csv",
]

missing = [f for f in required if not (CLEAN / f).exists()]

if missing:
    raise FileNotFoundError(
        f"Missing files in clean dataset: {missing}"
    )

# -----------------------------
# Read dimension tables
# -----------------------------
sku = pd.read_csv(CLEAN / "sku_master.csv")
inv = pd.read_csv(CLEAN / "inventory_snapshot.csv")
stores = pd.read_csv(CLEAN / "store_master.csv")
customers = pd.read_csv(CLEAN / "customer_master.csv")
promotions = pd.read_csv(CLEAN / "promotions.csv")
flags = pd.read_csv(CLEAN / "sku_inventory_flags.csv")

# Remove exact duplicate rows
for d in [sku, inv, stores, customers, promotions, flags]:
    d.drop_duplicates(inplace=True)

print("Dimension tables loaded successfully.")

# -----------------------------
# Process large sales file
# -----------------------------
sales_path = CLEAN / "sales_transactions.csv"

parts = []

usecols = [
    "date",
    "receipt_id",
    "store_id",
    "sku_id",
    "customer_id",
    "quantity",
    "unit_price",
    "total_value",
    "discount_pct",
    "promo_id",
]

print("Processing sales transactions...")

for chunk_no, ch in enumerate(
    pd.read_csv(
        sales_path,
        usecols=usecols,
        parse_dates=["date"],
        chunksize=CHUNK,
    ),
    start=1,
):

    print(f"Processing chunk {chunk_no}...")

    ch = ch.drop_duplicates().copy()

    for c in [
        "quantity",
        "unit_price",
        "total_value",
        "discount_pct",
    ]:
        ch[c] = pd.to_numeric(ch[c], errors="coerce")

    ch["discount_pct"] = ch["discount_pct"].fillna(0)

    # Remove unusable records
    ch = ch.dropna(
        subset=[
            "date",
            "sku_id",
            "quantity",
            "total_value",
        ]
    ).copy()

    # Positive sales only
    ch = ch[
        (ch["quantity"] > 0)
        & (ch["total_value"] >= 0)
    ].copy()

    # Weekly calendar feature
    ch["week_start"] = (
        ch["date"]
        - pd.to_timedelta(
            ch["date"].dt.weekday,
            unit="D"
        )
    ).dt.normalize()

    # Promotion flag
    ch["promo_flag"] = ch["promo_id"].notna().astype("int8")

    # Weekly SKU aggregation
    g = (
        ch.groupby(
            ["week_start", "sku_id"],
            as_index=False
        )
        .agg(
            units_sold=("quantity", "sum"),
            revenue=("total_value", "sum"),
            avg_unit_price=("unit_price", "mean"),
            avg_discount_pct=("discount_pct", "mean"),
            promo_txn_share=("promo_flag", "mean"),
            transactions=("receipt_id", "nunique"),
            customers=("customer_id", "nunique"),
            stores=("store_id", "nunique"),
        )
    )

    parts.append(g)

# -----------------------------
# Combine weekly results
# -----------------------------
weekly = pd.concat(
    parts,
    ignore_index=True
)

weekly = (
    weekly
    .groupby(
        ["week_start", "sku_id"],
        as_index=False
    )
    .agg(
        units_sold=("units_sold", "sum"),
        revenue=("revenue", "sum"),
        avg_unit_price=("avg_unit_price", "mean"),
        avg_discount_pct=("avg_discount_pct", "mean"),
        promo_txn_share=("promo_txn_share", "mean"),
        transactions=("transactions", "sum"),
        customers=("customers", "sum"),
        stores=("stores", "max"),
    )
)

weekly = weekly.sort_values(
    ["sku_id", "week_start"]
)

weekly.to_csv(
    OUT / "weekly_sku_demand_clean.csv",
    index=False
)

print(
    f"Weekly demand created: {len(weekly):,} rows"
)

# -----------------------------
# Inventory aggregation
# -----------------------------
invagg = (
    inv.groupby("sku_id", as_index=False)
    .agg(
        stores_with_inventory=("store_id", "nunique"),
        stock_on_hand=("stock_on_hand", "sum"),
        reorder_point=("reorder_point", "sum"),
        safety_stock=("safety_stock", "sum"),
    )
)

invagg.to_csv(
    OUT / "inventory_by_sku.csv",
    index=False
)

flags.to_csv(
    OUT / "anomaly_flags.csv",
    index=False
)

# -----------------------------
# Data quality report
# -----------------------------
rows = []

for name, d in [
    ("sku_master", sku),
    ("inventory_snapshot", inv),
    ("store_master", stores),
    ("customer_master", customers),
    ("promotions", promotions),
    ("sku_inventory_flags", flags),
]:
    rows.append(
        {
            "dataset": name,
            "rows": len(d),
            "columns": len(d.columns),
            "duplicate_rows": int(
                d.duplicated().sum()
            ),
            "missing_cells": int(
                d.isna().sum().sum()
            ),
        }
    )

# Referential integrity
sku_ids = set(
    sku["sku_id"].astype(str)
)

store_ids = set(
    stores["store_id"].astype(str)
)

invalid_inventory = (
    ~inv["sku_id"]
    .astype(str)
    .isin(sku_ids)
).sum()

invalid_stores = (
    ~inv["store_id"]
    .astype(str)
    .isin(store_ids)
).sum()

invalid_flags = (
    ~flags["sku_id"]
    .astype(str)
    .isin(sku_ids)
).sum()

rows.extend(
    [
        {
            "dataset": "inventory_fk_check",
            "rows": len(inv),
            "columns": 0,
            "duplicate_rows": 0,
            "missing_cells": int(
                invalid_inventory
                + invalid_stores
            ),
        },
        {
            "dataset": "flag_fk_check",
            "rows": len(flags),
            "columns": 0,
            "duplicate_rows": 0,
            "missing_cells": int(
                invalid_flags
            ),
        },
    ]
)

dq = pd.DataFrame(rows)

dq.to_csv(
    OUT / "data_quality_report.csv",
    index=False
)

print("\nD1 COMPLETE")
print("=" * 60)
print(dq.to_string(index=False))
print("=" * 60)

print(
    f"\nWeekly demand file: "
    f"{OUT / 'weekly_sku_demand_clean.csv'}"
)

print(
    f"Inventory file: "
    f"{OUT / 'inventory_by_sku.csv'}"
)

print(
    f"Data quality report: "
    f"{OUT / 'data_quality_report.csv'}"
)