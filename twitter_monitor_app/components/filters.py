from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from config.settings import get_settings


def _segment_label(option: str) -> str:
    return option


def render_sidebar_filters(catalog: dict):
    settings = get_settings()
    st.sidebar.header("Filtros")
    search_platform = st.sidebar.segmented_control(
        "Plataforma",
        options=["X", "LinkedIn"],
        default="X",
        format_func=_segment_label,
    )
    if search_platform == "X":
        x_search_mode = st.sidebar.segmented_control(
            "Búsqueda en X",
            options=["App", "Google"],
            default="App",
            format_func=_segment_label,
        )
    else:
        x_search_mode = "Google"

    sector_topics = catalog["sector_topics"]
    people = catalog["people"]
    companies = catalog["companies"]
    monitor_users = catalog["monitor_users"]
    monitor_accounts = catalog.get("monitor_accounts", {})

    selected_categories = st.sidebar.multiselect("Categorías", options=list(sector_topics.keys()), default=list(sector_topics.keys())[:4])
    selected_people = st.sidebar.multiselect("Personas", options=list(people.keys()), default=[])
    company_defaults = [name for name in ["Andess", "Aguas Andinas"] if name in companies]
    selected_companies = st.sidebar.multiselect("Empresas", options=list(companies.keys()), default=company_defaults)
    date_range = st.sidebar.date_input("Rango de fechas", value=(date.today() - timedelta(days=7), date.today()))

    is_x_app_mode = search_platform == "X" and x_search_mode == "App"
    simulation_mode = True
    strategy = "Balanceada"
    limit = settings.default_limit
    use_cache = True
    cache_ttl_hours = settings.default_cache_ttl_hours
    incremental_mode = True
    include_user_timelines = False
    selected_monitor_users = []
    chile_only = False
    export_only_high_views = False
    google_results_per_keyword = settings.default_google_results_per_keyword
    google_language = "es"
    google_lowercase_text = False
    google_min_delay = 4.0
    google_max_delay = 8.0

    if is_x_app_mode:
        simulation_mode = st.sidebar.toggle("Simulación sin API", value=True)
        strategy = st.sidebar.selectbox("Estrategia de consumo API", options=["Rápida", "Balanceada", "Profunda"], index=1)
        limit = st.sidebar.slider("Límite de resultados", min_value=20, max_value=settings.max_limit, value=settings.default_limit, step=20)
        use_cache = st.sidebar.toggle("Usar caché local", value=True)
        cache_ttl_hours = st.sidebar.slider("TTL caché (horas)", min_value=1, max_value=48, value=settings.default_cache_ttl_hours, step=1)
        incremental_mode = st.sidebar.toggle("Modo incremental: traer sólo posts nuevos", value=True)
        include_user_timelines = st.sidebar.toggle("Incluir timelines de usuarios monitoreados", value=False)
        if include_user_timelines:
            selected_monitor_users = st.sidebar.multiselect(
                "Usuarios para timeline",
                options=monitor_users,
                default=monitor_users[:2],
                format_func=lambda username: f"{monitor_accounts.get(username, username)} (@{username})",
            )
        chile_only = st.sidebar.toggle("Sólo posts hechos desde Chile (CL)", value=False)
        export_only_high_views = st.sidebar.toggle("Exportar sólo posts con viewCount > 1000", value=False)
    else:
        google_results_per_keyword = st.sidebar.slider(
            "Resultados Google por keyword",
            min_value=5,
            max_value=settings.max_google_results_per_keyword,
            value=settings.default_google_results_per_keyword,
            step=5,
        )
        google_language = st.sidebar.selectbox("Idioma Google", options=["es", "en"], index=0)
        google_lowercase_text = st.sidebar.toggle("Normalizar texto a minúsculas", value=False)
        st.sidebar.caption("Google puede bloquear consultas intensivas. Aunque el selector permita más, la app aplica un tope efectivo por keyword para reducir HTTP 429.")

    run = st.sidebar.button("Ejecutar monitoreo", width="stretch", type="primary")

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = date.today()

    return {
        "search_platform": search_platform,
        "x_search_mode": x_search_mode,
        "simulation_mode": simulation_mode,
        "selected_categories": selected_categories,
        "selected_people": selected_people,
        "selected_companies": selected_companies,
        "start_date": start_date,
        "end_date": end_date,
        "strategy": strategy,
        "limit": limit,
        "use_cache": use_cache,
        "cache_ttl_hours": cache_ttl_hours,
        "incremental_mode": incremental_mode,
        "include_user_timelines": include_user_timelines,
        "selected_monitor_users": selected_monitor_users,
        "chile_only": chile_only,
        "export_only_high_views": export_only_high_views,
        "google_results_per_keyword": google_results_per_keyword,
        "google_language": google_language,
        "google_lowercase_text": google_lowercase_text,
        "google_min_delay": google_min_delay,
        "google_max_delay": google_max_delay,
        "run": run,
    }
