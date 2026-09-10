# DocumentaciÃ³n de Monitoreo con Serper.dev API

Este documento detalla la integraciÃ³n de la API de **Serper.dev** en el mÃ³dulo `google_social_monitor.py` para obtener resultados estables de LinkedIn y X/Twitter vÃ­a Google.

## Â¿Por quÃ© usar Serper.dev?

Google bloquea rÃ¡pidamente el "scraping" directo de su motor de bÃºsqueda cuando detecta trÃ¡fico automatizado. La API de Serper permite:

1.  **Estabilidad total:** No hay bloqueos (HTTP 429) ni captchas.
2.  **Cuota Gratuita:** El nivel gratuito ofrece **2,500 bÃºsquedas gratis** al mes sin tarjeta de crÃ©dito.
3.  **Formato JSON:** Respuesta directa y limpia, sin pelear con selectores CSS inestables.

## ConfiguraciÃ³n Paso a Paso

1.  Crea una cuenta en [https://serper.dev/](https://serper.dev/).
2.  Copia tu `API Key` desde el dashboard.
3.  Abre el archivo `.env` en `twitter_monitor_app/`.
4.  Pega tu key en la lÃ­nea correspondiente:
    ```env
    SERPER_API_KEY=tu_api_key_serper_aqui
    ```

## Cambios Implementados en el CÃ³digo

### 1. Batching de Keywords (OptimizaciÃ³n de Cuota)
Para no gastar tus 2,500 bÃºsquedas rÃ¡pidamente, el script agrupa las palabras clave de a 5 usando el operador `OR`.
- **Antes:** 50 keywords = 50 bÃºsquedas.
- **Ahora:** 50 keywords = 10 bÃºsquedas.

### 2. AtribuciÃ³n Inteligente
Al agrupar bÃºsquedas, un resultado puede venir por cualquiera de las 5 keywords del lote. El script analiza el tÃ­tulo y el snippet para asignar el resultado a la keyword que mÃ¡s encaje.

### 3. Mecanismo de Fallback (HÃ­brido)
El script es inteligente:
- Si detecta `SERPER_API_KEY` en el entorno, usa la API (Recomendado).
- Si no la detecta, intenta usar el scraping de Google como plan de reserva (Inestable).

## Estructura de la Query

Para LinkedIn, el script genera una consulta optimizada:
`site:linkedin.com ("Andess" OR "SISS" OR "Aguas Andinas" OR "Essbio" OR "Esval")`

Y filtra automÃ¡ticamente para quedarse solo con:
- `/posts/`
- `/feed/update/`
- `/pulse/`
- `/in/`
- `/company/`

## ValidaciÃ³n del LÃ­mite

Se incluyÃ³ el parÃ¡metro `results_per_batch` que solicita automÃ¡ticamente un volumen mayor de resultados (mÃ­nimo 30) cuando se agrupa por lotes, asegurando que todas las keywords tengan oportunidad de aparecer.

---
*DocumentaciÃ³n generada automÃ¡ticamente tras la implementaciÃ³n del flujo Serper.*
