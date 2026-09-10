from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd
import streamlit as st

PACKAGE_ROOT = Path(__file__).resolve().parent
PACKAGE_PARENT = PACKAGE_ROOT.parent

# Support both `streamlit run app.py` and package-style execution in Streamlit Cloud
# without importing the same module tree under two different names.
if __package__:
    if str(PACKAGE_PARENT) not in sys.path:
        sys.path.insert(0, str(PACKAGE_PARENT))

    from twitter_monitor_app.components.charts import render_charts
    from twitter_monitor_app.components.filters import render_sidebar_filters
    from twitter_monitor_app.components.metrics import render_kpis
    from twitter_monitor_app.components.tables import render_rankings, render_results_table
    from twitter_monitor_app.components.taxonomy_editor import render_taxonomy_editor
    from twitter_monitor_app.config.settings import get_settings
    from twitter_monitor_app.data.keywords import get_default_catalog
    from twitter_monitor_app.google_social_monitor import (
        GoogleRateLimitError,
        MAX_GOOGLE_PAGES_PER_KEYWORD,
        collect_monitor_results,
    )
    from twitter_monitor_app.services.classifier import post_process_tweets
    from twitter_monitor_app.services.data_manager import collect_api_data, mock_tweets
    from twitter_monitor_app.services.deepseek_analysis import (
        DeepSeekAnalysisError,
        build_analysis_sections,
        related_links,
        request_deepseek_analysis,
        section_cache_payload,
        select_related_rows,
    )
    from twitter_monitor_app.services.email_sender import (
        EmailDeliveryError,
        is_email_delivery_configured,
        send_report_email,
    )
    from twitter_monitor_app.services.exporter import dataframe_to_csv_bytes, dataframe_to_excel_bytes
    from twitter_monitor_app.services.runtime_store import get_history_count, load_cache, make_cache_key, persist_history, save_cache
    from twitter_monitor_app.services.scoring import enrich_scores
    from twitter_monitor_app.services.twitter_client import TwitterApiError
else:
    if str(PACKAGE_ROOT) not in sys.path:
        sys.path.insert(0, str(PACKAGE_ROOT))

    from components.charts import render_charts
    from components.filters import render_sidebar_filters
    from components.metrics import render_kpis
    from components.tables import render_rankings, render_results_table
    from components.taxonomy_editor import render_taxonomy_editor
    from config.settings import get_settings
    from data.keywords import get_default_catalog
    from google_social_monitor import GoogleRateLimitError, MAX_GOOGLE_PAGES_PER_KEYWORD, collect_monitor_results
    from services.classifier import post_process_tweets
    from services.data_manager import collect_api_data, mock_tweets
    from services.deepseek_analysis import (
        DeepSeekAnalysisError,
        build_analysis_sections,
        related_links,
        request_deepseek_analysis,
        section_cache_payload,
        select_related_rows,
    )
    from services.email_sender import EmailDeliveryError, is_email_delivery_configured, send_report_email
    from services.exporter import dataframe_to_csv_bytes, dataframe_to_excel_bytes
    from services.runtime_store import get_history_count, load_cache, make_cache_key, persist_history, save_cache
    from services.scoring import enrich_scores
    from services.twitter_client import TwitterApiError

logging.basicConfig(level=logging.INFO)


def build_google_keywords(filters: Dict, catalog: dict) -> List[str]:
    keywords: list[str] = []

    for category in filters["selected_categories"]:
        keywords.extend(catalog["sector_topics"].get(category, []))
    for person in filters["selected_people"]:
        keywords.extend(catalog["people"].get(person, []))
    for company in filters["selected_companies"]:
        keywords.extend(catalog["companies"].get(company, []))

    deduped_keywords: list[str] = []
    seen: set[str] = set()
    for keyword in keywords:
        normalized = keyword.casefold().strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped_keywords.append(keyword.strip())
    return deduped_keywords


