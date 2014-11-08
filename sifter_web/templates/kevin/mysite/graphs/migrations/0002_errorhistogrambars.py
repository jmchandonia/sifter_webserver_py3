# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('graphs', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ErrorHistogramBars',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('category', models.TextField()),
                ('bin', models.FloatField()),
                ('barHeight', models.IntegerField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
