from fpdf import FPDF
from datetime import datetime, date
import os

def fmt_d(n):
    if n is None:
        return '0.00'
    s = f'{float(n):,.2f}'
    return s.replace(',', ' ')

def font_paths():
    """Return (regular_ttf, bold_ttf) or (None, None)."""
    dirname = os.path.dirname(__file__)
    reg = os.path.join(dirname, 'static', 'fonts', 'DejaVuSans.ttf')
    bold = os.path.join(dirname, 'static', 'fonts', 'DejaVuSans-Bold.ttf')
    if os.path.exists(reg) and os.path.exists(bold):
        return (reg, bold)
    # Windows Arial
    arial = 'C:/Windows/Fonts/ARIAL.TTF'
    arialbd = 'C:/Windows/Fonts/ARIALBD.TTF'
    if os.path.exists(arial) and os.path.exists(arialbd):
        return (arial, arialbd)
    if os.path.exists(arial):
        return (arial, arial)  # fallback: regular as bold
    # DejaVuSans from system
    djr = 'C:/Windows/Fonts/DejaVuSans.ttf'
    djb = 'C:/Windows/Fonts/DejaVuSans-Bold.ttf'
    if os.path.exists(djr):
        return (djr, djb if os.path.exists(djb) else djr)
    return (None, None)

class PDFReport(FPDF):
    def __init__(self, title='SCAFMH', unidad=None, ufv=None, hoy=None):
        super().__init__('L', 'mm', 'A4')
        self.set_auto_page_break(auto=True, margin=15)
        self.report_title = title
        self.unidad = unidad or {}
        self.ufv_val = ufv
        self.hoy_val = hoy or date.today()
        self._register_fonts()

    def _register_fonts(self):
        """Register Unicode fonts with bold variant."""
        reg, bld = font_paths()
        if reg:
            self.add_font('Custom', '', reg, uni=True)
            self.add_font('Custom', 'B', bld or reg, uni=True)
            self.font_name = 'Custom'
        else:
            self.font_name = 'Helvetica'

    def header(self):
        self.set_font(self.font_name, '', 8)
        self.cell(0, 4, 'ENTIDAD: 670 - Organo Electoral Plurinacional', 0, 0, 'L')
        if self.ufv_val:
            self.cell(0, 4, f'UFV: {self.ufv_val:.5f} Bs.', 0, 1, 'R')
        else:
            self.ln(4)
        self.set_font(self.font_name, '', 7)
        self.cell(0, 4, f'UNIDAD: {self.unidad.get("codigo","")} - {self.unidad.get("descripcion","")}', 0, 0, 'L')
        self.cell(0, 4, f'AL: {self.hoy_val.strftime("%d DE %B DE %Y").upper()}', 0, 1, 'R')
        self.set_font(self.font_name, 'B', 10)
        self.cell(0, 8, self.report_title, 0, 1, 'C')
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.font_name, '', 7)
        self.cell(0, 10, f'Pagina {self.page_no()}/{{nb}}', 0, 0, 'R')

    def write_table(self, headers, rows, col_widths, font_size=7):
        self.set_font(self.font_name, 'B', font_size)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, h, 1, 0, 'C')
        self.ln()
        self.set_font(self.font_name, '', font_size)
        for row in rows:
            for i, val in enumerate(row):
                align = 'R' if isinstance(val, (int, float)) else 'L'
                display = fmt_d(val) if isinstance(val, float) else str(val)
                self.cell(col_widths[i], 5, display, 1, 0, align)
            self.ln()

    def write_resumen_table(self, data, total, font_size=7):
        self.set_font(self.font_name, 'B', font_size)
        headers = ['GRUPO', 'CANT', 'COSTO HISTORICO', 'COSTO ACTUAL', 'DEP. ACUM.',
                   'DEP. GESTION', 'VALOR NETO', '%PART']
        cw = [35, 10, 28, 30, 28, 28, 30, 12]
        for i, h in enumerate(headers):
            self.cell(cw[i], 7, h, 1, 0, 'C')
        self.ln()
        self.set_font(self.font_name, '', font_size)
        # data is an OrderedDict: group_name -> {grupo, cantidad, costo_historico, ...}
        total_valor = total.get('valor_neto', 1) or 1
        for gdict in data.values():
            pct = (gdict['valor_neto'] / total_valor * 100) if total_valor else 0
            vals = [gdict['grupo'][:35], str(gdict['cantidad']),
                    gdict['costo_historico'], gdict['costo_actual_inicial'],
                    gdict['dep_acum_inicial'], gdict['dep_gestion'],
                    gdict['valor_neto'], round(pct, 1)]
            for i, v in enumerate(vals):
                a = 'R' if i > 0 else 'L'
                d = v if isinstance(v, str) else fmt_d(v)
                self.cell(cw[i], 5, str(d), 1, 0, a)
            self.ln()
        # Total row
        self.set_font(self.font_name, 'B', font_size)
        tvals = ['TOTALES', str(total['cantidad']),
                 total['costo_historico'], total['costo_actual_inicial'],
                 total['dep_acum_inicial'], total['dep_gestion'],
                 total['valor_neto'], '100.0']
        for i, v in enumerate(tvals):
            a = 'R' if i > 0 else 'L'
            d = v if isinstance(v, str) else fmt_d(v)
            self.cell(cw[i], 6, str(d), 1, 0, a)
        self.ln()


