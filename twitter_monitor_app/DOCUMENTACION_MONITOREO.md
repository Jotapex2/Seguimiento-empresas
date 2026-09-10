# Documentación del monitoreo

## Objetivo

Este documento resume los ajustes hechos al catálogo de monitoreo y a la estrategia de consumo de `twitterapi.io`, para dejar trazabilidad técnica y facilitar futuras mantenciones.

## Cambios realizados

### 1. Recorte del catálogo de keywords

Se simplificó el catálogo base definido en [data/keywords.py](F:\SeguimientoAgua\twitter_monitor_app\data\keywords.py) con estos criterios:

- eliminar redundancias entre categorías
- sacar términos demasiado amplios o ruidosos
- dejar entidades con relación directa al monitoreo sectorial
- reducir personas periféricas que agregaban conversación política no relevante

### 2. Personas priorizadas

La lista priorizada actual quedó acotada a:

- José Antonio Kast
- Iván Poduje
- Louis de Grange
- Nicolás Balmaceda
- Jorge Quiroz
- Joaquín Daga

Estas personas aparecen tanto en `PEOPLE` como en `PRIORITY_PEOPLE`, y la categoría `Líderes del sector` quedó alineada con esa lista.

### 3. Estrategias para reducir consumo API

Se implementaron tres mejoras concretas:

- no consultar todas las categorías por defecto si el usuario no selecciona filtros
- aplicar corte temprano cuando ya se alcanza el volumen objetivo de la estrategia
- consultar timelines solo para usuarios seleccionados explícitamente

## Estado actual del catálogo

### Categorías vigentes

El bloque `SECTOR_TOPICS` quedó reducido y orientado a señales más precisas:

- `Andess`
- `Regulación sanitaria`
- `Industria sanitaria`
- `Empresas asociadas`
- `Agua Potable Rural`
- `Agua, sequía y cambio climático`
- `Líderes del sector`
- `Riesgo regulatorio`

### Empresas vigentes

Se mantienen empresas sanitarias y actores directamente relacionados:

- Andess
- Aguas del Altiplano
- Aguas Antofagasta
- Nueva Atacama
- Aguas del Valle
- Aguas Andinas
- Sacyr Agua
- Essbio
- Esval
- Nuevosur
- Aguas Araucanía
- Suralis
- Aguas Patagonia
- Aguas Magallanes
- SMAPA

### Personas vigentes

El bloque `PEOPLE` quedó acotado a:

- Presidente José Antonio Kast
- Iván Poduje
- Louis de Grange
- Nicolás Balmaceda
- Jorge Quiroz
- Joaquín Daga

## Cambios de comportamiento en la app

### No buscar todo por defecto

Antes, si no había selección de filtros, [services/query_builder.py](F:\SeguimientoAgua\twitter_monitor_app\services\query_builder.py) armaba queries para todas las categorías.

Ahora:

- si no hay categorías, personas o empresas seleccionadas, no se genera plan de query automáticamente
- si tampoco se seleccionan timelines, la app devuelve un error guiando al usuario a elegir al menos un filtro

Impacto:

- baja fuerte de llamadas innecesarias
- menos ruido en resultados
- mejor control del costo por corrida

### Corte temprano por volumen objetivo

En [app.py](F:\SeguimientoAgua\twitter_monitor_app\app.py), dentro de `collect_api_data`, ahora se corta la ejecución cuando `collected` alcanza el `effective_limit` de la estrategia elegida.

Impacto:

- evita seguir haciendo requests cuando ya se juntó suficiente material
- aprovecha mejor estrategias como `Rápida` y `Balanceada`
- reduce paginación y llamadas de timeline innecesarias

### Timelines selectivas

En [components/filters.py](F:\SeguimientoAgua\twitter_monitor_app\components\filters.py):

- el toggle `Incluir timelines de usuarios monitoreados` sigue existiendo
- pero ahora, al activarlo, aparece un selector de usuarios
- la app consulta solo los usuarios elegidos en `selected_monitor_users`

En [app.py](F:\SeguimientoAgua\twitter_monitor_app\app.py):

- ya no se recorren automáticamente todos los `monitor_users`
- el límite por timeline se ajusta según capacidad restante

Impacto:

- reduce llamadas fijas por corrida
- permite usar timelines como inspección dirigida, no como costo permanente

## Cambios en la UI

La barra lateral ahora incorpora este flujo:

1. seleccionar categorías, personas y empresas
2. opcionalmente activar timelines
3. si timelines está activo, elegir usuarios concretos
4. ejecutar monitoreo

Además, se corrigieron tildes y textos visibles para el usuario.

## Archivos modificados

- [data/keywords.py](F:\SeguimientoAgua\twitter_monitor_app\data\keywords.py)
- [services/query_builder.py](F:\SeguimientoAgua\twitter_monitor_app\services\query_builder.py)
- [components/filters.py](F:\SeguimientoAgua\twitter_monitor_app\components\filters.py)
- [app.py](F:\SeguimientoAgua\twitter_monitor_app\app.py)

## Validación realizada

Se validó sintaxis Python con:

```bash
python -m py_compile app.py components\filters.py services\query_builder.py data\keywords.py
```

Resultado:

- compilación exitosa

Limitación:

- no se pudo probar la UI en este entorno porque `streamlit` no está instalado

## Recomendaciones siguientes

Las siguientes mejoras pueden seguir bajando costo:

- TTL de caché distinto por tipo de query
- desactivar por defecto categorías con bajo rendimiento histórico
- registrar métricas por batch para podar queries malas
- introducir una estrategia de dos etapas: discovery y deep dive

## Resumen ejecutivo

El monitoreo quedó más estricto, con menos ruido y menor costo de API.

Los principales resultados son:

- menos keywords redundantes
- menos personas no esenciales
- cero consultas automáticas a todas las categorías cuando no hay filtros
- corte temprano al llegar al volumen objetivo
- timelines solo bajo selección explícita
