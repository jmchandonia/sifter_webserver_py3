from haystack import indexes
from sifter_results_ready_db.models import SifterResults


class SifterResultsIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    uniprot_id = indexes.CharField(model_attr='uniprot_id')
    suggestions = indexes.FacetCharField()
    content_auto_uniprotid= indexes.EdgeNgramField(model_attr='uniprotid')

    def get_model(self):
        return SifterResults
		
    def prepare(self, obj):
        prepared_data = super(SifterResultsIndex, self).prepare(obj)
        prepared_data['suggestions'] = prepared_data['text']
        return prepared_data

    def index_queryset(self, using=None):
        return self.get_model().objects.all()
		