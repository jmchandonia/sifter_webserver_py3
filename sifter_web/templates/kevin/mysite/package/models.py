from django.db import models

class Histogram(models.Model):
    barHeight = models.DecimalField()
    barWidth = models.DecimalField()
