"""Maquetacion comun de los manuales (python-docx).

Concentra el estilo para que el manual tecnico y el de usuario se vean igual:
portada, encabezado y pie con numeracion, titulos, parrafos con formato
en linea (**negrita**, `codigo`), vinetas, tablas con cabecera repetida,
bloques de codigo, notas destacadas y figuras con pie.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

RAIZ = Path(__file__).resolve().parents[1]

AZUL = RGBColor(0x1F, 0x38, 0x64)
AZUL_MEDIO = RGBColor(0x2E, 0x74, 0xB5)
GRIS = RGBColor(0x5A, 0x64, 0x72)
GRIS_CLARO = RGBColor(0x8A, 0x94, 0xA6)
NEGRO_SUAVE = RGBColor(0x22, 0x26, 0x2E)
BLANCO = RGBColor(0xFF, 0xFF, 0xFF)

HEX_AZUL = "1F3864"
HEX_AZUL_MEDIO = "2E74B5"
HEX_FONDO_TABLA = "F2F5FA"
HEX_FONDO_CODIGO = "F5F7FA"
HEX_BORDE = "C9D2DE"

TIPOGRAFIA = "Calibri"
TIPOGRAFIA_TITULO = "Calibri Light"
MONO = "Consolas"


# ---------------------------------------------------------------------------
# Utilidades XML
# ---------------------------------------------------------------------------
def _elemento(nombre: str, **atributos) -> OxmlElement:
    el = OxmlElement(nombre)
    for clave, valor in atributos.items():
        el.set(qn("w:%s" % clave), str(valor))
    return el


def _alineacion(valor):
    """Acepta WD_ALIGN_PARAGRAPH o un nombre en espanol."""
    if not isinstance(valor, str):
        return valor
    mapa = {"izquierda": WD_ALIGN_PARAGRAPH.LEFT,
            "centro": WD_ALIGN_PARAGRAPH.CENTER,
            "derecha": WD_ALIGN_PARAGRAPH.RIGHT,
            "justificado": WD_ALIGN_PARAGRAPH.JUSTIFY}
    return mapa.get(valor.lower(), WD_ALIGN_PARAGRAPH.LEFT)


def sombrear(elemento, color_hex: str) -> None:
    """Aplica fondo a una celda o a un parrafo."""
    pr = elemento.get_or_add_tcPr() if elemento.tag.endswith("}tc") else elemento.get_or_add_pPr()
    for viejo in pr.findall(qn("w:shd")):
        pr.remove(viejo)
    pr.append(_elemento("w:shd", val="clear", color="auto", fill=color_hex))


def bordes(elemento, color: str = HEX_BORDE, tamano: int = 4, lados=("top", "left", "bottom", "right")) -> None:
    """Dibuja bordes en una celda o parrafo."""
    es_celda = elemento.tag.endswith("}tc")
    pr = elemento.get_or_add_tcPr() if es_celda else elemento.get_or_add_pPr()
    nombre = "w:tcBorders" if es_celda else "w:pBdr"
    for viejo in pr.findall(qn(nombre)):
        pr.remove(viejo)
    contenedor = OxmlElement(nombre)
    for lado in lados:
        contenedor.append(_elemento("w:%s" % lado, val="single", sz=tamano,
                                    space="0", color=color))
    pr.append(contenedor)


def margenes_celda(celda, arriba=60, abajo=60, izquierda=90, derecha=90) -> None:
    pr = celda._tc.get_or_add_tcPr()
    for viejo in pr.findall(qn("w:tcMar")):
        pr.remove(viejo)
    contenedor = OxmlElement("w:tcMar")
    for lado, valor in (("top", arriba), ("bottom", abajo),
                        ("left", izquierda), ("right", derecha)):
        contenedor.append(_elemento("w:%s" % lado, w=valor, type="dxa"))
    pr.append(contenedor)


def repetir_cabecera(fila) -> None:
    tr_pr = fila._tr.get_or_add_trPr()
    tr_pr.append(_elemento("w:tblHeader", val="true"))


def no_partir_fila(fila) -> None:
    tr_pr = fila._tr.get_or_add_trPr()
    tr_pr.append(_elemento("w:cantSplit", val="true"))


def campo(parrafo, instruccion: str) -> None:
    """Inserta un campo de Word (PAGE, NUMPAGES, ...)."""
    run = parrafo.add_run()
    inicio = _elemento("w:fldChar", fldCharType="begin")
    run._r.append(inicio)
    run2 = parrafo.add_run()
    texto = OxmlElement("w:instrText")
    texto.set(qn("xml:space"), "preserve")
    texto.text = " %s " % instruccion
    run2._r.append(texto)
    run3 = parrafo.add_run()
    run3._r.append(_elemento("w:fldChar", fldCharType="separate"))
    marcador = parrafo.add_run("1")
    marcador.font.name = TIPOGRAFIA
    marcador.font.size = Pt(8)
    marcador.font.color.rgb = GRIS
    run4 = parrafo.add_run()
    run4._r.append(_elemento("w:fldChar", fldCharType="end"))


def fijar_fuente(estilo, nombre: str) -> None:
    """Asigna la misma tipografia a todos los alfabetos del estilo."""
    rpr = estilo.element.get_or_add_rPr()
    for viejo in rpr.findall(qn("w:rFonts")):
        rpr.remove(viejo)
    rpr.append(_elemento("w:rFonts", ascii=nombre, hAnsi=nombre,
                         eastAsia=nombre, cs=nombre))


# ---------------------------------------------------------------------------
# Formato en linea
# ---------------------------------------------------------------------------
_PATRON = re.compile(r"(\*\*.+?\*\*|`.+?`)")


def escribir_formato(parrafo, texto: str, tamano: float | None = None,
                     color: RGBColor | None = None) -> None:
    """Escribe texto interpretando **negrita** y `codigo`."""
    for trozo in _PATRON.split(texto):
        if not trozo:
            continue
        if trozo.startswith("**") and trozo.endswith("**"):
            run = parrafo.add_run(trozo[2:-2])
            run.bold = True
        elif trozo.startswith("`") and trozo.endswith("`"):
            run = parrafo.add_run(trozo[1:-1])
            run.font.name = MONO
            run.font.size = Pt((tamano or 10.5) - 1)
            run.font.color.rgb = RGBColor(0x1B, 0x4F, 0x72)
        else:
            run = parrafo.add_run(trozo)
        if tamano and not (trozo.startswith("`")):
            run.font.size = Pt(tamano)
        if color is not None:
            run.font.color.rgb = color


# ---------------------------------------------------------------------------
# Documento
# ---------------------------------------------------------------------------
class Manual:
    """Envoltorio de alto nivel sobre python-docx."""

    def __init__(self, titulo: str, subtitulo: str, version: str,
                 autor: str, materia: str, encabezado: str,
                 fecha: str | None = None):
        self.titulo = titulo
        self.subtitulo = subtitulo
        self.version = version
        self.autor = autor
        self.materia = materia
        self.encabezado = encabezado
        self.fecha = fecha or date.today().strftime("%d/%m/%Y")

        self.documento = Document()
        self._figuras = 0
        self._tablas = 0
        self._configurar_pagina()
        self._configurar_estilos()
        self._configurar_encabezado_pie()

    # -- configuracion base ------------------------------------------------
    def _configurar_pagina(self) -> None:
        seccion = self.documento.sections[0]
        seccion.orientation = WD_ORIENT.PORTRAIT
        seccion.page_width = Cm(21.0)
        seccion.page_height = Cm(29.7)
        seccion.top_margin = Cm(2.3)
        seccion.bottom_margin = Cm(2.2)
        seccion.left_margin = Cm(2.2)
        seccion.right_margin = Cm(2.2)
        seccion.header_distance = Cm(1.1)
        seccion.footer_distance = Cm(1.1)

    def _configurar_estilos(self) -> None:
        estilos = self.documento.styles

        normal = estilos["Normal"]
        normal.font.name = TIPOGRAFIA
        normal.font.size = Pt(10.5)
        normal.font.color.rgb = NEGRO_SUAVE
        normal.paragraph_format.space_after = Pt(6)
        normal.paragraph_format.space_before = Pt(0)
        normal.paragraph_format.line_spacing = 1.12
        fijar_fuente(normal, TIPOGRAFIA)

        especificaciones = {
            "Heading 1": (19, True, AZUL, 18, 8),
            "Heading 2": (13.5, True, AZUL_MEDIO, 14, 4),
            "Heading 3": (11.5, True, AZUL, 10, 3),
            "Heading 4": (10.5, True, GRIS, 8, 2),
        }
        for nombre, (tamano, negrita, color, antes, despues) in especificaciones.items():
            estilo = estilos[nombre]
            estilo.font.name = TIPOGRAFIA_TITULO if tamano > 13 else TIPOGRAFIA
            estilo.font.size = Pt(tamano)
            estilo.font.bold = negrita
            estilo.font.color.rgb = color
            estilo.font.italic = False
            estilo.paragraph_format.space_before = Pt(antes)
            estilo.paragraph_format.space_after = Pt(despues)
            estilo.paragraph_format.keep_with_next = True
            fijar_fuente(estilo, TIPOGRAFIA_TITULO if tamano > 13 else TIPOGRAFIA)

        for nombre in ("List Bullet", "List Number"):
            estilo = estilos[nombre]
            estilo.font.name = TIPOGRAFIA
            estilo.font.size = Pt(10.5)
            estilo.paragraph_format.space_after = Pt(3)
            estilo.paragraph_format.line_spacing = 1.1

        pie = estilos["Caption"]
        pie.font.name = TIPOGRAFIA
        pie.font.size = Pt(8.5)
        pie.font.italic = True
        pie.font.color.rgb = GRIS
        pie.font.bold = False

    def _configurar_encabezado_pie(self) -> None:
        seccion = self.documento.sections[0]
        seccion.different_first_page_header_footer = True

        encabezado = seccion.header
        parrafo = encabezado.paragraphs[0]
        parrafo.text = ""
        parrafo.alignment = WD_ALIGN_PARAGRAPH.LEFT
        izquierda = parrafo.add_run(self.encabezado)
        izquierda.font.size = Pt(8)
        izquierda.font.color.rgb = GRIS_CLARO
        izquierda.font.name = TIPOGRAFIA
        parrafo.add_run("\t\t")
        derecha = parrafo.add_run("%s  ·  v%s" % (self.materia, self.version))
        derecha.font.size = Pt(8)
        derecha.font.color.rgb = GRIS_CLARO
        derecha.font.name = TIPOGRAFIA
        bordes(parrafo._p, color=HEX_BORDE, tamano=4, lados=("bottom",))

        pie = seccion.footer
        parrafo = pie.paragraphs[0]
        parrafo.text = ""
        parrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = parrafo.add_run("Página ")
        run.font.size = Pt(8)
        run.font.color.rgb = GRIS
        campo(parrafo, "PAGE")
        run = parrafo.add_run(" de ")
        run.font.size = Pt(8)
        run.font.color.rgb = GRIS
        campo(parrafo, "NUMPAGES")
        for r in parrafo.runs:
            r.font.size = Pt(8)
            r.font.color.rgb = GRIS
            r.font.name = TIPOGRAFIA

    # -- portada ----------------------------------------------------------
    def portada(self, imagen: Path | None = None, ancho_imagen_cm: float = 15.0,
                resumen: str = "", metadatos=None) -> None:
        documento = self.documento

        banda = documento.add_table(rows=1, cols=1)
        banda.autofit = False
        celda = banda.rows[0].cells[0]
        celda.width = Cm(16.6)
        sombrear(celda._tc, HEX_AZUL)
        margenes_celda(celda, arriba=520, abajo=520, izquierda=280, derecha=280)
        parrafo = celda.paragraphs[0]
        parrafo.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = parrafo.add_run("CENTINELA IoT")
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(0x9D, 0xC3, 0xE6)
        run.font.bold = True
        run.font.name = TIPOGRAFIA

        parrafo = celda.add_paragraph()
        run = parrafo.add_run(self.titulo)
        run.font.size = Pt(28)
        run.font.bold = True
        run.font.color.rgb = BLANCO
        run.font.name = TIPOGRAFIA_TITULO
        parrafo.paragraph_format.space_after = Pt(6)

        parrafo = celda.add_paragraph()
        run = parrafo.add_run(self.subtitulo)
        run.font.size = Pt(12)
        run.font.color.rgb = RGBColor(0xD6, 0xE4, 0xF5)
        run.font.name = TIPOGRAFIA
        parrafo.paragraph_format.space_after = Pt(0)

        documento.add_paragraph()
        if imagen and Path(imagen).exists():
            figura = documento.add_paragraph()
            figura.alignment = WD_ALIGN_PARAGRAPH.CENTER
            figura.add_run().add_picture(str(imagen), width=Cm(ancho_imagen_cm))
            documento.add_paragraph()

        if resumen:
            parrafo = documento.add_paragraph()
            escribir_formato(parrafo, resumen, tamano=10.5, color=GRIS)
            parrafo.paragraph_format.space_after = Pt(14)

        metadatos = metadatos or [
            ("Asignatura", self.materia),
            ("Documento", self.titulo),
            ("Versión del sistema", "v%s" % self.version),
            ("Autor", self.autor),
            ("Fecha", self.fecha),
        ]
        tabla = documento.add_table(rows=0, cols=2)
        tabla.alignment = WD_TABLE_ALIGNMENT.LEFT
        tabla.autofit = False
        tabla.columns[0].width = Cm(4.6)
        tabla.columns[1].width = Cm(9.5)
        for etiqueta, valor in metadatos:
            fila = tabla.add_row()
            celda_a, celda_b = fila.cells
            celda_a.width = Cm(4.6)
            celda_b.width = Cm(9.5)
            for celda in (celda_a, celda_b):
                margenes_celda(celda, 70, 70, 110, 110)
                bordes(celda._tc, lados=(), color=HEX_BORDE)
            bordes(celda_a._tc, color=HEX_BORDE, tamano=4,
                   lados=("bottom",))
            bordes(celda_b._tc, color=HEX_BORDE, tamano=4,
                   lados=("bottom",))
            p = celda_a.paragraphs[0]
            r = p.add_run(etiqueta)
            r.font.size = Pt(9)
            r.font.bold = True
            r.font.color.rgb = GRIS
            p.paragraph_format.space_after = Pt(0)
            p = celda_b.paragraphs[0]
            r = p.add_run(valor)
            r.font.size = Pt(9.5)
            r.font.color.rgb = NEGRO_SUAVE
            p.paragraph_format.space_after = Pt(0)

        self.salto_pagina()

    # -- estructura --------------------------------------------------------
    def h1(self, texto: str, nueva_pagina: bool = True) -> None:
        parrafo = self.documento.add_paragraph(style="Heading 1")
        if nueva_pagina and self.documento.paragraphs:
            parrafo.paragraph_format.page_break_before = True
        escribir_formato(parrafo, texto)
        bordes(parrafo._p, color=HEX_AZUL_MEDIO, tamano=8, lados=("bottom",))
        parrafo.paragraph_format.space_after = Pt(10)

    def h2(self, texto: str) -> None:
        parrafo = self.documento.add_paragraph(style="Heading 2")
        escribir_formato(parrafo, texto)

    def h3(self, texto: str) -> None:
        parrafo = self.documento.add_paragraph(style="Heading 3")
        escribir_formato(parrafo, texto)

    def h4(self, texto: str) -> None:
        parrafo = self.documento.add_paragraph(style="Heading 4")
        escribir_formato(parrafo, texto)

    def parrafo(self, texto: str = "", alineacion=None, tamano=None,
                espacio_despues: float | None = None, cursiva: bool = False,
                color: RGBColor | None = None) -> None:
        parrafo = self.documento.add_paragraph()
        escribir_formato(parrafo, texto, tamano=tamano, color=color)
        parrafo.alignment = _alineacion(alineacion if alineacion is not None
                                        else "justificado")
        if espacio_despues is not None:
            parrafo.paragraph_format.space_after = Pt(espacio_despues)
        if cursiva:
            for run in parrafo.runs:
                run.italic = True

    def vinetas(self, elementos, nivel: int = 0) -> None:
        estilo = "List Bullet" if nivel == 0 else "List Bullet 2"
        for elemento in elementos:
            parrafo = self.documento.add_paragraph(style=estilo)
            escribir_formato(parrafo, elemento)

    def numerada(self, elementos) -> None:
        """Lista numerada con numeracion manual.

        Se evita el estilo "List Number" de Word porque continua la numeracion
        de la lista anterior del documento.
        """
        for indice, elemento in enumerate(elementos, start=1):
            parrafo = self.documento.add_paragraph()
            formato = parrafo.paragraph_format
            formato.left_indent = Cm(0.85)
            formato.first_line_indent = Cm(-0.85)
            formato.space_after = Pt(3)
            formato.tab_stops.add_tab_stop(Cm(0.85))
            run = parrafo.add_run("%d." % indice)
            run.bold = True
            run.font.size = Pt(10.5)
            run.font.color.rgb = AZUL_MEDIO
            parrafo.add_run("\t")
            escribir_formato(parrafo, elemento)

    def codigo(self, texto: str) -> None:
        parrafo = self.documento.add_paragraph()
        parrafo.paragraph_format.left_indent = Cm(0.35)
        parrafo.paragraph_format.right_indent = Cm(0.2)
        parrafo.paragraph_format.space_before = Pt(4)
        parrafo.paragraph_format.space_after = Pt(8)
        parrafo.paragraph_format.line_spacing = 1.0
        parrafo.paragraph_format.keep_together = True
        sombrear(parrafo._p, HEX_FONDO_CODIGO)
        bordes(parrafo._p, color="D8DEE7", tamano=4)
        lineas = texto.strip("\n").split("\n")
        for indice, linea in enumerate(lineas):
            run = parrafo.add_run(linea if linea else " ")
            run.font.name = MONO
            run.font.size = Pt(8.5)
            run.font.color.rgb = RGBColor(0x1F, 0x29, 0x33)
            if indice < len(lineas) - 1:
                run.add_break(WD_BREAK.LINE)

    def tabla(self, cabeceras, filas, anchos=None, fuente: float = 8.6,
              alinear_centro=(), primera_columna_negrita: bool = True,
              pie: str | None = None) -> None:
        columnas = len(cabeceras)
        tabla = self.documento.add_table(rows=1, cols=columnas)
        tabla.alignment = WD_TABLE_ALIGNMENT.CENTER
        tabla.autofit = False
        tabla.style = "Table Grid"

        if anchos is None:
            anchos = [16.6 / columnas] * columnas
        else:
            total = sum(anchos)
            anchos = [a * 16.6 / total for a in anchos]

        cabecera = tabla.rows[0]
        repetir_cabecera(cabecera)
        no_partir_fila(cabecera)
        for indice, ancho in enumerate(anchos):
            tabla.columns[indice].width = Cm(ancho)
        for indice, texto in enumerate(cabeceras):
            celda = cabecera.cells[indice]
            celda.width = Cm(anchos[indice])
            sombrear(celda._tc, HEX_AZUL)
            margenes_celda(celda)
            parrafo = celda.paragraphs[0]
            parrafo.paragraph_format.space_after = Pt(0)
            parrafo.paragraph_format.space_before = Pt(0)
            if indice in alinear_centro:
                parrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = parrafo.add_run(str(texto))
            run.bold = True
            run.font.size = Pt(fuente)
            run.font.color.rgb = BLANCO
            run.font.name = TIPOGRAFIA

        for numero, fila in enumerate(filas):
            celdas = tabla.add_row().cells
            no_partir_fila(tabla.rows[-1])
            for indice, valor in enumerate(fila):
                celda = celdas[indice]
                celda.width = Cm(anchos[indice])
                margenes_celda(celda)
                if numero % 2 == 1:
                    sombrear(celda._tc, HEX_FONDO_TABLA)
                parrafo = celda.paragraphs[0]
                parrafo.paragraph_format.space_after = Pt(0)
                parrafo.paragraph_format.space_before = Pt(0)
                parrafo.paragraph_format.line_spacing = 1.0
                if indice in alinear_centro:
                    parrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
                escribir_formato(parrafo, str(valor), tamano=fuente)
                if primera_columna_negrita and indice == 0:
                    for run in parrafo.runs:
                        run.bold = True

        self._tablas += 1
        if pie:
            self.pie_tabla(pie)
        else:
            self.documento.add_paragraph().paragraph_format.space_after = Pt(2)

    def pie_tabla(self, texto: str) -> None:
        parrafo = self.documento.add_paragraph(style="Caption")
        parrafo.alignment = WD_ALIGN_PARAGRAPH.LEFT
        parrafo.paragraph_format.space_before = Pt(3)
        parrafo.paragraph_format.space_after = Pt(10)
        run = parrafo.add_run("Tabla %d. %s" % (self._tablas, texto))
        run.font.size = Pt(8.5)
        run.italic = True
        run.font.color.rgb = GRIS

    def figura(self, ruta: Path, pie: str, ancho_cm: float = 15.5) -> None:
        ruta = Path(ruta)
        if not ruta.exists():
            self.parrafo("**[Figura no disponible: %s]**" % ruta.name)
            return
        parrafo = self.documento.add_paragraph()
        parrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        parrafo.paragraph_format.space_before = Pt(6)
        parrafo.paragraph_format.space_after = Pt(2)
        parrafo.paragraph_format.keep_with_next = True
        parrafo.add_run().add_picture(str(ruta), width=Cm(ancho_cm))

        self._figuras += 1
        parrafo = self.documento.add_paragraph(style="Caption")
        parrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        parrafo.paragraph_format.space_after = Pt(12)
        run = parrafo.add_run("Figura %d. %s" % (self._figuras, pie))
        run.font.size = Pt(8.5)
        run.italic = True
        run.font.color.rgb = GRIS

    def nota(self, texto: str, tipo: str = "nota", titulo: str | None = None) -> None:
        """Recuadro destacado: nota (azul), aviso (ambar), peligro (rojo)."""
        colores = {
            "nota": (HEX_AZUL_MEDIO, "EAF1FA", "Nota"),
            "aviso": ("B45309", "FDF3E3", "Aviso"),
            "peligro": ("B91C1C", "FBEAEA", "Importante"),
            "truco": ("15803D", "E9F6EE", "Recomendación"),
        }
        borde, fondo, etiqueta = colores.get(tipo, colores["nota"])
        tabla = self.documento.add_table(rows=1, cols=1)
        tabla.autofit = False
        celda = tabla.rows[0].cells[0]
        celda.width = Cm(16.6)
        sombrear(celda._tc, fondo)
        margenes_celda(celda, 100, 100, 150, 150)
        bordes(celda._tc, color=borde, tamano=18, lados=("left",))
        parrafo = celda.paragraphs[0]
        parrafo.paragraph_format.space_after = Pt(0)
        run = parrafo.add_run("%s: " % (titulo or etiqueta))
        run.bold = True
        run.font.size = Pt(9.2)
        run.font.color.rgb = RGBColor.from_string(borde)
        escribir_formato(parrafo, texto, tamano=9.2)
        self.documento.add_paragraph().paragraph_format.space_after = Pt(4)

    def salto_pagina(self) -> None:
        self.documento.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def referencia(self, texto: str) -> None:
        """Entrada de bibliografia con sangria francesa (APA)."""
        parrafo = self.documento.add_paragraph()
        formato = parrafo.paragraph_format
        formato.left_indent = Cm(1.0)
        formato.first_line_indent = Cm(-1.0)
        formato.space_after = Pt(7)
        formato.line_spacing = 1.15
        escribir_formato(parrafo, texto, tamano=9.8)

    def bloque_datos(self, filas, anchos=(4.6, 11.8)) -> None:
        """Tabla de dos columnas sin cabecera, para fichas y resumentes."""
        tabla = self.documento.add_table(rows=0, cols=2)
        tabla.autofit = False
        tabla.columns[0].width = Cm(anchos[0])
        tabla.columns[1].width = Cm(anchos[1])
        for etiqueta, valor in filas:
            celdas = tabla.add_row().cells
            for indice, celda in enumerate(celdas):
                celda.width = Cm(anchos[indice])
                margenes_celda(celda, 70, 70, 110, 110)
                bordes(celda._tc, color=HEX_BORDE, tamano=4, lados=("bottom",))
            p = celdas[0].paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(etiqueta)
            r.bold = True
            r.font.size = Pt(9)
            r.font.color.rgb = GRIS
            p = celdas[1].paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            escribir_formato(p, valor, tamano=9.5)
        self.documento.add_paragraph().paragraph_format.space_after = Pt(2)

    def guardar(self, ruta: Path) -> Path:
        ruta = Path(ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        self.documento.save(str(ruta))
        return ruta