def build_dataframe(tweets: List[Dict], catalog: dict) -> pd.DataFrame:
    normalized_rows = []
    for tweet in tweets:
        enriched = enrich_scores(tweet, catalog)
        author = enriched.get("author", {}) or {}
        normalized_rows.append(
            {
                **enriched,
                "author_name": author.get("name", ""),
                "author_username": author.get("userName", ""),
                "engagement_total": (
                    int(enriched.get("likeCount", 0) or 0)
                    + int(enriched.get("retweetCount", 0) or 0)
                    + int(enriched.get("replyCount", 0) or 0)
                    + int(enriched.get("quoteCount", 0) or 0)
                ),
            }
        )
    return pd.DataFrame(normalized_rows)


def render_limitations(df: pd.DataFrame):
    missing_views = bool(df.empty) or df["viewCount"].isna().any() if "viewCount" in df.columns else True
    limitations = [
        "twitterapi.io es una API de terceros, no la API oficial de X/Twitter.",
        "Algunos operadores avanzados pueden comportarse distinto; la app compensa con filtros en Python.",
        "La paginación depende de `cursor`; la propia documentación indica que `has_next_page` puede venir en `true` aun sin más resultados.",
    ]
    if missing_views:
        limitations.append("`viewCount` o métricas similares pueden faltar en algunas respuestas; la app usa fallback seguro.")
    st.info("\n".join(f"- {item}" for item in limitations))


def build_export_dataframe(df: pd.DataFrame, export_only_high_views: bool) -> pd.DataFrame:
    if df.empty:
        return df
    export_df = df.copy()
    if export_only_high_views:
        view_counts = pd.to_numeric(export_df.get("viewCount"), errors="coerce")
        export_df = export_df.loc[view_counts > 1000].copy()
    return export_df


def build_google_export_name(filters: Dict) -> str:
    platform = "linkedin" if filters["search_platform"] == "LinkedIn" else "x"
    mode = "google" if filters["x_search_mode"] == "Google" or platform == "linkedin" else "app"
    return f"{platform}_{mode}_results"


def build_report_mail_subject(filters: Dict) -> str:
    return (
        f"Informe {format_google_mode(filters)} "
        f"{filters['start_date'].isoformat()} a {filters['end_date'].isoformat()}"
    )


def format_analysis_for_email(analysis_sections: List[Dict] | None) -> str:
    if not analysis_sections:
        return ""

    blocks = ["", "Análisis DeepSeek:"]
    for section in analysis_sections:
        links = section.get("links", [])
        link_lines = "\n".join(f"- {link}" for link in links) if links else "- Sin links relacionados."
        blocks.append(
            "\n".join(
                [
                    "",
                    section.get("title", "Sección"),
                    section.get("analysis", "Sin análisis disponible."),
                    "Links relacionados:",
                    link_lines,
                ]
            )
        )
    return "\n".join(blocks)


def build_report_mail_body(filters: Dict, export_df: pd.DataFrame, analysis_sections: List[Dict] | None = None) -> str:
    selected_groups = [
        f"Categorías: {', '.join(filters['selected_categories']) or 'sin selección'}",
        f"Personas: {', '.join(filters['selected_people']) or 'sin selección'}",
        f"Empresas: {', '.join(filters['selected_companies']) or 'sin selección'}",
    ]
    summary_lines = [
        "Adjunto informe generado desde Twitter Monitor App.",
        f"Fuente: {format_google_mode(filters)}",
        f"Rango de fechas: {filters['start_date'].isoformat()} a {filters['end_date'].isoformat()}",
        f"Total de registros exportados: {len(export_df)}",
        *selected_groups,
    ]
    analysis_text = format_analysis_for_email(analysis_sections)
    if analysis_text:
        summary_lines.append(analysis_text)
    return "\n".join(summary_lines)


def render_email_report_section(filters: Dict, export_df: pd.DataFrame, export_name: str, analysis_sections: List[Dict] | None = None):
    st.markdown("#### Enviar por correo")
    if export_df.empty:
        st.caption("No hay datos para adjuntar en el informe.")
        return

    if not is_email_delivery_configured():
        st.warning("Falta configuración SMTP en `.env`. Define `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` y `EMAIL_FROM`.")
        return

    with st.form(f"email-report-form-{export_name}"):
        recipients_raw = st.text_input("Destinatarios", placeholder="persona@empresa.cl, equipo@empresa.cl")
        subject = st.text_input("Asunto", value=build_report_mail_subject(filters))
        send_clicked = st.form_submit_button("Enviar informe")

    if not send_clicked:
        return

    recipients = [item.strip() for item in recipients_raw.split(",") if item.strip()]
    attachment_name = f"{export_name}.xlsx"
    attachment_bytes = dataframe_to_excel_bytes(export_df)

    try:
        send_report_email(
            recipients=recipients,
            subject=subject.strip() or build_report_mail_subject(filters),
            body=build_report_mail_body(filters, export_df, analysis_sections),
            attachment_name=attachment_name,
            attachment_bytes=attachment_bytes,
        )
    except EmailDeliveryError as exc:
        st.error(str(exc))
        return

    st.success(f"Informe enviado a: {', '.join(recipients)}")


