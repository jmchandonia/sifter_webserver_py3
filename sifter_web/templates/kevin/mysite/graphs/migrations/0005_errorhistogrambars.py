# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('graphs', '0004_delete_errorhistogrambars'),
    ]

    operations = [
        migrations.CreateModel(
            name='ErrorHistogramBars',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('numelCat', models.IntegerField()),
                ('famSizeCat', models.IntegerField()),
                ('bin', models.FloatField()),
                ('barHeight', models.IntegerField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
