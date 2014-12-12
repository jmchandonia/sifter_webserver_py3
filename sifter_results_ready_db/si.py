from haystack import indexes
from sifter_results_ready_db.models import SifterResults


class SifterResultsIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    uniprot_id = indexes.CharField(model_attr='uniprot_id')
    uniprot_acc = indexes.CharField(model_attr='uniprot_acc')

    def get_model(self):
        return SifterResults

    def index_queryset(self, using=None):
        return self.get_model().objects.all()
		