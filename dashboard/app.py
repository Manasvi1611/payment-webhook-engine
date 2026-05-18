import os
import time

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:password@localhost:5432/webhooks",
)
# Convert asyncpg URL to psycopg2 for synchronous dashboard use.
DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


@st.cache_resource
def get_engine():
    return create_engine(DATABASE_URL, pool_pre_ping=True)


st.set_page_config(page_title="Webhook Dashboard", layout="wide")
st.title("Payment Webhook Delivery Dashboard")
st.caption("Real-time monitoring of webhook delivery status")

refresh = st.sidebar.slider("Auto-refresh interval (seconds)", 5, 60, 10)
st.sidebar.info("Dashboard refreshes automatically.")

try:
    engine = get_engine()
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM delivery_logs")).scalar() or 0
        success = conn.execute(
            text("SELECT COUNT(*) FROM delivery_logs WHERE status = 'success'")
        ).scalar() or 0
        failed = conn.execute(
            text("SELECT COUNT(*) FROM delivery_logs WHERE status = 'failed'")
        ).scalar() or 0
        dlq = conn.execute(
            text("SELECT COUNT(*) FROM delivery_logs WHERE status = 'dead_letter'")
        ).scalar() or 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Deliveries", total)
        col2.metric("Successful", success, delta=None)
        col3.metric("Failed (retrying)", failed)
        col4.metric("Dead Letter", dlq)

        success_rate = round(success / total * 100, 1) if total else 0
        st.progress(success_rate / 100, text=f"Success rate: {success_rate}%")

        st.subheader("Status Distribution")
        status_df = pd.DataFrame(
            {"Status": ["Success", "Failed", "Dead Letter"], "Count": [success, failed, dlq]}
        ).set_index("Status")
        st.bar_chart(status_df)

        st.subheader("Recent Deliveries")
        df = pd.read_sql(
            text(
                "SELECT id, event_id, subscriber_id, event_type, status, attempts,"
                " last_attempt, error_message"
                " FROM delivery_logs ORDER BY created_at DESC LIMIT 100"
            ),
            conn,
        )
        st.dataframe(df, use_container_width=True)

        st.subheader("Subscribers")
        subs_df = pd.read_sql(
            text("SELECT id, name, url, events, active, created_at FROM subscribers"),
            conn,
        )
        st.dataframe(subs_df, use_container_width=True)

except Exception as exc:
    st.error(f"Cannot connect to database: {exc}")
    st.info(
        "Make sure PostgreSQL is running and DATABASE_URL points to the correct host."
    )

time.sleep(refresh)
st.rerun()
