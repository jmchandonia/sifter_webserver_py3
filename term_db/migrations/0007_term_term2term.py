# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('term_db', '0006_auto_20141111_0034'),
    ]

    operations = [
        migrations.CreateModel(
            name='Term',
            fields=[
            ],
            options={
                'db_table': 'term',
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
