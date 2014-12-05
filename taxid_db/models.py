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


class Taxid(models.Model):
    tax_id = models.IntegerField(primary_key=True, blank=True)
    tax_name = models.TextField(blank=True)

    class Meta:
        managed = False
        db_table = 'taxid'

    def get_absolute_url(self):
        return "/predictions/?taxid=%s" % self.tax_id

    def __unicode__(self):
        return '%s (taxid:%s)'%(self.tax_name,self.tax_id)
