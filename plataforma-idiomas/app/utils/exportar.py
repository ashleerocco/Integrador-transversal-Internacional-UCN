"""Utilidades para exportar las tablas visibles de la aplicación a Excel."""

from datetime import date, datetime
from io import BytesIO

import pandas as pd
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter


def dataframe_a_excel(df: pd.DataFrame, nombre_archivo: str, nombre_hoja: str) -> BytesIO:
    """Genera un libro .xlsx en memoria con formato básico para la tabla recibida."""
    salida = BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=nombre_hoja[:31])
        hoja = writer.sheets[nombre_hoja[:31]]
        hoja.freeze_panes = "A2"
        hoja.auto_filter.ref = hoja.dimensions
        for celda in hoja[1]:
            celda.font = Font(bold=True)

        for indice, columna in enumerate(df.columns, start=1):
            letra = get_column_letter(indice)
            maximo = max([len(str(columna))] + [
                len(str(valor)) for valor in df[columna].dropna().head(1000)
            ])
            hoja.column_dimensions[letra].width = min(max(maximo + 2, 10), 50)
            titulo = str(columna).lower()
            for fila in range(2, len(df) + 2):
                celda = hoja.cell(fila, indice)
                valor = celda.value
                if any(p in titulo for p in ("rut", "documento", "código", "codigo")):
                    celda.number_format = "@"
                    if valor is not None:
                        celda.value = str(valor)
                elif any(p in titulo for p in ("fecha", "inicio", "término", "termino", "solicitado", "entregado", "recibida")):
                    if isinstance(valor, (date, datetime)):
                        celda.number_format = "dd-mm-yyyy"
                    elif isinstance(valor, str) and len(valor) >= 10 and valor[4:5] == "-":
                        try:
                            celda.value = datetime.fromisoformat(valor[:10])
                            celda.number_format = "dd-mm-yyyy"
                        except ValueError:
                            pass
                elif "monto" in titulo or "clp" in titulo or "valor" in titulo:
                    celda.number_format = '$#,##0;[Red]-$#,##0'
                elif titulo == "id" or titulo.endswith("_id"):
                    celda.number_format = "@"
                    if valor is not None:
                        celda.value = str(valor)
    salida.name = nombre_archivo
    salida.seek(0)
    return salida


def boton_descarga(df: pd.DataFrame, nombre_base: str, nombre_hoja: str, *, key: str | None = None):
    """Muestra un botón para descargar el DataFrame y reporta errores de forma amigable."""
    import streamlit as st
    from datetime import date

    nombre = f"{nombre_base}_{date.today().isoformat()}.xlsx"
    try:
        archivo = dataframe_a_excel(df, nombre, nombre_hoja)
        _, boton = st.columns([5, 1])
        boton.download_button(
            "Descargar en Excel", data=archivo, file_name=nombre,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            disabled=df.empty, key=key,
        )
    except Exception:
        st.error("No se pudo preparar el archivo Excel. Inténtalo nuevamente.")
