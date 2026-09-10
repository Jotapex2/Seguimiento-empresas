# Twitter Monitor App

Aplicación web en Streamlit para monitorear publicaciones de X/Twitter con foco en el sector sanitario, hídrico y regulatorio en Chile.

La integración está basada en `twitterapi.io`, no en la API oficial de X/Twitter.

## Características

- Monitoreo por categorías, empresas y personas.
- Integración HTTP con `twitterapi.io` usando `requests` y header `x-api-key`.
- Construcción de queries simples con batching automático.
- Post-procesamiento en Python:
  - filtro por idioma español
  - normalización de texto
  - matching inteligente por categoría, empresa y persona
  - detección básica de contexto chileno
  - eliminación de duplicados
- Scoring de relevancia y riesgo reputacional.
- Dashboard ejecutivo con KPIs, rankings y gráficos.
- Exportación a CSV y Excel.
- Envío de informe por correo con adjunto Excel vía SMTP.
- Análisis ejecutivo con DeepSeek Chat en cuatro secciones: industria sanitaria, ministro Iván Poduje, Louis de Grange y Nicolás Balmaceda.
- Modo simulación sin API para probar la UI.
- Caché local en disco para evitar consultas repetidas.
- Modo incremental para traer sólo posts nuevos por query.
- Estrategias de consumo API: `Rápida`, `Balanceada`, `Profunda`.

## Estructura

```text
twitter_monitor_app/
├── app.py
├── requirements.txt
├── .env.example
├── README.md
├── config/
│   └── settings.py
├── data/
│   └── keywords.py
├── services/
│   ├── twitter_client.py
│   ├── query_builder.py
│   ├── classifier.py
│   ├── scoring.py
│   └── exporter.py
├── utils/
│   ├── text_utils.py
│   └── helpers.py
└── components/
    ├── filters.py
    ├── metrics.py
    ├── charts.py
    └── tables.py
```

## Requisitos

- Python 3.10+
- API key de `twitterapi.io` para modo real

## Cómo obtener la API key

1. Crea una cuenta en `https://twitterapi.io/`
2. Ingresa al dashboard
3. Copia la API key
4. Crea un archivo `.env` a partir de `.env.example`

## Configuración

```bash
cp .env.example .env
```

Completa:

```env
TWITTERAPI_IO_KEY=your_api_key_here
BASE_URL=https://api.twitterapi.io
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=usuario@example.com
SMTP_PASSWORD=your_smtp_password
SMTP_USE_TLS=true
EMAIL_FROM=usuario@example.com
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_API_URL=https://api.deepseek.com/chat/completions
DEEPSEEK_MODEL=deepseek-chat
```

El envío de correo usa SMTP y adjunta el informe en formato Excel desde la sección de exportación. Si `DEEPSEEK_API_KEY` está configurada, el cuerpo del correo incluye las tres secciones de análisis y links relacionados.

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecución

```bash
streamlit run app.py
```

## Modo simulación sin API

La app activa por defecto el modo `Simulación sin API`. Esto permite:

- probar toda la UI
- validar filtros y exportación
- evitar consumo de créditos o rate limit

## Eficiencia de consumo API

La app incluye tres mecanismos para bajar costo:

- `Rápida`: limita batches y volumen total; sirve para exploración ejecutiva.
- `Balanceada`: punto medio para operación diaria.
- `Profunda`: usa más batches y deja crecer el volumen solicitado.
- `Usar caché local`: reutiliza respuestas recientes en `data/runtime/cache/`.
- `Modo incremental`: guarda el último `createdAt` por query y pide sólo contenido nuevo cuando es posible.

Persistencia local:

- histórico consolidado en `data/runtime/history.json`
- estado incremental en `data/runtime/incremental_state.json`
- respuestas cacheadas en `data/runtime/cache/`

## Endpoints usados

- `GET /twitter/tweet/advanced_search`
- `GET /twitter/user/last_tweets`

Autenticación:

- header `x-api-key`

## Manejo de limitaciones de twitterapi.io

- `twitterapi.io` es una API de terceros; la cobertura y semántica de búsqueda no son idénticas a la API oficial.
- Algunos operadores avanzados pueden funcionar de forma parcial o distinta según el endpoint.
- La app usa queries simples y compensa con filtros posteriores en Python.
- La documentación de `twitterapi.io` indica que en algunos endpoints `has_next_page` puede venir en `true` aunque no existan más resultados. Por eso el cliente corta si una página llega vacía.
- Algunas métricas como `viewCount` pueden venir nulas o no estar presentes.
- El endpoint de timeline de usuario puede ser costoso si se consulta de forma muy frecuente.

## Matching inteligente

Cada tweet procesado devuelve:

- `category_detected`
- `matched_keyword`
- lista de matches por:
  - categoría
  - empresa
  - persona
  - riesgo

## Notas de implementación

- Las queries largas se dividen en batches automáticos.
- Si el filtro `lang:es` no fuese soportado de forma consistente por la API, la app filtra idioma en Python.
- La detección de contexto chileno es heurística, basada en términos como `Chile`, `SISS`, `DGA`, `MOP`, regiones y `APR`.