def generar_pdf_inv_codigo(rows, unidad, ufv, hoy):
    pdf = PDFReport('Inventario Ordenado por Codigo de Activo', unidad, ufv, hoy)
    pdf.alias_nb_pages()
    pdf.add_page()
    headers = ['CODIGO', 'DESCRIPCION', 'COSTO', 'FECHA', 'COSTO ACTUAL',
               'DEP. ACUM.', 'DEP. GEST.', 'DEP. TOTAL', 'VALOR NETO', 'GRUPO']
    cw = [18, 50, 22, 16, 22, 22, 18, 22, 22, 30]
    table = []
    for r in rows:
        fec = r['fecha_incorporacion'].strftime('%d/%m/%Y') if r.get('fecha_incorporacion') else ''
        table.append([r['codigo'][:18], r['descripcion'][:50],
                      r['costo'], fec, r['costo_actual_inicial'],
                      r['dep_acum_inicial'], r['dep_gestion'],
                      r['dep_acum_total'], r['valor_neto'],
                      r['grupo_nombre'][:30]])
    pdf.write_table(headers, table, cw, 7)
    return pdf


def generar_pdf_inv_grupo_detalle(rows, unidad, ufv, hoy):
    pdf = PDFReport('Inventario de Activos Fijos por Grupo Contable', unidad, ufv, hoy)
    pdf.alias_nb_pages()
    pdf.add_page()
    headers = ['CODIGO', 'DESCRIPCION', 'COSTO', 'FECHA', '%DEPR',
               'DIAS', 'COSTO ACTUAL', 'DEP. ACUM. INI', 'ACT. DEP.',
               'DEP. ACUM. AJUST', 'DEP. GESTION', 'DEP. TOTAL', 'VALOR NETO']
    cw = [16, 38, 18, 14, 10, 8, 20, 20, 16, 20, 18, 18, 20]
    table = []
    for r in rows:
        fec = r['fecha_incorporacion'].strftime('%d/%m/%Y') if r.get('fecha_incorporacion') else ''
        table.append([r['codigo'][:16], r['descripcion'][:38],
                      r['costo'], fec, r.get('porcentaje_depr', ''),
                      r.get('dias', ''), r['costo_actual_inicial'],
                      r['dep_acum_inicial'], r.get('actualizacion_dep', 0),
                      r.get('dep_acum_ajustado', 0), r['dep_gestion'],
                      r['dep_acum_total'], r['valor_neto']])
    pdf.write_table(headers, table, cw, 6.5)
    return pdf


