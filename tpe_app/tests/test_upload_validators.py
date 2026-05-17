"""Tests para tpe_app.utils.upload_validators."""
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, SimpleTestCase
from PIL import Image

from tpe_app.utils.upload_validators import (
    client_ip,
    validar_imagen,
    validar_pdf,
)


def _png_bytes(w=4, h=4, color=(255, 0, 0)):
    buf = BytesIO()
    Image.new('RGB', (w, h), color).save(buf, format='PNG')
    return buf.getvalue()


def _pdf_minimo():
    return b'%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<<>>\n%%EOF\n'


class ValidarPdfTests(SimpleTestCase):
    def test_pdf_valido_pasa(self):
        f = SimpleUploadedFile('ok.pdf', _pdf_minimo(), content_type='application/pdf')
        self.assertTrue(validar_pdf(f))

    def test_pdf_cabecera_invalida_falla(self):
        f = SimpleUploadedFile('fake.pdf', b'NO PDF AQUI', content_type='application/pdf')
        with self.assertRaises(ValidationError) as ctx:
            validar_pdf(f)
        self.assertIn('cabecera incorrecta', str(ctx.exception))

    def test_pdf_vacio_falla(self):
        f = SimpleUploadedFile('empty.pdf', b'', content_type='application/pdf')
        with self.assertRaises(ValidationError):
            validar_pdf(f)

    def test_pdf_excede_tamano_falla(self):
        # Construye un "PDF" valido pero gigante
        big = _pdf_minimo() + (b'\0' * (15 * 1024 * 1024))
        f = SimpleUploadedFile('big.pdf', big, content_type='application/pdf')
        with self.assertRaises(ValidationError) as ctx:
            validar_pdf(f, max_bytes=10 * 1024 * 1024)
        self.assertIn('tamano maximo', str(ctx.exception))

    def test_pdf_sin_eof_falla(self):
        # PDF con cabecera correcta pero sin marcador EOF
        truncado = b'%PDF-1.4\n' + (b'x' * 2000)
        f = SimpleUploadedFile('trunc.pdf', truncado, content_type='application/pdf')
        with self.assertRaises(ValidationError) as ctx:
            validar_pdf(f)
        self.assertIn('truncado', str(ctx.exception))

    def test_pdf_none_falla(self):
        with self.assertRaises(ValidationError):
            validar_pdf(None)


class ValidarImagenTests(SimpleTestCase):
    def test_png_valido_pasa(self):
        f = SimpleUploadedFile('ok.png', _png_bytes(), content_type='image/png')
        self.assertTrue(validar_imagen(f))

    def test_archivo_falso_falla(self):
        f = SimpleUploadedFile('fake.jpg', b'NO SOY IMAGEN', content_type='image/jpeg')
        with self.assertRaises(ValidationError) as ctx:
            validar_imagen(f)
        self.assertIn('no es una imagen valida', str(ctx.exception))

    def test_imagen_vacia_falla(self):
        f = SimpleUploadedFile('empty.png', b'', content_type='image/png')
        with self.assertRaises(ValidationError):
            validar_imagen(f)

    def test_formato_no_permitido_falla(self):
        # GIF deberia rechazarse porque whitelist es JPEG/PNG/WEBP
        buf = BytesIO()
        Image.new('RGB', (4, 4), (0, 255, 0)).save(buf, format='GIF')
        f = SimpleUploadedFile('img.gif', buf.getvalue(), content_type='image/gif')
        with self.assertRaises(ValidationError) as ctx:
            validar_imagen(f)
        self.assertIn('Formato de imagen no permitido', str(ctx.exception))

    def test_none_falla(self):
        with self.assertRaises(ValidationError):
            validar_imagen(None)


class ClientIpTests(SimpleTestCase):
    def setUp(self):
        self.rf = RequestFactory()

    def test_remote_addr(self):
        req = self.rf.get('/')
        req.META['REMOTE_ADDR'] = '10.0.0.5'
        self.assertEqual(client_ip(req), '10.0.0.5')

    def test_x_forwarded_for_tiene_prioridad(self):
        req = self.rf.get('/')
        req.META['REMOTE_ADDR'] = '10.0.0.5'
        req.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.10, 10.0.0.99'
        self.assertEqual(client_ip(req), '203.0.113.10')

    def test_sin_headers_retorna_none(self):
        req = self.rf.get('/')
        # RequestFactory pone REMOTE_ADDR='127.0.0.1' por defecto
        req.META.pop('REMOTE_ADDR', None)
        self.assertIsNone(client_ip(req))