def render_deepseek_analysis(df: pd.DataFrame, source_label: str, catalog: dict, existing_sections: List[Dict] | None = None) -> List[Dict]:
    st.subheader("Análisis DeepSeek")
    if existing_sections is not None:
        for section in existing_sections:
            st.markdown(f"#### {section.get('title', 'Sección')}")
            st.markdown(section.get("analysis", "Sin análisis disponible."))
            links = section.get("links", [])
            if links:
                st.markdown("Links relacionados:")
                for link in links:
                    st.markdown(f"- [{link}]({link})")
            else:
                st.caption(f"Sin links relacionados en los resultados de {source_label}.")
        return existing_sections

    if df.empty:
        st.caption("No hay resultados para analizar.")
        return []

    settings = get_settings()
    if not settings.deepseek_api_key:
        st.warning("Falta configurar `DEEPSEEK_API_KEY` en `.env` para generar el análisis automático.")
        return []

    analysis_sections: List[Dict] = []
    for section in build_analysis_sections(catalog):
        fallback_to_all = section.title == "Implicancias para la industria sanitaria"
        rows = select_related_rows(df, section.terms, fallback_to_all=fallback_to_all)
        links = related_links(rows)
        with st.spinner(f"Generando análisis: {section.title}..."):
            cache_key = make_cache_key(
                "llm_analysis",
                {
                    "model": settings.deepseek_model,
                    "section": section_cache_payload(section, rows),
                },
            )
            analysis = load_cache(cache_key, settings.default_cache_ttl_hours)
            if analysis is None:
                try:
                    analysis = request_deepseek_analysis(
                        api_key=settings.deepseek_api_key,
                        api_url=settings.deepseek_api_url,
                        model=settings.deepseek_model,
                        section=section,
                        rows=rows,
                    )
                    save_cache(cache_key, analysis)
                except DeepSeekAnalysisError as exc:
                    analysis = f"No se pudo generar esta sección: {exc}"

        analysis_sections.append({"title": section.title, "analysis": analysis, "links": links})
        st.markdown(f"#### {section.title}")
        st.markdown(analysis)
        if links:
            st.markdown("Links relacionados:")
            for link in links:
                st.markdown(f"- [{link}]({link})")
        else:
            st.caption(f"Sin links relacionados en los resultados de {source_label}.")
    return analysis_sections


