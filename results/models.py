from django.db import models

# Create your models here.

class SIFTER_Output(models.Model):
    job_id = models.PositiveIntegerField() #0 to 2147483647
    exp_weight = models.DecimalField(max_digits=3,decimal_places=2) #0.00-1.00
    email = models.EmailField()
    query_method = models.CharField(max_length=30)
    sifter_EXP_choices = models.BooleanField(default=True) #True: EXP-Modle, False: ALL-Model
    n_proteins = models.PositiveIntegerField()
    n_species = models.PositiveIntegerField()
    n_functions = models.PositiveIntegerField()
    n_sequences = models.PositiveIntegerField()
    submission_date = models.DateField()
    result_date = models.DateField()
    input_file=models.FileField()
    output_file=models.FileField()    
    def __unicode__(self):
        return '%s'%self.job_id
    
    def was_submitted_recently(self):
        return self.result_date >= timezone.now() - datetime.timedelta(days=15)
