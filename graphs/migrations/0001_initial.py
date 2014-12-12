# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ErrorHistogramBarsTmp',
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
        migrations.CreateModel(
            name='Histogram',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('barHeight', models.DecimalField(max_digits=10, decimal_places=3)),
                ('barWidth', models.DecimalField(max_digits=10, decimal_places=3)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
