# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('graphs', '0003_auto_20141103_2350'),
    ]

    operations = [
        migrations.DeleteModel(
            name='ErrorHistogramBars',
        ),
    ]
