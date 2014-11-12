# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('weight_db', '0002_delete_weight'),
    ]

    operations = [
        migrations.CreateModel(
            name='Weight',
            fields=[
            ],
            options={
                'db_table': 'weight',
                'managed': False,
            },
            bases=(models.Model,),
        ),
    ]
