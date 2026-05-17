"""Calcula SHA-256 y tamano de DocumentoAdjunto historicos sin hash.

Solo procesa documentos con sha256 vacio. Documentos cuyo archivo ya no
existe en disco se reportan y se omiten (no fallan el comando).

Uso:
    python manage.py rehash_documentos
    python manage.py rehash_documentos --dry-run
"""
import hashlib
import logging

from django.core.management.base import BaseCommand

from tpe_app.models import DocumentoAdjunto

security_log = logging.getLogger('tpe_app.security')


class Command(BaseCommand):
    help = 'Calcula SHA-256 y tamano de DocumentoAdjunto historicos sin hash.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Reporta cuantos se procesarian sin escribir cambios.',
        )

    def handle(self, *args, **opts):
        dry_run = opts['dry_run']
        pendientes = DocumentoAdjunto.objects.filter(sha256='').order_by('id')
        total = pendientes.count()
        self.stdout.write(f'Documentos sin SHA-256: {total}')

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry-run: no se escribiran cambios.'))
            return

        procesados = 0
        omitidos = 0
        for doc in pendientes.iterator():
            if not doc.archivo:
                omitidos += 1
                self.stdout.write(self.style.WARNING(
                    f'  - omitido (sin archivo): id={doc.id} nombre={doc.nombre}'
                ))
                continue
            try:
                sha = hashlib.sha256()
                tam = 0
                doc.archivo.open('rb')
                try:
                    for chunk in doc.archivo.chunks():
                        sha.update(chunk)
                        tam += len(chunk)
                finally:
                    doc.archivo.close()
                doc.sha256 = sha.hexdigest()
                doc.tamano_bytes = tam
                doc.save(update_fields=['sha256', 'tamano_bytes'])
                procesados += 1
                self.stdout.write(f'  + {doc.sha256[:12]} ({tam} bytes) id={doc.id}')
            except FileNotFoundError:
                omitidos += 1
                self.stdout.write(self.style.WARNING(
                    f'  - omitido (archivo no existe en disco): id={doc.id} {doc.archivo.name}'
                ))
            except Exception as e:
                omitidos += 1
                self.stdout.write(self.style.ERROR(
                    f'  ! error id={doc.id}: {e.__class__.__name__}: {e}'
                ))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Procesados: {procesados}'))
        if omitidos:
            self.stdout.write(self.style.WARNING(f'Omitidos:   {omitidos}'))
        security_log.info('REHASH_DOCS procesados=%s omitidos=%s', procesados, omitidos)
