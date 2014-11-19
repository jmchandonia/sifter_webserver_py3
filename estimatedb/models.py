# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
#
# Also note: You'll have to insert the output of 'django-admin.py sqlcustom [app_label]'
# into your database.
from __future__ import unicode_literals

from django.db import models


class Errorhistogrambars(models.Model):
    numelcat = models.IntegerField(db_column='numelCat', primary_key=True, blank=True, null=False)  # Field name made lowercase.
    famsizecat = models.IntegerField(db_column='famSizeCat', primary_key=True, blank=True, null=False)  # Field name made lowercase.
    bin = models.FloatField(blank=True, null=False)
    barheight = models.IntegerField(db_column='barHeight', blank=True, null=False)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'ErrorHistogramBars'
