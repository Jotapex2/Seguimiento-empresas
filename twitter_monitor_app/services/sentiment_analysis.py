from __future__ import annotations

import json
import re
from collections import Counter
from typing import Dict, Iterable, List

import pandas as pd
import requests

from config.settings import get_settings, is_secret_configured
from services.runtime_store import load_cache, make_cache_key, save_cache
from utils.text_utils import normalize_text

SENTIMENTS = ("positivo", "negativo", "neutral")

# Sube esta versión al cambiar los prompts de clasificación para invalidar la
# caché anterior; si no, seguirían usándose clasificaciones hechas con el prompt viejo.
SENTIMENT_PROMPT_VERSION = 2

POSITIVE_LEXICON = {
    "bueno",
    "buena",
    "excelente",
    "mejora",
    "mejoran",
    "mejorar",
    "logro",
    "logros",
    "avance",
    "avances",
    "inversion",
    "inversiones",
    "beneficio",
    "beneficios",
    "exito",
    "exitoso",
    "positivo",
    "confianza",
    "apoyo",
    "solucion",
    "soluciones",
    "innovacion",
    "sostenible",
    "crecimiento",
    "oportunidad",
    "oportunidades",
    "agradece",
    "felicita",
    "destaca",
    "premiado",
    "reconocimiento",
    "transparencia",
    "eficiente",
    "eficiencia",
}

NEGATIVE_LEXICON = {
    "malo",
    "mala",
    "crisis",
    "problema",
    "problemas",
    "falla",
    "fallas",
    "sancion",
    "sanciones",
    "multa",
    "multas",
    "corte",
    "cortes",
    "racionamiento",
    "contaminacion",
    "denuncia",
    "denuncias",
    "corrupcion",
    "reclamo",
    "reclamos",
    "protesta",
    "protestas",
    "deuda",
    "perdida",
    "perdidas",
    "riesgo",
    "fallo",
    "demanda",
    "emergencia",
    "alerta",
    "deficiente",
    "incumplimiento",
    "critica",
    "criticas",
    "rechazo",
    "conflicto",
    "inseguridad",
    "falta",
}

# Palabras funcionales del español: conectores, preposiciones, artículos,
# pronombres y verbos auxiliares. No aportan significado a una nube de palabras,
# así que se descartan. Van sin tildes porque el texto se normaliza antes de
# tokenizar, y el tokenizador solo considera palabras de 4 letras o más.
STOPWORDS = {
    # conectores y marcadores del discurso
    "ademas",
    "apenas",
    "aunque",
    "casi",
    "como",
    "cuando",
    "cuanta",
    "cuantas",
    "cuanto",
    "cuantos",
    "entonces",
    "inclusive",
    "incluso",
    "jamas",
    "luego",
    "mientras",
    "nunca",
    "ojala",
    "pero",
    "porque",
    "pues",
    "quizas",
    "siempre",
    "sino",
    "siquiera",
    "solo",
    "tambien",
    "tampoco",
    "todavia",
    # fragmentos de conectores compuestos ("sin embargo", "no obstante",
    # "a pesar de", "respecto a", "debido a", "a través de")
    "debido",
    "embargo",
    "obstante",
    "pesar",
    "pese",
    "respecto",
    "traves",
    # preposiciones y locuciones prepositivas
    "ante",
    "bajo",
    "cabe",
    "contra",
    "desde",
    "durante",
    "entre",
    "hacia",
    "hasta",
    "mediante",
    "para",
    "segun",
    "sobre",
    "tras",
    # artículos y determinantes
    "aquel",
    "aquella",
    "aquellas",
    "aquellos",
    "cada",
    "cual",
    "cuales",
    "esas",
    "esos",
    "esta",
    "estas",
    "este",
    "esto",
    "estos",
    "menos",
    "mucha",
    "muchas",
    "mucho",
    "muchos",
    "ningun",
    "ninguna",
    "otra",
    "otras",
    "otro",
    "otros",
    "poca",
    "pocas",
    "poco",
    "pocos",
    "tanta",
    "tantas",
    "tanto",
    "tantos",
    "toda",
    "todas",
    "todo",
    "todos",
    "unas",
    "unos",
    # pronombres
    "aquello",
    "ellas",
    "ellos",
    "misma",
    "mismo",
    "nosotras",
    "nosotros",
    "nuestra",
    "nuestras",
    "nuestro",
    "nuestros",
    "quien",
    "quienes",
    "suya",
    "suyas",
    "suyo",
    "suyos",
    "usted",
    "ustedes",
    # adverbios de lugar y tiempo
    "abajo",
    "ahora",
    "alli",
    "alla",
    "antes",
    "aqui",
    "arriba",
    "despues",
    "donde",
    "ayer",
    # verbos auxiliares y copulativos frecuentes
    "eran",
    "eras",
    "eres",
    "esta",
    "estaba",
    "estaban",
    "estan",
    "fueron",
    "haber",
    "habia",
    "habian",
    "habra",
    "habran",
    "hace",
    "hacen",
    "haya",
    "hayan",
    "hemos",
    "hubo",
    "puede",
    "pueden",
    "sean",
    "ser",
    "sera",
    "seran",
    "sido",
    "son",
    "tiene",
    "tienen",
    # términos geográficos y temporales genéricos
    "anos",
    "chile",
    "chilena",
    "chileno",
    "dias",
}

