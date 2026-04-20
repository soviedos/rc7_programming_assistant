# Ingestion de Manuales

## Objetivo

Transformar manuales PDF DENSO en una base de conocimiento confiable y recuperable.

## Supuestos del proyecto

- Los manuales tienen buena calidad digital.
- El texto es extraible sin depender principalmente de OCR.
- Cada tema puede aplicar a diferentes tipos de robot o versiones del controlador.

## Pipeline recomendado

1. Subida del PDF a object storage.
2. Registro del manual en base de datos.
3. Parsing de texto y deteccion de estructura.
4. Segmentacion por:
   - capitulo
   - seccion
   - comando
   - ejemplo PAC
   - tabla
5. Deteccion de aplicabilidad:
   - 4-axis
   - 6-axis
   - vision
   - all robots
   - version minima
6. Generacion de embeddings.
7. Indexacion en PostgreSQL + pgvector.

## Justificacion

No basta con recuperar texto similar; el sistema debe filtrar contexto correcto para el robot configurado por el usuario.

## Resultado esperado

Cada chunk debe incluir:

- texto
- pagina
- seccion
- comandos detectados
- aplicabilidad tecnica
- referencia al archivo original
