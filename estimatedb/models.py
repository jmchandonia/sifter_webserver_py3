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


class Allsifterdata(models.Model):
    type = models.TextField(primary_key=True, blank=True)
    pfam = models.TextField(blank=True)
    numterms = models.IntegerField(db_column='numTerms', blank=True)  # Field name made lowercase.
    famsize = models.IntegerField(db_column='famSize', blank=True)  # Field name made lowercase.
    maxfun = models.IntegerField(db_column='maxFun', blank=True)  # Field name made lowercase.
    numel = models.IntegerField(blank=True)
    time = models.FloatField(blank=True)
    fam = models.TextField(blank=True)

    class Meta:
        managed = False
        db_table = 'AllSifterData'
        unique_together = (('type', 'pfam', 'numterms', 'famsize', 'maxfun', 'numel', 'time', 'fam'),)


class Errorhistogrambars(models.Model):
    numelcat = models.IntegerField(db_column='numelCat', primary_key=True, blank=True)  # Field name made lowercase.
    famsizecat = models.IntegerField(db_column='famSizeCat', blank=True)  # Field name made lowercase.
    bin = models.FloatField(blank=True)
    barheight = models.IntegerField(db_column='barHeight', blank=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'ErrorHistogramBars'
        unique_together = (('numelcat', 'famsizecat'),)


class Errors(models.Model):
    numelcat = models.IntegerField(db_column='numelCat', primary_key=True, blank=True)  # Field name made lowercase.
    famsizecat = models.IntegerField(db_column='famSizeCat', blank=True)  # Field name made lowercase.
    error = models.FloatField(blank=True)
    famsize = models.IntegerField(db_column='famSize', blank=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Errors'
        unique_together = (('numelcat', 'famsizecat'),)


class Percentiles(models.Model):
    numelcat = models.IntegerField(db_column='numelCat', primary_key=True, blank=True)  # Field name made lowercase.
    famsizecat = models.IntegerField(db_column='famSizeCat', blank=True)  # Field name made lowercase.
    per95 = models.FloatField(blank=True)
    per999 = models.FloatField(blank=True)

    class Meta:
        managed = False
        db_table = 'Percentiles'
        unique_together = (('numelcat', 'famsizecat'),)


class Sifterdata(models.Model):
    type = models.TextField(primary_key=True, blank=True)
    pfam = models.TextField(blank=True)
    numterms = models.IntegerField(db_column='numTerms', blank=True)  # Field name made lowercase.
    famsize = models.IntegerField(db_column='famSize', blank=True)  # Field name made lowercase.
    maxfun = models.IntegerField(db_column='maxFun', blank=True)  # Field name made lowercase.
    numel = models.IntegerField(blank=True)
    time = models.FloatField(blank=True)

    class Meta:
        managed = False
        db_table = 'SifterData'
        unique_together = (('type', 'pfam', 'numterms', 'famsize', 'maxfun', 'numel', 'time'),)
