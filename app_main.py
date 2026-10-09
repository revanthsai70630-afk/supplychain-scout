
import streamlit as st
import pandas as pd
from io import StringIO
from datetime import date

st.set_page_config(
    page_title="SupplyChain Scout",
    page_icon="📦",
    layout="wide"
)

SAMPLE_DATA = """order_id,supplier,country,product,order_date,expected_date,actual_date,quantity,unit_cost,stock_on_hand,reorder_level
PO-1001,Northstar Parts,Japan,Sensor A,2026-09-20,2026-10-04,2026-10-03,100,12.50,24,40
PO-1002,Alpine Components,France,Valve B,2026-09-22,2026-10-05,2026-10-08,80,18.00,20,30
PO-1003,Pacific Materials,Singapore,Cable C,2026-09-25,2026-10-10,,200,4.50,150,60
PO-1004,Euro Industrial,Netherlands,Motor D,2026-09-18,2026-10-02,2026-10-02,25,240.00,4,8
PO-1005,Maple Supply,Canada,Filter E,2026-09-28,2026-10-07,,60,7.25,12,20
PO-1006,Sunrise Electronics,Japan,Board F,2026-09-21,2026-10-06,2026-10-09,40,95.00,10,15
PO-1007,Bluewater Trade,Ireland,Seal G,2026-09-29,2026-10-12,,90,3.20,70,25
PO-1008,Atlas Manufacturing,France,Bearing H,2026-09-19,2026-10-01,2026-10-01,50,14.00,18,20
PO-1009,Orchid Components,Singapore,Relay I,2026-09-30,2026-10-08,,120,8.00,15,35
PO-1010,Polar Systems,Finland,Bracket J,2026-09-24,2026-10-09,,45,22.00,16,16
"""

st.title("📦 SupplyChain Scout")
st.write(
    "Monitor supplier deliveries, purchase orders, "
    "and inventory reorder risks."
)

uploaded_file = st.file_uploader(
    "Upload your order data (CSV)",
    type=["csv"]
)

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
else:
    df = pd.read_csv(StringIO(SAMPLE_DATA))
    st.info("Showing demonstration data. Upload your own CSV to analyze it.")

required = [
    "order_id", "supplier", "country", "product",
    "order_date", "expected_date", "actual_date",
    "quantity", "unit_cost", "stock_on_hand", "reorder_level"
]

missing = [col for col in required if col not in df.columns]

if missing:
    st.error("Missing required columns: " + ", ".join(missing))
    st.stop()

for col in ["expected_date", "actual_date"]:
    df[col] = pd.to_datetime(df[col], errors="coerce")

for col in ["quantity", "unit_cost", "stock_on_hand", "reorder_level"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(
    subset=["quantity", "unit_cost", "stock_on_hand", "reorder_level"]
)

today = pd.Timestamp(date.today())

df["reference_date"] = df["actual_date"].fillna(today)

df["delay_days"] = (
    df["reference_date"] - df["expected_date"]
).dt.days

df["delay_days"] = df["delay_days"].fillna(0).clip(lower=0).astype(int)

df["delivery_status"] = "Pending"

df.loc[
    df["actual_date"].notna()
    & (df["delay_days"] == 0),
    "delivery_status"
] = "On time"

df.loc[
    df["actual_date"].notna()
    & (df["delay_days"] > 0),
    "delivery_status"
] = "Delivered late"

df.loc[
    df["actual_date"].isna()
    & (df["expected_date"] < today),
    "delivery_status"
] = "Overdue"

df["inventory_status"] = "OK"

df.loc[
    df["stock_on_hand"] <= df["reorder_level"],
    "inventory_status"
] = "Reorder"

df["order_value"] = df["quantity"] * df["unit_cost"]

st.sidebar.header("Filters")

suppliers = ["All"] + sorted(df["supplier"].dropna().unique().tolist())

selected_supplier = st.sidebar.selectbox(
    "Supplier",
    suppliers
)

statuses = ["All"] + sorted(df["delivery_status"].unique().tolist())

selected_status = st.sidebar.selectbox(
    "Delivery status",
    statuses
)

filtered = df.copy()

if selected_supplier != "All":
    filtered = filtered[filtered["supplier"] == selected_supplier]

if selected_status != "All":
    filtered = filtered[filtered["delivery_status"] == selected_status]

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Orders", len(filtered))

c2.metric(
    "Overdue Orders",
    int((filtered["delivery_status"] == "Overdue").sum())
)

c3.metric(
    "Delivered Late",
    int((filtered["delivery_status"] == "Delivered late").sum())
)

c4.metric(
    "Items to Reorder",
    int((filtered["inventory_status"] == "Reorder").sum())
)

st.subheader("📋 Purchase Order Details")

display_columns = [
    "order_id", "supplier", "country", "product",
    "expected_date", "actual_date", "delay_days",
    "delivery_status", "stock_on_hand", "inventory_status"
]

st.dataframe(
    filtered[display_columns],
    use_container_width=True,
    hide_index=True
)

st.subheader("📊 Orders by Delivery Status")

status_counts = filtered["delivery_status"].value_counts()

if not status_counts.empty:
    st.bar_chart(status_counts)

st.subheader("⚠️ Inventory Reorder Alerts")

alerts = filtered[filtered["inventory_status"] == "Reorder"]

if alerts.empty:
    st.success("No inventory reorder alerts in the selected data.")
else:
    st.dataframe(
        alerts[
            ["product", "supplier", "stock_on_hand", "reorder_level"]
        ],
        use_container_width=True,
        hide_index=True
    )

st.subheader("🏭 Supplier Summary")

summary = (
    filtered.groupby("supplier", as_index=False)
    .agg(
        total_orders=("order_id", "count"),
        average_delay_days=("delay_days", "mean"),
        order_value=("order_value", "sum")
    )
)

summary["average_delay_days"] = summary["average_delay_days"].round(1)
summary["order_value"] = summary["order_value"].round(2)

st.dataframe(
    summary,
    use_container_width=True,
    hide_index=True
)

csv_data = filtered.to_csv(index=False).encode("utf-8")

st.download_button(
    "Download filtered report (CSV)",
    data=csv_data,
    file_name="supplychain_report.csv",
    mime="text/csv"
)

st.caption(
    "SupplyChain Scout | Demonstration project using sample data. "
    "Check real operational data before making business decisions."
)
