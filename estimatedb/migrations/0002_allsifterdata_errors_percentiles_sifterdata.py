# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('estimatedb', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Allsifterdata',
            fields=[
            ],
            options={
                'db_table': 'AllSifterData',
                'managed': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Errors',
            fields=[
            ],
            options={
                'db_table': 'Errors',
                'managed': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Percentiles',
            fields=[
            ],
            options={
                'db_table': 'Percentiles',
                'managed': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Sifterdata',
            fields=[
            ],
            options={
                'db_table': 'SifterData',
                'managed': False,
            },
            bases=(models.Model,),
        ),
    ]
