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


class SifterResults(models.Model):
    uniprot_id = models.TextField(primary_key=True, blank=True)
    uniprot_acc = models.TextField(blank=True)
    tax_id = models.IntegerField(blank=True)
    mode = models.TextField(blank=True)
    preds = models.BinaryField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'sifter_results'
        unique_together = (('uniprot_id', 'uniprot_acc', 'tax_id', 'mode'),)
    
    def __str__(self):
        return '%s'%self.uniprot_id
