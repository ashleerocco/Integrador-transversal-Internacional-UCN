"""Descargas Excel (.xlsx): cabeceras en español, fechas legibles y enlaces de Drive clicables."""
from __future__ import annotations

import io
from datetime import date, datetime

import pandas as pd
import streamlit as st
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

# Nombres técnicos -> cabeceras en español (lo que no esté aquí se "humaniza")
ETIQUETAS = {
    "rut": "RUT", "rut_estudiante": "RUT", "rut_docente": "RUT docente", "tipo_documento": "Tipo de documento",
    "nombre_completo": "Nombre completo", "nombres": "Nombres", "apellido_paterno": "Apellido paterno",
    "apellido_materno": "Apellido materno", "nombre_social": "Nombre social", "correo": "Correo",
    "telefono": "Teléfono", "vinculo_nombre": "Vínculo UCN", "vinculo_detalle_nombre": "Detalle vínculo",
    "campus_nombre": "Campus", "genero": "Género", "sexo": "Sexo", "fecha_nacimiento": "Fecha de nacimiento",
    "edad": "Edad", "nacionalidad": "Nacionalidad", "carrera": "Carrera / Unidad / Profesión",
    "curso": "Curso", "cursos": "Cursos", "oferta_id": "ID oferta", "idioma_nombre": "Idioma", "idioma": "Idioma",
    "monto": "Monto", "monto_total": "Monto total", "monto_pagado": "Monto pagado", "saldo": "Saldo",
    "estado_pago": "Estado de pago", "fecha_primer_pago": "Fecha primer pago", "fecha": "Fecha",
    "banco": "Banco", "n_transaccion": "N° transacción", "n_boleta": "N° boleta/código", "n_cuota": "N° cuota",
    "forma_pago_nombre": "Forma de pago", "codigo_proyecto": "Código proyecto", "mes": "Mes",
    "comprobante_drive_url": "Comprobante", "drive_url": "Archivo", "cedula_url": "Cédula",
    "licencia_url": "Licencia E. Media", "cedula_drive_url": "Cédula", "licencia_drive_url": "Licencia E. Media",
    "estado": "Estado", "creado_en": "Creado", "fecha_solicitada": "Fecha solicitada",
    "fecha_firma": "Fecha de firma", "fecha_entrega": "Fecha de entrega", "nota1": "Nota 1", "nota2": "Nota 2",
    "nota3": "Nota 3", "nota_final": "Nota final", "porcentaje": "% asistencia", "codigo": "Código",
    "cupo_minimo": "Mínimo", "cupo_maximo": "Máximo", "inscritos": "Inscritos", "faltan": "Faltan",
    "solicitudes_pendientes": "Solicitudes pendientes", "pagados": "Pagados", "periodo": "Período",
    "salud_tiene_condicion": "Condición de salud", "salud_requerimiento": "Requerimiento de salud",
}


def etiqueta(col: str) -> str:
    return ETIQUETAS.get(col, col.replace("_", " ").capitalize())


def _valor(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (list, tuple, dict)):
        return ", ".join(map(str, v)) if not isinstance(v, dict) else str(v)
    if isinstance(v, str) and len(v) >= 10 and v[4:5] == "-" and v[7:8] == "-":
        try:
            if len(v) == 10:
                return date.fromisoformat(v)
            return datetime.fromisoformat(v.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return v
    return v


def a_excel(hojas: dict[str, pd.DataFrame]) -> bytes:
    wb = Workbook()
    wb.remove(wb.active)
    for nombre, df in hojas.items():
        ws = wb.create_sheet(title=nombre[:31])
        df = df if df is not None else pd.DataFrame()
        cols = list(df.columns)
        ws.append([etiqueta(c) for c in cols])
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="421668")
        for fila in df.itertuples(index=False):
            ws.append([_valor(v) for v in fila])
        for j, col in enumerate(cols, start=1):
            letra = get_column_letter(j)
            ancho = max([len(etiqueta(col))] + [len(str(ws.cell(row=i, column=j).value or ""))
                                                 for i in range(2, min(ws.max_row, 200) + 1)])
            ws.column_dimensions[letra].width = min(max(ancho + 2, 10), 60)
            for i in range(2, ws.max_row + 1):
                celda = ws.cell(row=i, column=j)
                if isinstance(celda.value, datetime):
                    celda.number_format = "DD-MM-YYYY HH:MM"
                elif isinstance(celda.value, date):
                    celda.number_format = "DD-MM-YYYY"
                elif isinstance(celda.value, str) and celda.value.startswith("https://"):
                    celda.hyperlink = celda.value
                    celda.value = "Abrir"
                    celda.font = Font(color="6D5CE8", underline="single")
        ws.freeze_panes = "A2"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def boton_excel(df: pd.DataFrame, nombre: str, key: str, hoja: str | None = None):
    """Descarga de la tabla tal como se ve (respetando los filtros activos)."""
    st.download_button(
        "Descargar Excel", data=a_excel({hoja or nombre: df}),
        file_name=f"{nombre}_{date.today():%Y%m%d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=key,
    )


def renombrar(df: pd.DataFrame) -> pd.DataFrame:
    """Para mostrar en pantalla con las mismas cabeceras del Excel."""
    return df.rename(columns={c: etiqueta(c) for c in df.columns})
