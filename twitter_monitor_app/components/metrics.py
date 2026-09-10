from __future__ import annotations

import pandas as pd
import streamlit as st


def render_kpis(df: pd.DataFrame):
    total = len(df)
    avg_relevance = round(df["relevance_score"].mean(), 1) if total else 0.0
    avg_risk = round(df["risk_score"].mean(), 1) if total else 0.0
    unique_authors = df["author_username"].nunique() if total and "author_username" in df.columns else 0

    cols = st.columns(4)
    cols[0].metric("Tweets", total)
    cols[1].metric("Autores únicos", unique_authors)
    cols[2].metric("Relevancia promedio", avg_relevance)
    cols[3].metric("Riesgo promedio", avg_risk)
