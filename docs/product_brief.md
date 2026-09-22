# RetailPulse AI — Product Brief

## Producto
RetailPulse AI es una plataforma de analítica de demanda para retail que transforma ventas históricas, calendario/eventos y precios en métricas verificables, comparaciones por tienda/departamento y pronósticos de demanda.

## Usuario objetivo
- Gerencia comercial: entender dónde cambia la demanda y qué segmentos explican la variación.
- Analista BI: consultar KPIs con definiciones únicas y filtros controlados.
- Planificación: revisar pronósticos y error histórico por segmento.
- Equipo de datos: rastrear qué lote, transformación y modelo produjo cada cifra.

## Problema
Los equipos de retail pueden terminar con análisis dispersos y definiciones inconsistentes de métricas. RetailPulse AI centraliza el flujo desde datos crudos hasta KPIs, forecast y consulta asistida, conservando trazabilidad y reproducibilidad.

## Piloto del MVP
Dataset M5 Forecasting — Accuracy.

Subconjunto inicial configurable:
- 3 tiendas
- 2 departamentos

La selección concreta se definirá en configuración durante RP-02; no se incrustará en el código.

## Decisiones que habilita
1. Cómo evolucionan las unidades y el revenue_proxy en las últimas semanas.
2. Qué tiendas o departamentos explican la mayor variación.
3. Qué demanda se espera en el horizonte seleccionado y cuál es el error histórico.
4. Qué eventos o variaciones de precio coinciden con cambios de demanda.
5. Cómo se define cada métrica y de qué tabla/período proviene.

## MVP congelado
- Ingesta batch reproducible.
- Capas Bronze / Silver / Gold.
- Contratos y pruebas de calidad.
- KPIs y capa semántica SQL.
- Baseline de forecasting y modelo candidato.
- Dashboard Power BI de tres páginas.
- API FastAPI.
- Asistente de IA con herramientas de solo lectura y cifras verificables.
- Reproducibilidad local y README técnico.

## Restricciones y honestidad del producto
- M5 no contiene inventario real.
- revenue_proxy = units × sell_price; no representa ingreso contable auditado.
- Las alertas de demanda no implican causalidad.
- Cualquier escenario de reposición será simulado y estará rotulado como tal.
- El MVP debe funcionar localmente sin gasto obligatorio.

## Resultado demostrable
En menos de 3 minutos, una persona debe poder ver el flujo de datos, consultar KPIs, comparar tiendas/departamentos, revisar un forecast y obtener una respuesta del asistente con fuente, período y fecha de actualización.

## Criterio de éxito de RP-00
- El problema se explica en ~30 segundos.
- Cada función Must responde a una pregunta de negocio.
- Existe una lista explícita de exclusiones.
- No se agregan funciones nuevas al MVP sin moverlas al backlog.
