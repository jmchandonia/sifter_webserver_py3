# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('term_db', '0005_term_term2term'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Term',
        ),
        migrations.DeleteModel(
            name='Term2Term',
        ),
    ]
