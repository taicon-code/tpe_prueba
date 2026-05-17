"""Marca de agua diagonal y footer de auditoria para PDFs generados.

Tres estados:
  - 'BORRADOR': resolucion/auto sin Notificacion. Marca roja en grande,
    para alertar que NO es documento oficial.
  - 'FIRMADO': resolucion/auto con Notificacion registrada.
    Marca verde "FIRMADO".
  - 'REPORTE': reportes agregados (historial, lotes, custodia). Marca
    gris pequena indicando que es reporte informativo y no reemplaza al
    documento oficial firmado.

Se aplica via callbacks `onFirstPage`/`onLaterPages` de SimpleDocTemplate.
"""
from reportlab.lib import colors


def _marca_diagonal_grande(canvas, text, color, size=72, alpha=0.18):
    canvas.saveState()
    canvas.setFillColor(color, alpha=alpha)
    canvas.setFont('Helvetica-Bold', size)
    canvas.translate(canvas._pagesize[0] / 2, canvas._pagesize[1] / 2)
    canvas.rotate(45)
    canvas.drawCentredString(0, 0, text)
    canvas.restoreState()


def _aviso_reporte(canvas):
    """Texto pequeno bottom-center: 'Reporte de consulta - No reemplaza...'."""
    canvas.saveState()
    canvas.setFillColor(colors.HexColor('#555555'))
    canvas.setFont('Helvetica-Oblique', 7)
    canvas.drawCentredString(
        canvas._pagesize[0] / 2,
        22,
        'Reporte de consulta TPE — No reemplaza al documento oficial firmado',
    )
    canvas.restoreState()


def _footer_sha(canvas, sha_corto):
    """Footer con SHA-256 corto en esquina inferior derecha (audit trail)."""
    if not sha_corto:
        return
    canvas.saveState()
    canvas.setFillColor(colors.HexColor('#888888'))
    canvas.setFont('Helvetica', 6)
    canvas.drawRightString(
        canvas._pagesize[0] - 18, 12,
        f'SHA-256: {sha_corto}',
    )
    canvas.restoreState()


def hacer_callback(estado='REPORTE', sha_corto='', extra=None):
    """Construye callback compatible con SimpleDocTemplate.onFirstPage/onLaterPages.

    Args:
        estado: 'BORRADOR' (rojo grande), 'FIRMADO' (verde grande),
                'REPORTE' (aviso gris pequeno) o '' (sin marca).
        sha_corto: 12 primeros chars del SHA-256 del DocumentoAdjunto si aplica.
        extra: callback existente a componer (se ejecuta primero).
    """
    estado = (estado or '').upper()

    def _callback(canvas, doc):
        if extra is not None:
            extra(canvas, doc)

        if estado == 'BORRADOR':
            _marca_diagonal_grande(canvas, 'BORRADOR', colors.HexColor('#b30000'))
        elif estado == 'FIRMADO':
            _marca_diagonal_grande(canvas, 'FIRMADO', colors.HexColor('#0a7e2e'))
        elif estado == 'REPORTE':
            _aviso_reporte(canvas)
        # estado vacio: sin marca, solo SHA si lo hay

        _footer_sha(canvas, sha_corto)

    return _callback


def estado_documento(documento):
    """Determina BORRADOR/FIRMADO desde un documento (Resolucion, AUTOTPE, etc.).

    Reglas:
      - tiene Notificacion (relacion inversa) -> FIRMADO
      - no tiene -> BORRADOR
    """
    if documento is None:
        return ''
    notif = getattr(documento, 'notificacion', None)
    if notif is not None:
        return 'FIRMADO'
    return 'BORRADOR'
