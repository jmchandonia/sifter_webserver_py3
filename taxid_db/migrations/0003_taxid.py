# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('taxid_db', '0002_delete_taxid'),
    ]

    operations = [
        migrations.CreateModel(
            name='Taxid',
            fields=[
            ],
            options={
                'db_table': 'taxid',
                'managed': False,
            },
            bases=(models.Model,),
        ),
    ]
