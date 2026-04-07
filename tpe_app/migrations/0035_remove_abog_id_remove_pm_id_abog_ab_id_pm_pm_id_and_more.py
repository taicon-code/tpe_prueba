# Migración 0035 — REESCRITA MANUALMENTE v3
#
# Problema: Django no puede renombrar PKs de 'pm' y 'abog' porque MySQL
# valida los FK constraints incluso con FK_CHECKS=0 en ciertas versiones.
#
# Solución: eliminar todos los FK constraints que referencian pm.id y abog.id,
# renombrar las columnas, y recrear los constraints apuntando al nuevo nombre.
#
# Se usa SeparateDatabaseAndState para que la parte de estado de Django
# (RemoveField/AddField) no genere DDL adicional.

from django.db import migrations, models

DROP_AND_RENAME_SQL = """
SET FOREIGN_KEY_CHECKS = 0;

-- 1. Eliminar FK constraints que referencian pm.id
ALTER TABLE `pm_sim`
    DROP FOREIGN KEY `PM_SIM_ID_PM_a0844f66_fk_PM_id`;

-- 2. Eliminar FK constraints que referencian abog.id
ALTER TABLE `abog_sim`
    DROP FOREIGN KEY `abog_sim_ID_ABOG_75f28ca9_fk_abog_id`;
ALTER TABLE `autotpe`
    DROP FOREIGN KEY `autotpe_ID_ABOG_d6e818d4_fk_abog_id`;
ALTER TABLE `dictamen`
    DROP FOREIGN KEY `dictamen_ID_ABOG_250cc375_fk_abog_id`;
ALTER TABLE `res`
    DROP FOREIGN KEY `res_ID_ABOG_ced573f3_fk_abog_id`;
ALTER TABLE `rr`
    DROP FOREIGN KEY `rr_ID_ABOG_4ad0335e_fk_abog_id`;

-- 3. Renombrar pk de pm: id (bigint) → pm_id (bigint)
ALTER TABLE `pm`
    CHANGE COLUMN `id` `pm_id` bigint NOT NULL AUTO_INCREMENT;

-- 4. Renombrar pk de abog: id (bigint) → ab_id (bigint)
ALTER TABLE `abog`
    CHANGE COLUMN `id` `ab_id` bigint NOT NULL AUTO_INCREMENT;

-- 5. Hacer PM_CI nullable
ALTER TABLE `pm`
    MODIFY COLUMN `PM_CI` DECIMAL(13,0) NULL DEFAULT NULL;

-- 6. Recrear FK constraints apuntando a los nuevos nombres de columna
ALTER TABLE `pm_sim`
    ADD CONSTRAINT `PM_SIM_ID_PM_a0844f66_fk_PM_id`
    FOREIGN KEY (`ID_PM`) REFERENCES `pm` (`pm_id`);

ALTER TABLE `abog_sim`
    ADD CONSTRAINT `abog_sim_ID_ABOG_75f28ca9_fk_abog_id`
    FOREIGN KEY (`ID_ABOG`) REFERENCES `abog` (`ab_id`);

ALTER TABLE `autotpe`
    ADD CONSTRAINT `autotpe_ID_ABOG_d6e818d4_fk_abog_id`
    FOREIGN KEY (`ID_ABOG`) REFERENCES `abog` (`ab_id`);

ALTER TABLE `dictamen`
    ADD CONSTRAINT `dictamen_ID_ABOG_250cc375_fk_abog_id`
    FOREIGN KEY (`ID_ABOG`) REFERENCES `abog` (`ab_id`);

ALTER TABLE `res`
    ADD CONSTRAINT `res_ID_ABOG_ced573f3_fk_abog_id`
    FOREIGN KEY (`ID_ABOG`) REFERENCES `abog` (`ab_id`);

ALTER TABLE `rr`
    ADD CONSTRAINT `rr_ID_ABOG_4ad0335e_fk_abog_id`
    FOREIGN KEY (`ID_ABOG`) REFERENCES `abog` (`ab_id`);

SET FOREIGN_KEY_CHECKS = 1;
"""

