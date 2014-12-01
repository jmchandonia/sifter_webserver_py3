from haystack import indexes
from taxid_db.models import Taxid


class TaxidIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    tax_id = indexes.CharField(model_attr='tax_id')
    tax_name = indexes.CharField(model_attr='tax_name')
    suggestions = indexes.FacetCharField()
    content_auto_taxname = indexes.EdgeNgramField(model_attr='tax_name')
    content_auto_taxid = indexes.EdgeNgramField(model_attr='tax_id')

    def get_model(self):
        return Taxid
		
		
    def prepare(self, obj):
        prepared_data = super(TaxidIndex, self).prepare(obj)
        prepared_data['suggestions'] = prepared_data['text']
        return prepared_data

    def index_queryset(self, using=None):
        return self.get_model().objects.all()
				