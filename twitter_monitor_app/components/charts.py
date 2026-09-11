from __future__ import annotations

from collections import Counter
from typing import Dict, Iterable

import pandas as pd
import plotly.express as px
import streamlit as st

from services.exporter import matplotlib_figure_to_png_bytes, plotly_figure_to_png_bytes
from services.sentiment_analysis import build_sentiment_word_frequencies, build_wordcloud_figure


def _render_plotly_download(fig, name: str):
    # Static image conversion can block in headless environments. Only run it
    # when requested, never while displaying monitoring results.
    if not st.button("Preparar PNG", key=f"prepare-png-{name}"):
        return
    png_bytes = plotly_figure_to_png_bytes(fig)
    if png_bytes:
        st.download_button("Descargar PNG", data=png_bytes, file_name=f"{name}.png", mime="image/png", key=f"png-{name}", on_click="ignore")
    else:
        st.caption("Descarga PNG no disponible: instala `kaleido`.")


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
    with col1:
        _render_plotly_download(fig_categories, "tweets_por_categoria")

    top_authors = (
        df.groupby("author_username", dropna=False)
        .size()
        .reset_index(name="tweets")
        .sort_values("tweets", ascending=False)
        .head(10)
    )
    fig_authors = px.bar(top_authors, x="author_username", y="tweets", title="Top autores")
    col2.plotly_chart(fig_authors, width="stretch")
    with col2:
        _render_plotly_download(fig_authors, "top_autores")

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
        _render_plotly_download(fig_timeline, "evolucion_temporal")


def build_top_mentions(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["entidad", "menciones"])

    counter: Counter = Counter()
    if "matches" in df.columns:
        for matches in df["matches"]:
            if not isinstance(matches, list):
                continue
            for item in matches:
                if isinstance(item, dict) and item.get("match_type") == "company" and item.get("group"):
                    counter[item["group"]] += 1

    if not counter:
        column = "keyword" if "keyword" in df.columns else "matched_keyword"
        if column in df.columns:
            for value in df[column].dropna():
                text = str(value).strip()
                if text and text.lower() != "nan":
                    counter[text] += 1

    return pd.DataFrame(counter.most_common(top_n), columns=["entidad", "menciones"])


def render_top_mentions(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    top_df = build_top_mentions(df, top_n)
    if top_df.empty:
        st.info("Sin menciones de empresas o keywords para mostrar.")
        return top_df

    st.dataframe(top_df, width="stretch", hide_index=True)
    fig = px.bar(
        top_df.sort_values("menciones"),
        x="menciones",
        y="entidad",
        orientation="h",
        title=f"Top {top_n} empresas/keywords más mencionadas",
    )
    st.plotly_chart(fig, width="stretch")
    _render_plotly_download(fig, "top_menciones")

    import matplotlib.pyplot as plt

    st.caption("Nube de empresas/keywords más mencionadas (el tamaño refleja el número de menciones)")
    fig_cloud = build_wordcloud_figure(
        dict(zip(top_df["entidad"], top_df["menciones"])),
        "Blues",
    )
    st.pyplot(fig_cloud)
    st.download_button(
        "Descargar nube (PNG)",
        data=matplotlib_figure_to_png_bytes(fig_cloud),
        file_name="nube_menciones.png",
        mime="image/png",
        key="png-nube-menciones",
    )
    plt.close(fig_cloud)

    st.download_button(
        "Descargar CSV",
        data=top_df.to_csv(index=False).encode("utf-8"),
        file_name="top_menciones.csv",
        mime="text/csv",
        key="csv-top-menciones",
    )
    return top_df


def render_sentiment_clouds(
    df: pd.DataFrame,
    sentiments: Dict[str, str],
    *,
    used_fallback: bool = False,
    extra_stopwords: Iterable[str] = (),
):
    if df.empty or not sentiments:
        st.info("Sin datos para el análisis de sentimiento.")
        return

    counts = Counter(sentiments.values())
    cols = st.columns(3)
    cols[0].metric("Positivos", counts.get("positivo", 0))
    cols[1].metric("Negativos", counts.get("negativo", 0))
    cols[2].metric("Neutrales", counts.get("neutral", 0))

    if used_fallback:
        st.warning(
            "No se pudo usar DeepSeek (falta `DEEPSEEK_API_KEY` o hubo un error). "
            "Se usó un clasificador léxico local como respaldo."
        )

    st.caption(
        "Solo se muestran las palabras que distinguen un sentimiento del otro. "
        "Se excluyen los conectores y palabras funcionales (pero, como, además, sin embargo…) "
        "y los términos de rubro o genéricos (minería, automotriz, empresa, etc.), "
        "porque describen el tema, no una emoción."
    )

    positive_freq, negative_freq, words_df = build_sentiment_word_frequencies(
        df, sentiments, extra_stopwords=extra_stopwords
    )

    import matplotlib.pyplot as plt

    fig_positive = build_wordcloud_figure(
        positive_freq, "Greens", empty_message="Sin palabras positivas tras el filtrado"
    )
    fig_negative = build_wordcloud_figure(
        negative_freq, "Reds", empty_message="Sin palabras negativas tras el filtrado"
    )

    col_positive, col_negative = st.columns(2)
    with col_positive:
        st.caption("Palabras positivas")
        st.pyplot(fig_positive)
        st.download_button(
            "Descargar nube positiva (PNG)",
            data=matplotlib_figure_to_png_bytes(fig_positive),
            file_name="nube_positiva.png",
            mime="image/png",
            key="png-nube-positiva",
        )
    with col_negative:
        st.caption("Palabras negativas")
        st.pyplot(fig_negative)
        st.download_button(
            "Descargar nube negativa (PNG)",
            data=matplotlib_figure_to_png_bytes(fig_negative),
            file_name="nube_negativa.png",
            mime="image/png",
            key="png-nube-negativa",
        )

    if not words_df.empty:
        st.download_button(
            "Descargar CSV de palabras",
            data=words_df.to_csv(index=False).encode("utf-8"),
            file_name="sentimiento_palabras.csv",
            mime="text/csv",
            key="csv-sentimiento",
        )

    plt.close(fig_positive)
    plt.close(fig_negative)
