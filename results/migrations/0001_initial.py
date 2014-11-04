# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='SIFTER_Output',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('job_id', models.PositiveIntegerField()),
                ('exp_weight', models.DecimalField(max_digits=3, decimal_places=2)),
                ('email', models.EmailField(max_length=75)),
                ('query_method', models.CharField(max_length=30)),
                ('n_proteins', models.PositiveIntegerField()),
                ('n_species', models.PositiveIntegerField()),
                ('n_sequences', models.PositiveIntegerField()),
                ('submission_date', models.DateField()),
                ('result_date', models.DateField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
