# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('graphs', '0002_errorhistogrambars'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='errorhistogrambars',
            name='category',
        ),
        migrations.AddField(
            model_name='errorhistogrambars',
            name='famSizeCat',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='errorhistogrambars',
            name='numelCat',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
    ]
