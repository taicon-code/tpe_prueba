# Generated migration to remove obsolete abog table
# The class was removed from models.py in v4.0 but the table remained in the database

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tpe_app', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS `abog`;",
            reverse_sql="",
        ),
    ]
