from django.db import models

# Create your models here.
class Histogram(models.Model):
    barHeight = models.DecimalField(max_digits=10,decimal_places=3)
    barWidth = models.DecimalField(max_digits=10,decimal_places=3)

class ErrorHistogramBarsTmp(models.Model):
    numelCat = models.IntegerField()
    famSizeCat = models.IntegerField()
    bin = models.FloatField()
    barHeight = models.IntegerField()
