# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('results', '0011_sifter_output'),
    ]

    operations = [
        migrations.DeleteModel(
            name='SIFTER_Output',
        ),
    ]
