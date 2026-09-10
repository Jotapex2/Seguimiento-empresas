from __future__ import annotations

import json
from typing import Dict, List

import streamlit as st


def _dict_to_lines(mapping: Dict[str, List[str]]) -> str:
    return "\n".join(f"{key}: {', '.join(values)}" for key, values in mapping.items())


def _lines_to_dict(raw_text: str) -> Dict[str, List[str]]:
    parsed: Dict[str, List[str]] = {}
    for line in raw_text.splitlines():
        if not line.strip() or ":" not in line:
            continue
        key, values = line.split(":", 1)
        items = [item.strip() for item in values.replace(";", ",").split(",") if item.strip()]
        if key.strip():
            parsed[key.strip()] = items
    return parsed


def _list_to_text(items: List[str]) -> str:
    return "\n".join(items)


def _text_to_list(raw_text: str) -> List[str]:
    return [line.strip() for line in raw_text.replace(",", "\n").splitlines() if line.strip()]


def render_taxonomy_editor(catalog: dict, default_catalog: dict) -> dict:
    st.subheader("Editor de keywords y entidades")
    st.caption("Edita categorías, empresas, personas, términos de riesgo y usuarios monitoreados desde la UI. Los cambios viven en la sesión actual.")

    with st.expander("Abrir editor", expanded=False):
        uploaded = st.file_uploader("Cargar catálogo JSON", type=["json"])
        if uploaded is not None:
            imported_catalog = json.load(uploaded)
            st.session_state["catalog"] = imported_catalog
            st.success("Catálogo cargado desde JSON.")
            st.rerun()

        with st.form("taxonomy_editor_form"):
            sector_topics_text = st.text_area("Categorías y keywords", value=_dict_to_lines(catalog["sector_topics"]), height=240)
            companies_text = st.text_area("Empresas y aliases", value=_dict_to_lines(catalog["companies"]), height=180)
            people_text = st.text_area("Personas y aliases", value=_dict_to_lines(catalog["people"]), height=180)
            priority_people_text = st.text_area("Personas prioritarias", value=_list_to_text(catalog["priority_people"]), height=120)
            risk_terms_text = st.text_area("Términos de riesgo reputacional", value=_list_to_text(catalog["risk_terms"]), height=140)
            context_terms_text = st.text_area("Términos de contexto chileno", value=_list_to_text(catalog["chile_context_terms"]), height=140)
            monitor_users_text = st.text_area("Usuarios monitoreados", value=_list_to_text(catalog["monitor_users"]), height=120)

            save = st.form_submit_button("Guardar cambios", type="primary")
            reset = st.form_submit_button("Restaurar catálogo base")

        if save:
            updated_catalog = {
                "sector_topics": _lines_to_dict(sector_topics_text),
                "companies": _lines_to_dict(companies_text),
                "people": _lines_to_dict(people_text),
                "priority_people": _text_to_list(priority_people_text),
                "risk_terms": _text_to_list(risk_terms_text),
                "chile_context_terms": _text_to_list(context_terms_text),
                "monitor_users": _text_to_list(monitor_users_text),
            }
            st.session_state["catalog"] = updated_catalog
            st.success("Catálogo actualizado en la sesión.")
            st.rerun()

        if reset:
            st.session_state["catalog"] = default_catalog
            st.success("Catálogo restaurado.")
            st.rerun()

        st.download_button(
            "Descargar catálogo JSON",
            data=json.dumps(catalog, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name="monitor_catalog.json",
            mime="application/json",
        )

    return st.session_state.get("catalog", catalog)
