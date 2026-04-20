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


class Weight(models.Model):
    pfam = models.TextField(primary_key=True, blank=True)
    conf_code = models.TextField(blank=True)
    weight = models.FloatField(blank=True)

    class Meta:
        managed = False
        db_table = 'weight'
        unique_together = (('pfam', 'conf_code'),)

    def __str__(self):
        return '%s'%self.pfam
