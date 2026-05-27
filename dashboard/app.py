import os
import time

import pandas as pd
import plotly.express as px
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
        pending = conn.execute(
            text("SELECT COUNT(*) FROM delivery_logs WHERE status = 'pending'")
        ).scalar() or 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Deliveries", total)
        col2.markdown(
            f'<p style="font-size:.875rem;margin:0 0 4px;color:rgba(250,250,250,0.6)">Successful</p>'
            f'<p style="font-size:1.875rem;font-weight:600;color:#10b981;margin:0;line-height:1.2">{success}</p>',
            unsafe_allow_html=True,
        )
        col3.markdown(
            f'<p style="font-size:.875rem;margin:0 0 4px;color:rgba(250,250,250,0.6)">Failed (retrying)</p>'
            f'<p style="font-size:1.875rem;font-weight:600;color:#ef4444;margin:0;line-height:1.2">{failed}</p>',
            unsafe_allow_html=True,
        )
        col4.markdown(
            f'<p style="font-size:.875rem;margin:0 0 4px;color:rgba(250,250,250,0.6)">Dead Letter</p>'
            f'<p style="font-size:1.875rem;font-weight:600;color:#f59e0b;margin:0;line-height:1.2">{dlq}</p>',
            unsafe_allow_html=True,
        )

        success_rate = round(success / total * 100, 1) if total else 0
        st.progress(success_rate / 100, text=f"Success rate: {success_rate}%")

        st.subheader("Status Distribution")
        status_df = pd.DataFrame({
            "Status": ["Success", "Failed", "Dead Letter", "Pending"],
            "Count": [success, failed, dlq, pending],
        })
        fig = px.bar(
            status_df,
            x="Status",
            y="Count",
            color="Status",
            color_discrete_map={
                "Success":     "#10b981",
                "Failed":      "#ef4444",
                "Dead Letter": "#f59e0b",
                "Pending":     "#3b82f6",
            },
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

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
