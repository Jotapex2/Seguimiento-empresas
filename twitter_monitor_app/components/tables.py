from __future__ import annotations

import pandas as pd
import streamlit as st


def render_results_table(df: pd.DataFrame):
    if df.empty:
        st.warning("No se encontraron tweets relevantes con los filtros actuales.")
        return

    preview = df[
        [
            "createdAt",
            "author_name",
            "author_username",
            "category_detected",
            "matched_keyword",
            "relevance_score",
            "risk_score",
            "text",
            "url",
        ]
    ].sort_values(["relevance_score", "risk_score"], ascending=False)
    st.dataframe(preview, width="stretch", hide_index=True)


def render_rankings(df: pd.DataFrame):
    if df.empty:
        return

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Ranking de tweets")
        top_tweets = df.nlargest(10, "relevance_score")[["author_username", "matched_keyword", "relevance_score", "risk_score", "text"]]
        st.dataframe(top_tweets, width="stretch", hide_index=True)
    with col2:
        st.subheader("Ranking de autores")
        top_authors = (
            df.groupby(["author_username", "author_name"], dropna=False)
            .agg(tweets=("id", "count"), avg_relevance=("relevance_score", "mean"), avg_risk=("risk_score", "mean"))
            .reset_index()
            .sort_values(["tweets", "avg_relevance"], ascending=False)
            .head(10)
        )
        st.dataframe(top_authors, width="stretch", hide_index=True)
