# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Pfam',
            fields=[
            ],
            options={
                'db_table': 'pfam',
                'managed': False,
            },
            bases=(models.Model,),
        ),
    ]
