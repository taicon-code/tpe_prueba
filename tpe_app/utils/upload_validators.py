"""
Validadores de archivos subidos.

NUNCA confiar solo en la extension del nombre ni en el content_type que envia
el cliente: ambos son trivialmente falsificables. Estos validadores leen los
bytes reales del archivo y validan la estructura del formato.
"""
from io import BytesIO

from django.core.exceptions import ValidationError


def client_ip(request):
    """IP del cliente respetando X-Forwarded-For (primero) y REMOTE_ADDR."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR') or None


# Tamanos maximos por defecto (alineados con DATA_UPLOAD_MAX_MEMORY_SIZE en settings)
PDF_MAX_BYTES = 10 * 1024 * 1024   # 10 MB para PDFs escaneados
IMG_MAX_BYTES = 5 * 1024 * 1024    # 5 MB para fotos de PM

_PDF_MAGIC = b'%PDF-'


def _read_head(upload, n):
    """Lee los primeros n bytes del upload sin consumirlo (rebobina al final)."""
    pos = upload.tell() if hasattr(upload, 'tell') else None
    head = upload.read(n)
    if hasattr(upload, 'seek'):
        upload.seek(pos if pos is not None else 0)
    return head


def validar_pdf(upload, max_bytes=PDF_MAX_BYTES):
    """Valida que el upload sea un PDF real (no solo con extension .pdf).

    Comprueba:
      1. Tamano <= max_bytes.
      2. Cabecera empieza con '%PDF-' (RFC 8259 / ISO 32000).
      3. Termina con un trailer plausible ('%%EOF' en los ultimos 1024 bytes).

    Lanza ValidationError con mensaje en espanol si algun chequeo falla.
    """
    if upload is None:
        raise ValidationError('Debe seleccionar un archivo PDF.')

    size = getattr(upload, 'size', None)
    if size is None:
        raise ValidationError('No se pudo determinar el tamano del archivo.')
    if size == 0:
        raise ValidationError('El archivo PDF esta vacio.')
    if size > max_bytes:
        mb = max_bytes // (1024 * 1024)
        raise ValidationError(f'El PDF excede el tamano maximo de {mb} MB.')

    head = _read_head(upload, len(_PDF_MAGIC))
    if not head.startswith(_PDF_MAGIC):
        raise ValidationError(
            'El archivo no es un PDF valido (cabecera incorrecta). '
            'Verifique que sea un PDF real, no un archivo renombrado.'
        )

    # Leer los ultimos 1024 bytes para buscar el trailer EOF
    if hasattr(upload, 'seek'):
        upload.seek(max(0, size - 1024))
        tail = upload.read(1024)
        upload.seek(0)
        if b'%%EOF' not in tail:
            raise ValidationError(
                'El PDF parece estar truncado o corrupto (falta marcador EOF).'
            )

    return True


def validar_imagen(upload, max_bytes=IMG_MAX_BYTES, formatos_permitidos=('JPEG', 'PNG', 'WEBP')):
    """Valida que el upload sea una imagen real abrible por Pillow.

    Comprueba:
      1. Tamano <= max_bytes.
      2. Pillow puede abrir y verificar la estructura del archivo.
      3. El formato detectado por Pillow esta en la whitelist.

    Lanza ValidationError si algun chequeo falla.
    """
    if upload is None:
        raise ValidationError('Debe seleccionar una imagen.')

    size = getattr(upload, 'size', None)
    if size is None:
        raise ValidationError('No se pudo determinar el tamano del archivo.')
    if size == 0:
        raise ValidationError('El archivo de imagen esta vacio.')
    if size > max_bytes:
        mb = max_bytes // (1024 * 1024)
        raise ValidationError(f'La imagen excede el tamano maximo de {mb} MB.')

    # Importacion lazy: Pillow es pesado, solo lo cargamos cuando se usa.
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError as e:
        raise ValidationError(f'Pillow no esta instalado: {e}')

    # Pillow.verify() consume el stream; trabajamos sobre una copia en memoria.
    if hasattr(upload, 'seek'):
        upload.seek(0)
    data = upload.read()
    if hasattr(upload, 'seek'):
        upload.seek(0)

    try:
        img = Image.open(BytesIO(data))
        img.verify()  # Detecta truncamiento, corrupcion, decoradores maliciosos
    except (UnidentifiedImageError, Exception) as e:
        raise ValidationError(
            f'El archivo no es una imagen valida ({e.__class__.__name__}). '
            'Verifique que sea JPG, PNG o WEBP real.'
        )

    # Re-abrir para leer .format (verify() invalida la instancia)
    fmt = Image.open(BytesIO(data)).format
    if fmt not in formatos_permitidos:
        raise ValidationError(
            f'Formato de imagen no permitido: {fmt}. '
            f'Use uno de: {", ".join(formatos_permitidos)}.'
        )

    return True