# Palabras de rubro o genéricas del mundo corporativo: describen el tema de la
# publicación, no una emoción, así que nunca deberían aparecer en las nubes de
# sentimiento (van sin tildes porque el texto se normaliza antes de tokenizar).
SECTOR_STOPWORDS = {
    # rubros e industrias
    "mineria",
    "minera",
    "mineras",
    "minero",
    "mineros",
    "automotriz",
    "automotrices",
    "automovil",
    "automoviles",
    "vehiculos",
    "agua",
    "aguas",
    "hidrico",
    "hidrica",
    "energia",
    "energetica",
    "energetico",
    "electricidad",
    "electrica",
    "electrico",
    "sanitaria",
    "sanitario",
    "sanitarias",
    "saneamiento",
    "retail",
    "comercio",
    "supermercados",
    "banca",
    "bancaria",
    "bancario",
    "financiera",
    "financiero",
    "seguros",
    "telecomunicaciones",
    "telefonia",
    "construccion",
    "inmobiliaria",
    "agricultura",
    "agricola",
    "pesca",
    "salmon",
    "forestal",
    "transporte",
    "portuario",
    "logistica",
    # genéricos corporativos y geográficos
    "empresa",
    "empresas",
    "compania",
    "companias",
    "grupo",
    "holding",
    "sector",
    "industria",
    "industrial",
    "rubro",
    "mercado",
    "accionistas",
    "region",
    "regional",
    "nacional",
    "pais",
    "comuna",
    "informe",
    "reporte",
    "reportan",
    "anuncio",
    "anunciaron",
}

_WORD_PATTERN = re.compile(r"[a-z]{4,}")


class SentimentAnalysisError(RuntimeError):
    pass


def _first_value(row, columns: Iterable[str]) -> str:
    for column in columns:
        value = row.get(column)
        if value is None:
            continue
        if isinstance(value, float) and pd.isna(value):
            continue
        text = str(value).strip()
        if text and text.lower() != "nan":
            return text
    return ""


def post_key(row) -> str:
    return _first_value(row, ("id", "link", "url"))


def post_text(row) -> str:
    text = _first_value(row, ("text",))
    if text:
        return text
    titulo = _first_value(row, ("titulo",))
    descripcion = _first_value(row, ("descripcion",))
    return " ".join(part for part in (titulo, descripcion) if part).strip()


def _tokenize(text: str, extra_stopwords: Iterable[str] = ()) -> List[str]:
    stopwords = STOPWORDS | {word.casefold() for word in extra_stopwords}
    normalized = normalize_text(text)
    return [word for word in _WORD_PATTERN.findall(normalized) if word not in stopwords]


def _lexicon_sentiment(text: str) -> str:
    words = set(_tokenize(text))
    positive = len(words & POSITIVE_LEXICON)
    negative = len(words & NEGATIVE_LEXICON)
    if positive > negative:
        return "positivo"
    if negative > positive:
        return "negativo"
    return "neutral"