REVERSE_SQL = """
SET FOREIGN_KEY_CHECKS = 0;

ALTER TABLE `pm_sim`
    DROP FOREIGN KEY `PM_SIM_ID_PM_a0844f66_fk_PM_id`;
ALTER TABLE `abog_sim`
    DROP FOREIGN KEY `abog_sim_ID_ABOG_75f28ca9_fk_abog_id`;
ALTER TABLE `autotpe`
    DROP FOREIGN KEY `autotpe_ID_ABOG_d6e818d4_fk_abog_id`;
ALTER TABLE `dictamen`
    DROP FOREIGN KEY `dictamen_ID_ABOG_250cc375_fk_abog_id`;
ALTER TABLE `res`
    DROP FOREIGN KEY `res_ID_ABOG_ced573f3_fk_abog_id`;
ALTER TABLE `rr`
    DROP FOREIGN KEY `rr_ID_ABOG_4ad0335e_fk_abog_id`;

ALTER TABLE `pm`
    CHANGE COLUMN `pm_id` `id` bigint NOT NULL AUTO_INCREMENT;
ALTER TABLE `abog`
    CHANGE COLUMN `ab_id` `id` bigint NOT NULL AUTO_INCREMENT;

ALTER TABLE `pm_sim`
    ADD CONSTRAINT `PM_SIM_ID_PM_a0844f66_fk_PM_id`
    FOREIGN KEY (`ID_PM`) REFERENCES `pm` (`id`);
ALTER TABLE `abog_sim`
    ADD CONSTRAINT `abog_sim_ID_ABOG_75f28ca9_fk_abog_id`
    FOREIGN KEY (`ID_ABOG`) REFERENCES `abog` (`id`);
ALTER TABLE `autotpe`
    ADD CONSTRAINT `autotpe_ID_ABOG_d6e818d4_fk_abog_id`
    FOREIGN KEY (`ID_ABOG`) REFERENCES `abog` (`id`);
ALTER TABLE `dictamen`
    ADD CONSTRAINT `dictamen_ID_ABOG_250cc375_fk_abog_id`
    FOREIGN KEY (`ID_ABOG`) REFERENCES `abog` (`id`);
ALTER TABLE `res`
    ADD CONSTRAINT `res_ID_ABOG_ced573f3_fk_abog_id`
    FOREIGN KEY (`ID_ABOG`) REFERENCES `abog` (`id`);
ALTER TABLE `rr`
    ADD CONSTRAINT `rr_ID_ABOG_4ad0335e_fk_abog_id`
    FOREIGN KEY (`ID_ABOG`) REFERENCES `abog` (`id`);

SET FOREIGN_KEY_CHECKS = 1;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('tpe_app', '0034_alter_agenda_ag_fecprog'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(

            # ── Operaciones reales en la DB ──────────────────────────────────
            database_operations=[
                migrations.RunSQL(
                    sql=DROP_AND_RENAME_SQL,
                    reverse_sql=REVERSE_SQL,
                ),
            ],

            # ── Solo actualiza el estado interno de Django (sin DDL) ─────────
            state_operations=[
                migrations.RemoveField(model_name='abog', name='id'),
                migrations.RemoveField(model_name='pm',   name='id'),
                migrations.AddField(
                    model_name='abog',
                    name='ab_id',
                    field=models.AutoField(
                        db_column='ab_id', primary_key=True, serialize=False
                    ),
                ),
                migrations.AddField(
                    model_name='pm',
                    name='pm_id',
                    field=models.AutoField(
                        db_column='pm_id', primary_key=True, serialize=False
                    ),
                ),
                migrations.AlterField(
                    model_name='pm',
                    name='PM_CI',
                    field=models.DecimalField(
                        blank=True, decimal_places=0, max_digits=13,
                        null=True, unique=True,
                        verbose_name='Cédula de Identidad',
                    ),
                ),
            ],
        ),
    ]
