from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader


def extract_pdf_text_by_page(content: bytes) -> list[str]:
    reader = PdfReader(BytesIO(content))
    return [(page.extract_text() or "").strip() for page in reader.pages]


def extract_page_sections(content: bytes) -> dict[int, str]:
    """Mapea cada página (1-based) al título de la sección que la contiene.

    Se apoya en el outline del PDF, que en los manuales DENSO es la estructura
    real escrita por el fabricante (capítulo → sección → subsección), no una
    inferencia. Para una página se toma el título más profundo cuya sección
    empieza en esa página o antes, que es la sección en curso al leer en orden.

    Devuelve {} si el PDF no trae outline o no se puede resolver: es un dato
    opcional y su ausencia no debe romper la ingesta.
    """
    try:
        reader = PdfReader(BytesIO(content))
        outline = reader.outline
    except Exception:
        return {}

    marcas: list[tuple[int, str]] = []

    def recorrer(items) -> None:
        for item in items:
            if isinstance(item, list):
                recorrer(item)
                continue
            try:
                titulo = str(item.title).strip()
                if not titulo:
                    continue
                pagina = reader.get_destination_page_number(item) + 1
                marcas.append((pagina, titulo))
            except Exception:
                # Un marcador roto no invalida el resto del outline.
                continue

    try:
        recorrer(outline)
    except Exception:
        return {}

    if not marcas:
        return {}

    total = len(reader.pages)
    por_pagina: dict[int, str] = {}
    actual: str | None = None
    indice = 0
    for pagina in range(1, total + 1):
        while indice < len(marcas) and marcas[indice][0] <= pagina:
            actual = marcas[indice][1]
            indice += 1
        if actual:
            por_pagina[pagina] = actual

    return por_pagina
