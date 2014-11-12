# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('results', '0013_sifter_output'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sifter_output',
            name='input_file',
            field=models.FilePathField(),
        ),
        migrations.AlterField(
            model_name='sifter_output',
            name='output_file',
            field=models.FilePathField(),
        ),
    ]
