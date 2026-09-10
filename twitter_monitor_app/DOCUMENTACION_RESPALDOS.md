# DocumentaciÃ³n de Respaldos (Plan B y Plan C)

Este mÃ³dulo ahora soporta tres APIs de bÃºsqueda para garantizar que el monitoreo nunca se detenga. El script seleccionarÃ¡ automÃ¡ticamente la mejor opciÃ³n disponible basÃ¡ndose en las keys configuradas en el `.env`.

## Plan A: Serper.dev (Recomendado)
- **Cuota:** 2,500 bÃºsquedas gratis.
- **Key:** `SERPER_API_KEY`.
- **Obtener en:** [serper.dev](https://serper.dev/).

## Plan B: Google Custom Search API (Oficial)
- **Cuota:** 100 bÃºsquedas GRATIS al dÃ­a.
- **Keys:** `GOOGLE_API_KEY` y `GOOGLE_CX`.
- **Pasos para obtener:**
  1. Crea un proyecto en [Google Cloud Console](https://console.cloud.google.com/).
  2. Habilita "Custom Search API" y crea una API Key.
  3. Ve a [Programmable Search Engine](https://programmablesearchengine.google.com/), crea un buscador, aÃ±ade `linkedin.com` y `x.com` como sitios permitidos, y copia el "Search Engine ID" (CX).

## Plan C: SearchAPI.io (Respaldo Extra)
- **Cuota:** 100 bÃºsquedas gratis totales (crÃ©dito de bienvenida).
- **Key:** `SEARCHAPI_API_KEY`.
- **Obtener en:** [searchapi.io](https://www.searchapi.io/).

---

### Funcionamiento del Respaldo
El script intenta las APIs en este orden: **Serper -> Google Official -> SearchAPI**. Si la primera falla o no tiene Key, salta a la siguiente. Solo si fallan todas, el sistema avisarÃ¡ que no hay resultados disponibles.
