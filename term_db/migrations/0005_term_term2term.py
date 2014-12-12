# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('term_db', '0004_auto_20141110_0233'),
    ]

    operations = [
        migrations.CreateModel(
            name='Term',
            fields=[
            ],
            options={
                'db_table': 'term_db_term',
                'managed': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Term2Term',
            fields=[
            ],
            options={
                'db_table': 'term2term',
                'managed': False,
            },
            bases=(models.Model,),
        ),
    ]
