from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st


def render_charts(df: pd.DataFrame):
    if df.empty:
        st.info("Sin datos para graficar.")
        return

    col1, col2 = st.columns(2)

    category_counts = (
        df.assign(category_list=df["category_detected"].fillna("Sin categoría").str.split(", "))
        .explode("category_list")
        .groupby("category_list", dropna=False)
        .size()
        .reset_index(name="tweets")
        .sort_values("tweets", ascending=False)
    )
    fig_categories = px.bar(category_counts, x="category_list", y="tweets", title="Tweets por categoría")
    col1.plotly_chart(fig_categories, width="stretch")

    top_authors = (
        df.groupby("author_username", dropna=False)
        .size()
        .reset_index(name="tweets")
        .sort_values("tweets", ascending=False)
        .head(10)
    )
    fig_authors = px.bar(top_authors, x="author_username", y="tweets", title="Top autores")
    col2.plotly_chart(fig_authors, width="stretch")

    timeline = (
        df.assign(created_day=pd.to_datetime(df["createdAt"], errors="coerce").dt.date)
        .groupby("created_day", dropna=False)
        .size()
        .reset_index(name="tweets")
        .dropna()
    )
    if not timeline.empty:
        fig_timeline = px.line(timeline, x="created_day", y="tweets", markers=True, title="Evolución temporal")
        st.plotly_chart(fig_timeline, width="stretch")
