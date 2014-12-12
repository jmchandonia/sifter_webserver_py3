# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('results', '0019_delete_sifter_output'),
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
                ('sifter_EXP_choices', models.BooleanField(default=True)),
                ('n_proteins', models.PositiveIntegerField()),
                ('species', models.PositiveIntegerField()),
                ('n_functions', models.PositiveIntegerField()),
                ('n_sequences', models.PositiveIntegerField()),
                ('submission_date', models.DateField()),
                ('result_date', models.DateField()),
                ('input_file', models.FilePathField()),
                ('output_file', models.FilePathField()),
                ('deleted', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
