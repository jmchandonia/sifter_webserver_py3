# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('results', '0020_sifter_output'),
    ]

    operations = [
        migrations.AddField(
            model_name='sifter_output',
            name='ip',
            field=models.CharField(default='0', max_length=45),
            preserve_default=False,
        ),
    ]
