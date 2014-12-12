# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('weight_db', '0003_weight'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Weight',
        ),
    ]