def generar_pdf_resumen_grupo(resumen, total, unidad, ufv, hoy):
    pdf = PDFReport('Resumen de Activos Fijos por Grupo', unidad, ufv, hoy)
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.write_resumen_table(resumen, total, 7)
    return pdf


def generar_pdf_ufv(data, unidad, hoy):
    pdf = PDFReport('Reporte de Indices UFV', unidad, None, hoy)
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font(pdf.font_name, 'B', 8)
    headers = ['DIA', 'MES', 'ANO', 'INDICE UFV']
    cw = [20, 20, 20, 40]
    pdf.write_table(headers, [(d.fecha.strftime('%d'), d.fecha.strftime('%m'),
                                d.fecha.strftime('%Y'), float(d.valor)) for d in data],
                    cw, 8)
    return pdf


def generar_pdf_activos_simple(rows, unidad, ufv, hoy, title, headers, col_widths, font_size=7):
    pdf = PDFReport(title, unidad, ufv, hoy)
    pdf.alias_nb_pages()
    pdf.add_page()
    fec = lambda r: r['fecha_incorporacion'].strftime('%d/%m/%Y') if r.get('fecha_incorporacion') else ''
    table = []
    for r in rows:
        table.append([r['codigo'][:18], r['descripcion'][:48],
                      r['costo'], fec(r), r['costo_actual_inicial'],
                      r['dep_acum_inicial'], r['dep_gestion'],
                      r['dep_acum_total'], r['valor_neto'],
                      r['grupo_nombre'][:25]])
    pdf.write_table(headers, table, col_widths, font_size)
    return pdf


