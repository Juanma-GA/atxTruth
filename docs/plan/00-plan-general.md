# atxTruth — Plan general
 
Source of truth de Customer Services: catálogo de servicios + referencias de proyecto en Postgres,
y generación determinista de PowerPoint, HTML, Markdown y Excel. Se empieza por las Referencias.
 
## Decisiones de base (13/11/2026)
- Stack AACF web-app: React + TypeScript + Tailwind + shadcn / FastAPI + Postgres 16.
- Look & feel del mockup (sources/design), logo ALTEN. Paleta como tokens (desviación D1).
- Interfaz y contenido en EN/ES/FR. EN es el idioma maestro del contenido.
- Taxonomía: Catálogo V0 (32 familias, 83 servicios). El modelo admite ediciones futuras.
- Imágenes guardadas en Postgres.
- Todo se exporta a Excel y se reimporta con cambios (dos fases, idempotente por código estable).
- Listas de valores creables y editables desde la app.
- Las plantillas de sources/templates fijan formato y estilos; la forma de volcar los datos la decide el proyecto.
- Datos sintéticos en desarrollo; confidencialidad, SSO/MFA y datos reales los resuelve IT al desplegar.
- Sin IA hasta la fase final (servidor MCP).
 
## Encargos
| # | Encargo | Resultado verificable |
|---|---|---|
| E0 | Andamiaje: AACF, stack, tokens y shell, i18n EN/ES/FR, login y roles con SSO preparado, ajustes en la UI, auditoría, `check`, CI | La app arranca con login y el look del mockup; `check` en verde |
| E1 | Listas de valores editables + taxonomía (bloques, familias, servicios, soluciones, sectores, adyacentes) + infraestructura común de Excel ida y vuelta + importación inicial desde la hoja Lists | Listas y taxonomía creables, editables, exportables y reimportables |
| E2 | Referencias: modelo (campos traducibles, bloque y familia derivados del servicio, listas normalizadas de sedes, países, herramientas y estándares) + Excel ida y vuelta con el formato del CS_Reference_Template + informe de datos sucios | Las referencias de ejemplo importadas, exportadas, modificadas y reimportadas |
| E3 | Referencias en la UI: lista con filtros, ficha agrupada como el Excel, edición optimista, traducciones, galería de imágenes en Postgres, historial y papelera | Crear y editar una referencia sin Excel |
| E4 | Motor PPTX determinista + gestión de plantillas en la UI (subir y versionar) + Refs.pptx como formato de referencia + avisos de texto que no cabe + vista previa + tests contra ficheros de referencia, por idioma | La slide de cada referencia, igual que la plantilla, en EN/ES/FR |
| E5 | Salidas HTML y Markdown de referencias | Mismos datos en los formatos |
| E6 | Selecciones guardadas ("decks"): filtro + orden, regenerar con un clic; cobertura de referencias por servicio | Deck reproducible desde la base |
| E7 | Catálogo: contenido editorial por bloque (intro, key figures, added value, Digital & AI), editor + Excel ida y vuelta | Catálogo editable |
| E8 | Generación del catálogo con Template_for_Blocks.pptx (formato y estilos de la plantilla) | Slides de bloques desde Postgres |
| E9 | Informe HTML del catálogo (formato de catalogue_report_template.html) + Markdown | Informe desde Postgres |
| F1 | Traspaso a IT: SSO/MFA, despliegue, datos reales; endurecimiento (agente codebase-hardening) | Listo para el servidor de IT |
| F2 | Servidor MCP: Claude lee los datos y propone mejoras (textos que no caben, frases cortas, fusionar proyectos en una slide); una persona acepta cada cambio | Propuestas revisables desde Claude |