def render_x_app_dashboard(filters: Dict, df: pd.DataFrame, query_stats: Dict, catalog: dict, analysis_sections: List[Dict] | None = None) -> List[Dict]:
    render_kpis(df)
    render_limitations(df)
    render_efficiency_summary(filters, query_stats, df)
    if filters["chile_only"]:
        st.caption("Filtro activo: sólo se muestran posts detectados como originados en Chile (CL).")

    st.subheader("Resultados")
    render_results_table(df)

    analysis_sections = render_deepseek_analysis(df, format_google_mode(filters), catalog, analysis_sections)

    st.subheader("Visualizaciones")
    render_charts(df)

    st.subheader("Rankings")
    render_rankings(df)

    st.subheader("Exportación")
    export_df = build_export_dataframe(df, filters["export_only_high_views"])
    if filters["export_only_high_views"]:
        st.caption(f"Exportación filtrada: {len(export_df)} posts con viewCount mayor a 1000.")
    if not export_df.empty:
        st.download_button("Descargar CSV", data=dataframe_to_csv_bytes(export_df), file_name="twitter_monitor_results.csv", mime="text/csv")
        st.download_button(
            "Descargar Excel",
            data=dataframe_to_excel_bytes(export_df),
            file_name="twitter_monitor_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        render_email_report_section(filters, export_df, "twitter_monitor_results", analysis_sections)
    else:
        st.caption("Sin datos exportables con el filtro actual.")
    return analysis_sections


def render_google_dashboard(
    filters: Dict,
    df: pd.DataFrame,
    google_keywords: Iterable[str],
    catalog: dict,
    analysis_sections: List[Dict] | None = None,
) -> List[Dict]:
    render_google_metrics(df)
    render_google_summary(filters, google_keywords, df)

    st.subheader("Resultados")
    render_google_results(df)

    analysis_sections = render_deepseek_analysis(df, format_google_mode(filters), catalog, analysis_sections)

    st.subheader("Exportación")
    export_name = build_google_export_name(filters)
    if not df.empty:
        st.download_button("Descargar CSV", data=dataframe_to_csv_bytes(df), file_name=f"{export_name}.csv", mime="text/csv")
        st.download_button(
            "Descargar Excel",
            data=dataframe_to_excel_bytes(df),
            file_name=f"{export_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        render_email_report_section(filters, df, export_name, analysis_sections)
    else:
        st.caption("Sin datos exportables con el filtro actual.")
    return analysis_sections


def render_last_monitor_payload() -> bool:
    payload = st.session_state.get("last_monitor_payload")
    if not payload:
        return False

    catalog = st.session_state.get("catalog", get_default_catalog())
    st.info("Mostrando los últimos resultados generados. Ejecuta nuevamente el monitoreo para refrescar datos.")
    if payload["mode"] == "x_app":
        render_x_app_dashboard(
            payload["filters"],
            payload["df"],
            payload["query_stats"],
            catalog,
            payload.get("analysis_sections"),
        )
        return True

    render_google_dashboard(
        payload["filters"],
        payload["df"],
        payload.get("google_keywords", []),
        catalog,
        payload.get("analysis_sections"),
    )
    return True


def format_google_mode(filters: Dict) -> str:
    if filters["search_platform"] == "LinkedIn":
        return "LinkedIn / Google"
    if filters["x_search_mode"] == "Google":
        return "X / Google"
    return "X / App"


def render_google_metrics(df: pd.DataFrame):
    total = len(df)
    unique_keywords = df["keyword"].nunique() if total and "keyword" in df.columns else 0
    unique_links = df["link"].nunique() if total and "link" in df.columns else 0
    avg_relevance = round(df["relevancia_score"].mean(), 1) if total and "relevancia_score" in df.columns else 0.0

    cols = st.columns(4)
    cols[0].metric("Resultados", total)
    cols[1].metric("Keywords", unique_keywords)
    cols[2].metric("Links únicos", unique_links)
    cols[3].metric("Relevancia promedio", avg_relevance)


def render_google_results(df: pd.DataFrame):
    if df.empty:
        st.warning("No se encontraron resultados para los filtros actuales.")
        return
    preview_columns = ["platform", "keyword", "titulo", "fecha", "descripcion", "link", "relevancia_score"]
    st.dataframe(df[preview_columns], width="stretch", hide_index=True)


def render_google_summary(filters: Dict, keywords: Iterable[str], df: pd.DataFrame):
    keyword_count = len(list(keywords))
    effective_google_limit = min(filters["google_results_per_keyword"], MAX_GOOGLE_PAGES_PER_KEYWORD * 10)
    messages = [
        f"Modo activo: {format_google_mode(filters)}.",
        f"Keywords ejecutadas: {keyword_count}.",
        f"Resultados procesados: {len(df)}.",
        f"Límite efectivo Google por keyword: {effective_google_limit}.",
        "La búsqueda Google usa indexación pública y no aplica los mismos filtros/metricas que X vía app.",
    ]
    st.caption(" ".join(messages))


def render_efficiency_summary(filters: Dict, query_stats: Dict, df: pd.DataFrame):
    history_count = get_history_count()
    messages = [
        f"Estrategia activa: {filters['strategy']}.",
        f"Límite efectivo aplicado en esta corrida: {query_stats.get('effective_limit', filters['limit'])}.",
        f"Batches ejecutados: {query_stats.get('query_batches_executed', 0)} de {query_stats.get('query_batches_planned', 0)}.",
    ]
    if filters["include_user_timelines"]:
        messages.append(f"Timelines consultadas: {query_stats.get('timeline_users_executed', 0)}.")
    if filters["use_cache"]:
        messages.append(f"Consultas evitadas por caché: {query_stats.get('api_calls_saved_by_cache', 0)}.")
    if filters["incremental_mode"]:
        messages.append("Modo incremental activo: se intentó pedir sólo contenido nuevo por query.")
    if query_stats.get("stopped_early"):
        messages.append("Se aplicó corte temprano al alcanzar el volumen objetivo.")
    messages.append(f"Histórico local acumulado: {history_count} posts.")
    messages.append(f"Posts procesados en la corrida actual: {len(df)}.")
    st.caption(" ".join(messages))


def main():
    settings = get_settings()
    st.set_page_config(page_title=settings.app_name, layout="wide")
    st.title(settings.app_name)
    st.caption("Monitoreo ejecutivo para conversaciones del sector sanitario, hídrico y regulatorio en Chile en X y LinkedIn.")

    default_catalog = get_default_catalog()
    if "catalog" not in st.session_state:
        st.session_state["catalog"] = get_default_catalog()
    catalog = render_taxonomy_editor(st.session_state["catalog"], default_catalog)
    filters = render_sidebar_filters(catalog)
    is_x_app_mode = filters["search_platform"] == "X" and filters["x_search_mode"] == "App"

    st.caption(f"Fuente seleccionada: {format_google_mode(filters)}.")

    if not filters["run"]:
        if render_last_monitor_payload():
            return
        st.info("Configura filtros y ejecuta el monitoreo. Puedes alternar entre LinkedIn/Google, X/App y X/Google desde la barra lateral.")
        return

    if is_x_app_mode:
        with st.spinner("Consultando y procesando resultados de X..."):
            try:
                if filters["simulation_mode"]:
                    raw_tweets = mock_tweets()
                    query_stats = {
                        "api_calls_saved_by_cache": 0,
                        "query_batches_planned": 0,
                        "query_batches_executed": 0,
                        "timeline_users_executed": 0,
                        "effective_limit": filters["limit"],
                        "stopped_early": False,
                    }
                else:
                    raw_tweets, query_stats = collect_api_data(filters, catalog)
            except TwitterApiError as exc:
                st.error(str(exc))
                return

            processed = post_process_tweets(raw_tweets, catalog, chile_only=filters["chile_only"])
            df = build_dataframe(processed, catalog)
            persist_history(df.to_dict(orient="records"))

        analysis_sections = render_x_app_dashboard(filters, df, query_stats, catalog)
        st.session_state["last_monitor_payload"] = {
            "mode": "x_app",
            "filters": filters,
            "df": df,
            "query_stats": query_stats,
            "analysis_sections": analysis_sections,
        }
        return

    google_platform = "linkedin" if filters["search_platform"] == "LinkedIn" else "x"
    google_keywords = build_google_keywords(filters, catalog)
    if not google_keywords:
        st.error("Selecciona al menos una categoría, persona o empresa para buscar en Google.")
        return

    with st.spinner("Consultando resultados públicos vía Google..."):
        try:
            df = collect_monitor_results(
                keywords=google_keywords,
                results_per_keyword=filters["google_results_per_keyword"],
                language=filters["google_language"],
                platform_name=google_platform,
                lowercase_text=filters["google_lowercase_text"],
                min_delay_seconds=filters["google_min_delay"],
                max_delay_seconds=filters["google_max_delay"],
            )
        except GoogleRateLimitError as exc:
            st.error(
                "Google bloqueó temporalmente la consulta por exceso de requests. "
                "Baja el límite por keyword, usa menos keywords o espera antes de reintentar. "
                f"Detalle: {exc}"
            )
            return
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))
            return

    analysis_sections = render_google_dashboard(filters, df, google_keywords, catalog)
    st.session_state["last_monitor_payload"] = {
        "mode": "google",
        "filters": filters,
        "df": df,
        "google_keywords": list(google_keywords),
        "analysis_sections": analysis_sections,
    }


if __name__ == "__main__":
    main()