MESES_ES = ['', 'ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO',
            'JULIO', 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE']

def fecha_espanol(d):
    return f'{d.day} DE {MESES_ES[d.month]} DE {d.year}'

class ActaAsignacion(FPDF):
    """Acta de Asignacion Individual de Bienes."""
    def __init__(self, responsable, oficina, activos, hoy=None):
        super().__init__('P', 'mm', 'A4')
        self.set_auto_page_break(auto=True, margin=25)
        self.responsable = responsable
        self.oficina = oficina
        self.activos = activos
        self.hoy = hoy or date.today()
        self._register_fonts()
        self.alias_nb_pages()

    def _register_fonts(self):
        reg, bld = font_paths()
        if reg:
            self.add_font('C', '', reg, uni=True)
            self.add_font('C', 'B', bld or reg, uni=True)
            self.font_name = 'C'
        else:
            self.font_name = 'Helvetica'

    def header_blocks(self):
        """Draw the top section: title, date, entidad, responsable, etc."""
        # Top line: title + page
        self.set_font(self.font_name, 'B', 14)
        self.cell(0, 7, 'ASIGNACION INDIVIDUAL DE BIENES', 0, 0, 'C')
        self.set_font(self.font_name, '', 8)
        self.cell(0, 7, f'Pagina: {self.page_no()}', 0, 1, 'R')
        # Date line
        self.set_font(self.font_name, 'B', 11)
        self.cell(0, 6, fecha_espanol(self.hoy), 0, 0, 'C')
        self.set_font(self.font_name, '', 7)
        self.cell(0, 6, f'Fecha de Impresion: {self.hoy.strftime("%d/%m/%Y")}', 0, 1, 'R')
        self.ln(2)
        # ENTIDAD
        self.set_font(self.font_name, 'B', 9)
        self.cell(40, 5, 'ENTIDAD:', 0, 0)
        self.set_font(self.font_name, '', 9)
        self.cell(0, 5, '670    Organo Electoral Plurinacional', 0, 1)
        # UNIDAD
        uni = self.responsable.get('unidad_codigo', '') if isinstance(self.responsable, dict) else ''
        uni_desc = self.responsable.get('unidad_desc', '') if isinstance(self.responsable, dict) else ''
        self.set_font(self.font_name, 'B', 9)
        self.cell(40, 5, 'UNIDAD:', 0, 0)
        self.set_font(self.font_name, '', 9)
        self.cell(0, 5, f'{uni}    {uni_desc}', 0, 1)
        # RESPONSABLE + CARGO on same line
        resp_name = self.responsable.get('nombre', '') if isinstance(self.responsable, dict) else ''
        cargo = self.responsable.get('cargo', '') if isinstance(self.responsable, dict) else ''
        self.set_font(self.font_name, 'B', 9)
        self.cell(25, 5, 'RESPONSABLE:', 0, 0)
        self.set_font(self.font_name, '', 9)
        self.cell(80, 5, resp_name, 0, 0)
        self.set_font(self.font_name, 'B', 9)
        self.cell(15, 5, 'CARGO:', 0, 0)
        self.set_font(self.font_name, '', 9)
        self.cell(0, 5, cargo, 0, 1)
        # OFICINA + CI on same line
        ofi_nombre = self.oficina.get('nombre', '') if isinstance(self.oficina, dict) else ''
        ofi_cod = self.oficina.get('codofic', '') if isinstance(self.oficina, dict) else ''
        ci = self.responsable.get('carnet_identidad', '') if isinstance(self.responsable, dict) else ''
        self.set_font(self.font_name, 'B', 9)
        self.cell(18, 5, 'OFICINA:', 0, 0)
        self.set_font(self.font_name, '', 9)
        self.cell(87, 5, f'{ofi_cod} - {ofi_nombre}', 0, 0)
        self.set_font(self.font_name, 'B', 9)
        self.cell(10, 5, 'C.I.:', 0, 0)
        self.set_font(self.font_name, '', 9)
        self.cell(0, 5, ci, 0, 1)
        self.ln(3)

    def generar(self):
        """Generate the full acta PDF."""
        self.add_page()
        self.header_blocks()

        # Table header
        col_w = [28, 35, 95, 25]
        self.set_font(self.font_name, 'B', 8)
        self.cell(col_w[0], 6, 'CODIGO', 1, 0, 'C')
        self.cell(col_w[1], 6, 'AUXILIAR', 1, 0, 'C')
        self.cell(col_w[2], 6, 'DESCRIPCION DE ACTIVO', 1, 0, 'C')
        self.cell(col_w[3], 6, 'ESTADO', 1, 1, 'C')

        # Table rows
        self.set_font(self.font_name, '', 7)
        row_h = 5
        for a in self.activos:
            codigo = a.get('codigo', '')[:15]
            aux = a.get('auxiliar', '')[:25]
            desc = a.get('descripcion', '')[:80]
            estado = a.get('estado_bien', '')[:10]
            y_start = self.get_y()
            # Calculate needed height
            lines = max(1, len(desc) // 50 + 1)
            h = max(row_h, lines * 4)

            if self.get_y() + h > 270:
                self.add_page()
                self.header_blocks()
                self.set_font(self.font_name, 'B', 8)
                self.cell(col_w[0], 6, 'CODIGO', 1, 0, 'C')
                self.cell(col_w[1], 6, 'AUXILIAR', 1, 0, 'C')
                self.cell(col_w[2], 6, 'DESCRIPCION DE ACTIVO', 1, 0, 'C')
                self.cell(col_w[3], 6, 'ESTADO', 1, 1, 'C')
                self.set_font(self.font_name, '', 7)

            self.cell(col_w[0], h, codigo, 1, 0, 'L')
            self.cell(col_w[1], h, aux, 1, 0, 'L')
            x_desc = self.get_x()
            y_desc = self.get_y()
            self.cell(col_w[2], h, '', 1, 0, 'L')
            # Multi-cell for description
            self.set_xy(x_desc, y_desc)
            self.multi_cell(col_w[2], 4, desc, 0, 'L')
            # Move to estado cell
            self.set_xy(x_desc + col_w[2], y_desc)
            self.cell(col_w[3], h, estado, 1, 1, 'C')

        self.ln(4)

        # Total count
        self.set_font(self.font_name, 'B', 10)
        self.cell(0, 7, f'Cantidad {len(self.activos)}', 0, 1, 'R')
        self.ln(3)

        # Legal text
        self.set_font(self.font_name, '', 8)
        legal1 = ('El servidor publico queda prohibido de usar o permitir el uso de los bienes para beneficio '
                   'particular o privado, prestar o transferir el bien a otro empleado publico, enajenar el bien '
                   'por cuenta propia, danar o alterar sus caracteristicas fisicas o tecnicas, poner en riesgo el '
                   'bien, ingresar o sacar bienes particulares sin autorizacion de la Unidad o Responsable de '
                   'Activos Fijos.')
        legal2 = ('La no observancia a estas prohibiciones generara responsabilidades establecidas en la Ley '
                   'N 1178 y sus reglamentos.')
        legal3 = 'En senal de conformidad y aceptacion se firma el presente acta.'

        self.multi_cell(0, 4.5, legal1, 0, 'J')
        self.ln(1)
        self.multi_cell(0, 4.5, legal2, 0, 'J')
        self.ln(1)
        self.multi_cell(0, 4.5, legal3, 0, 'J')
        self.ln(10)

        # Signature lines
        self.set_font(self.font_name, '', 9)
        sw = 63
        for label in ['Autorizacion de Asignacion', 'Responsable de Activos Fijos', 'Funcionario']:
            self.cell(sw, 6, '__________________________________', 0, 0, 'C')
        self.ln()
        for label in ['Autorizacion de Asignacion', 'Responsable de Activos Fijos', 'Funcionario']:
            self.cell(sw, 6, label, 0, 0, 'C')
        self.ln(10)

        # footer
        self.set_font(self.font_name, '', 7)
        self.cell(0, 5, 'SCAFMH 1.0', 0, 1, 'C')

        return self


def generar_pdf_acta_transferencia(responsable, oficina, activos, hoy=None):
    """Generate acta PDF in 'Asignacion Individual de Bienes' format.
    
    Args:
        responsable: dict with nombre, cargo, carnet_identidad, unidad_codigo, unidad_desc
        oficina: dict with codofic, nombre
        activos: list of dicts with codigo, auxiliar, descripcion, estado_bien
        hoy: date
    Returns:
        ActaAsignacion instance (call output() to get bytes)
    """
    pdf = ActaAsignacion(responsable, oficina, activos, hoy)
    pdf.generar()
    return pdf


def generar_pdf_asignacion(rows, unidad, hoy):
    pdf = PDFReport('Asignacion Individual de Bienes', unidad, None, hoy)
    pdf.alias_nb_pages()
    pdf.add_page()
    headers = ['N', 'CODIGO', 'DESCRIPCION', 'FECHA', 'COSTO',
               'COSTO ACT.', 'DEPRECIACION', 'VALOR NETO', 'FIRMA']
    cw = [6, 16, 40, 14, 18, 18, 18, 18, 20]
    table = []
    for i, r in enumerate(rows, 1):
        fec = r['fecha_incorporacion'].strftime('%d/%m/%Y') if r.get('fecha_incorporacion') else ''
        table.append([str(i), r['codigo'][:16], r['descripcion'][:40],
                      fec, r['costo'], r['costo_actual_inicial'],
                      r['dep_acum_total'], r['valor_neto'], '____________'])
    pdf.write_table(headers, table, cw, 7)
    pdf.ln(20)
    pdf.set_font(pdf.font_name, '', 9)
    for label in ['ENTREGADO POR', 'RECIBIDO POR', 'V°B°']:
        pdf.cell(63, 6, f'_________________________    {label}', 0, 0, 'C')
    return pdf
