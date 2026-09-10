from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd
import requests


@dataclass(frozen=True)
class AnalysisSection:
    title: str
    focus: str
    terms: tuple[str, ...]


class DeepSeekAnalysisError(RuntimeError):
    pass


GENERAL_SECTION = AnalysisSection(
    title="Implicancias para la industria sanitaria",
    focus=(
        "Analiza las implicancias para la industria del agua potable y servicios "
        "sanitarios en Chile. Identifica riesgos regulatorios, reputacionales, "
        "operacionales y oportunidades de gestión pública."
    ),
    terms=(
        "agua potable",
        "sanitaria",
        "sanitarias",
        "aguas",
        "siss",
        "dga",
        "mop",
        "apr",
        "tarifas",
        "racionamiento",
        "sequia",
        "fiscalizacion",
        "sanciones",
    ),
)


def build_analysis_sections(catalog: dict) -> tuple[AnalysisSection, ...]:
    priority_people = catalog.get("priority_people", [])
    people_aliases = catalog.get("people", {})

    sections: list[AnalysisSection] = [GENERAL_SECTION]
    for person in priority_people:
        aliases = tuple(people_aliases.get(person, []))
        if not aliases:
            continue
        sections.append(
            AnalysisSection(
                title=f"Dichos y actividades de {person}",
                focus=(
                    f"Resume dichos, señales, actividades o menciones vinculadas a {person} "
                    "sobre agua potable, servicios sanitarios, infraestructura hídrica, "
                    "regulación o riesgo sectorial."
                ),
                terms=aliases,
            )
        )
    return tuple(sections)


def _row_text(row: pd.Series) -> str:
    parts = [
        row.get("text", ""),
        row.get("titulo", ""),
        row.get("descripcion", ""),
        row.get("category_detected", ""),
        row.get("matched_keyword", ""),
        row.get("keyword", ""),
        row.get("author_name", ""),
        row.get("author_username", ""),
    ]
    return " ".join(str(part or "") for part in parts).casefold()


def _row_url(row: pd.Series) -> str:
    for column in ("url", "post_url", "link"):
        value = row.get(column, "")
        if isinstance(value, str) and value.startswith("http"):
            return value
    tweet_id = row.get("id", "")
    if tweet_id:
        return f"https://x.com/i/web/status/{tweet_id}"
    return ""


def _row_summary(row: pd.Series) -> str:
    text = row.get("text") or row.get("descripcion") or row.get("titulo") or ""
    author = row.get("author_username") or row.get("author_name") or row.get("platform") or ""
    date = row.get("createdAt") or row.get("fecha") or ""
    keyword = row.get("matched_keyword") or row.get("keyword") or row.get("category_detected") or ""
    url = _row_url(row)
    return (
        f"- Fecha: {date}\n"
        f"  Autor/fuente: {author}\n"
        f"  Keyword/categoría: {keyword}\n"
        f"  Texto: {str(text)[:600]}\n"
        f"  Link: {url}"
    )


def section_cache_payload(section: AnalysisSection, rows: pd.DataFrame) -> dict:
    evidence = []
    for _, row in rows.iterrows():
        evidence.append(
            {
                "id": row.get("id", ""),
                "url": _row_url(row),
                "text": str(row.get("text") or row.get("descripcion") or row.get("titulo") or "")[:600],
                "keyword": row.get("matched_keyword") or row.get("keyword") or row.get("category_detected") or "",
                "date": row.get("createdAt") or row.get("fecha") or "",
            }
        )
    return {
        "title": section.title,
        "focus": section.focus,
        "terms": section.terms,
        "evidence": evidence,
    }


def select_related_rows(df: pd.DataFrame, terms: Iterable[str], fallback_limit: int = 8, fallback_to_all: bool = True) -> pd.DataFrame:
    if df.empty:
        return df
    normalized_terms = tuple(term.casefold() for term in terms)
    mask = df.apply(lambda row: any(term in _row_text(row) for term in normalized_terms), axis=1)
    related = df.loc[mask].copy()
    if related.empty and fallback_to_all:
        related = df.copy()

    sort_columns = [column for column in ("relevance_score", "relevancia_score", "risk_score") if column in related.columns]
    if sort_columns:
        related = related.sort_values(sort_columns, ascending=False)
    return related.head(fallback_limit)


def related_links(rows: pd.DataFrame) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()
    for _, row in rows.iterrows():
        url = _row_url(row)
        if url and url not in seen:
            seen.add(url)
            links.append(url)
    return links


def build_section_prompt(section: AnalysisSection, rows: pd.DataFrame) -> str:
    source_items = "\n\n".join(_row_summary(row) for _, row in rows.iterrows())
    return (
        "Eres un analista senior de asuntos públicos en Chile. "
        "Usa exclusivamente los posts entregados; si no hay evidencia suficiente, dilo explícitamente. "
        "No inventes hechos ni atribuciones.\n\n"
        f"Sección: {section.title}\n"
        f"Foco: {section.focus}\n\n"
        "Redacta en español un análisis ejecutivo de 2 a 4 bullets, concreto y accionable. "
        "Distingue implicancias, riesgos y señales relevantes cuando corresponda.\n\n"
        f"Posts disponibles:\n{source_items or 'Sin posts relacionados.'}"
    )


def request_deepseek_analysis(
    *,
    api_key: str,
    api_url: str,
    model: str,
    section: AnalysisSection,
    rows: pd.DataFrame,
    timeout: int = 45,
) -> str:
    if not api_key:
        raise DeepSeekAnalysisError("Falta configurar DEEPSEEK_API_KEY en `.env`.")
    if rows.empty:
        return "No hay posts relacionados suficientes para generar análisis."

    response = requests.post(
        api_url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": "Responde sólo en español, con criterio ejecutivo y sin inventar antecedentes."},
                {"role": "user", "content": build_section_prompt(section, rows)},
            ],
            "temperature": 0.2,
            "max_tokens": 650,
        },
        timeout=timeout,
    )
    if response.status_code >= 400:
        raise DeepSeekAnalysisError(f"DeepSeek devolvió HTTP {response.status_code}: {response.text[:300]}")

    payload = response.json()
    try:
        return payload["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise DeepSeekAnalysisError("Respuesta inesperada de DeepSeek.") from exc