def _strip_json_fences(content: str) -> str:
    text = (content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _post_deepseek(*, api_key: str, api_url: str, model: str, user_prompt: str, system_prompt: str, timeout: int = 60) -> str:
    if not is_secret_configured(api_key):
        raise SentimentAnalysisError("Falta configurar una DEEPSEEK_API_KEY válida en `.env`.")
    response = requests.post(
        api_url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
            "max_tokens": 2000,
        },
        timeout=timeout,
    )
    if response.status_code >= 400:
        raise SentimentAnalysisError(f"DeepSeek devolvió HTTP {response.status_code}: {response.text[:300]}")
    payload = response.json()
    try:
        return payload["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise SentimentAnalysisError("Respuesta inesperada de DeepSeek.") from exc


def _parse_classifications(content: str) -> Dict[str, str]:
    text = _strip_json_fences(content)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1 or end <= start:
            raise SentimentAnalysisError("DeepSeek no devolvió un arreglo JSON válido.")
        parsed = json.loads(text[start : end + 1])

    if isinstance(parsed, dict):
        parsed = parsed.get("resultados") or parsed.get("sentimientos") or []
    if not isinstance(parsed, list):
        raise SentimentAnalysisError("Formato de respuesta inesperado de DeepSeek.")

    result: Dict[str, str] = {}
    for item in parsed:
        if not isinstance(item, dict):
            continue
        identifier = str(item.get("id", "")).strip()
        label = str(item.get("sentimiento", "")).strip().lower()
        if identifier and label in SENTIMENTS:
            result[identifier] = label
    if not result:
        raise SentimentAnalysisError("DeepSeek no clasificó ninguna publicación.")
    return result


def _chunks(items: List[dict], size: int) -> Iterable[List[dict]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def _collect_posts(df: pd.DataFrame, max_posts: int) -> List[dict]:
    posts: List[dict] = []
    seen: set[str] = set()
    for _, row in df.iterrows():
        key = post_key(row)
        text = post_text(row)
        if not key or not text or key in seen:
            continue
        seen.add(key)
        posts.append({"id": key, "text": text[:600]})
        if len(posts) >= max_posts:
            break
    return posts


def classify_sentiments(
    df: pd.DataFrame,
    *,
    api_key: str,
    api_url: str,
    model: str,
    batch_size: int = 50,
    max_posts: int = 300,
    cache_ttl_hours: int | None = None,
) -> tuple[Dict[str, str], bool]:
    """Clasifica cada publicación como positivo/negativo/neutral usando DeepSeek.

    Devuelve (sentimientos_por_id, uso_fallback). Si falta la API key o falla la
    API se usa un clasificador léxico local y `uso_fallback` queda en True.
    """
    posts = _collect_posts(df, max_posts)
    sentiments: Dict[str, str] = {}
    used_fallback = False
    if not posts:
        return sentiments, used_fallback
    if not is_secret_configured(api_key):
        return {post["id"]: _lexicon_sentiment(post["text"]) for post in posts}, True

    ttl = cache_ttl_hours if cache_ttl_hours is not None else get_settings().default_cache_ttl_hours
    system_prompt = (
        "Eres un analista de reputación corporativa en Chile. Clasificas la actitud de cada "
        "publicación hacia la empresa o entidad mencionada, no el tema general del texto. "
        "Respondes exclusivamente con el JSON solicitado, sin texto adicional ni explicaciones."
    )
    for batch in _chunks(posts, batch_size):
        cache_key = make_cache_key(
            "sentiment",
            {
                "prompt_version": SENTIMENT_PROMPT_VERSION,
                "model": model,
                "posts": [post["id"] for post in batch],
                "texts": [post["text"] for post in batch],
            },
        )
        cached = load_cache(cache_key, ttl)
        if isinstance(cached, dict):
            sentiments.update(cached)
            continue

        user_prompt = (
            "Clasifica la actitud de cada publicación hacia la empresa o entidad mencionada.\n\n"
            "Criterios:\n"
            "- positivo: logros, buenas noticias, inversiones, reconocimientos, acuerdos, mejoras, "
            "crecimiento, apoyo o reputación favorable.\n"
            "- negativo: sanciones, multas, incumplimientos, crisis, accidentes, contaminación, "
            "cortes de servicio, denuncias, críticas, conflictos, pérdidas o daño reputacional.\n"
            "- neutral: información descriptiva, datos, contexto sectorial o menciones sin juicio de valor.\n\n"
            "Reglas:\n"
            "- Mencionar un rubro o sector (minería, energía, agua, automotriz, retail, banca, etc.) "
            "NO define el sentimiento por sí solo.\n"
            "- Una noticia informativa es neutral aunque trate un tema serio; el sentimiento requiere "
            "una valoración o un hecho positivo o negativo concreto.\n"
            "- No marques negativo solo por el contexto regulatorio o por el vocabulario del sector.\n"
            "- Evalúa la actitud hacia la entidad, no el tono general del tema.\n\n"
            "Responde EXCLUSIVAMENTE con un arreglo JSON con la forma "
            '[{"id": "<id>", "sentimiento": "positivo|negativo|neutral"}], sin texto adicional, '
            "un objeto por publicación y sin omitir ninguna.\n\n"
            "Publicaciones:\n"
            + json.dumps([{"id": post["id"], "texto": post["text"]} for post in batch], ensure_ascii=False)
        )
        try:
            content = _post_deepseek(
                api_key=api_key,
                api_url=api_url,
                model=model,
                user_prompt=user_prompt,
                system_prompt=system_prompt,
            )
            classifications = _parse_classifications(content)
            for post in batch:
                classifications.setdefault(post["id"], _lexicon_sentiment(post["text"]))
        except (SentimentAnalysisError, requests.RequestException, json.JSONDecodeError):
            used_fallback = True
            classifications = {post["id"]: _lexicon_sentiment(post["text"]) for post in batch}

        save_cache(cache_key, classifications)
        sentiments.update(classifications)

    return sentiments, used_fallback


def _discriminative_counts(
    positive: Counter,
    negative: Counter,
    *,
    min_count: int = 1,
    ratio: float = 2.0,
) -> tuple[Counter, Counter]:
    """Deja solo las palabras que distinguen un sentimiento del otro.

    Una palabra frecuente en ambas clases (p. ej. "mineras", "automotriz") es
    vocabulario del tema, no una señal de emoción, así que no sirve en una nube
    de sentimiento. Solo se conserva una palabra si aparece al menos `ratio`
    veces más en su clase que en la contraria.
    """
    positive_kept = Counter(
        {word: count for word, count in positive.items() if count >= min_count and count >= ratio * negative.get(word, 0)}
    )
    negative_kept = Counter(
        {word: count for word, count in negative.items() if count >= min_count and count >= ratio * positive.get(word, 0)}
    )
    return positive_kept, negative_kept


def build_sentiment_word_frequencies(
    df: pd.DataFrame,
    sentiments: Dict[str, str],
    *,
    top_n: int = 120,
    extra_stopwords: Iterable[str] = (),
    discriminative: bool = True,
    ratio: float = 2.0,
) -> tuple[Dict[str, int], Dict[str, int], pd.DataFrame]:
    positive: Counter = Counter()
    negative: Counter = Counter()
    ignore_words = set(SECTOR_STOPWORDS) | {word.casefold() for word in extra_stopwords}
    for _, row in df.iterrows():
        label = sentiments.get(post_key(row))
        if label == "positivo":
            positive.update(_tokenize(post_text(row), ignore_words))
        elif label == "negativo":
            negative.update(_tokenize(post_text(row), ignore_words))

    if discriminative:
        positive, negative = _discriminative_counts(positive, negative, ratio=ratio)

    positive_freq = dict(positive.most_common(top_n))
    negative_freq = dict(negative.most_common(top_n))
    rows = [{"sentimiento": "positivo", "palabra": word, "frecuencia": count} for word, count in positive.most_common(top_n)]
    rows += [{"sentimiento": "negativo", "palabra": word, "frecuencia": count} for word, count in negative.most_common(top_n)]
    words_df = pd.DataFrame(rows, columns=["sentimiento", "palabra", "frecuencia"])
    return positive_freq, negative_freq, words_df


def build_wordcloud_figure(frequencies: Dict[str, int], colormap: str):
    import matplotlib.pyplot as plt
    from wordcloud import WordCloud

    figure, axes = plt.subplots(figsize=(8, 4))
    if frequencies:
        cloud = WordCloud(
            width=800,
            height=400,
            background_color="white",
            colormap=colormap,
            max_words=100,
            prefer_horizontal=0.9,
            collocations=False,
        ).generate_from_frequencies(dict(frequencies))
        axes.imshow(cloud, interpolation="bilinear")
    else:
        axes.text(0.5, 0.5, "Sin palabras para mostrar", ha="center", va="center", fontsize=14)
    axes.axis("off")
    figure.tight_layout()
    return figure
