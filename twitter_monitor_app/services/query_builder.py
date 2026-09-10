from __future__ import annotations

from typing import Dict, Iterable, List

from utils.helpers import chunk_list


def build_simple_or_query(terms: Iterable[str], phrase_wrap: bool = True) -> str:
    cleaned = []
    for term in terms:
        term = term.strip()
        if not term:
            continue
        cleaned.append(f"\"{term}\"" if phrase_wrap and " " in term else term)
    return " OR ".join(cleaned)


def build_sector_batches(selected_categories: List[str], sector_topics: Dict[str, List[str]], batch_size: int = 15) -> List[Dict[str, str]]:
    batches: List[Dict[str, str]] = []
    for category in selected_categories:
        terms = sector_topics.get(category, [])
        for group in chunk_list(terms, batch_size):
            query = f"({build_simple_or_query(group)})"
            batches.append({"category": category, "query": query})
    return batches


def build_entity_batches(
    selected_people: List[str],
    selected_companies: List[str],
    people: Dict[str, List[str]],
    companies: Dict[str, List[str]],
    batch_size: int = 15,
) -> List[Dict[str, str]]:
    batches: List[Dict[str, str]] = []
    for person in selected_people:
        aliases = people.get(person, [])
        for group in chunk_list(aliases, batch_size):
            batches.append({"category": "Personas", "query": f"({build_simple_or_query(group)})", "entity": person})

    for company in selected_companies:
        aliases = companies.get(company, [])
        for group in chunk_list(aliases, batch_size):
            batches.append({"category": "Empresas", "query": f"({build_simple_or_query(group)})", "entity": company})
    return batches


def build_query_plan(selected_categories: List[str], selected_people: List[str], selected_companies: List[str], catalog: dict) -> List[Dict[str, str]]:
    plan = build_sector_batches(selected_categories, catalog["sector_topics"]) + build_entity_batches(
        selected_people,
        selected_companies,
        catalog["people"],
        catalog["companies"],
    )
    return plan


def append_date_operators(query: str, start_date=None, end_date=None) -> str:
    operators = []
    if start_date:
        operators.append(f"since:{start_date.isoformat()}_00:00:00_UTC")
    if end_date:
        operators.append(f"until:{end_date.isoformat()}_23:59:59_UTC")
    suffix = " ".join(operators).strip()
    return f"{query} {suffix}".strip()
