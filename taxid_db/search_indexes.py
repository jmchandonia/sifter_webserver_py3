from haystack import indexes
from taxid_db.models import Taxid


class TaxidIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    tax_id = indexes.CharField(model_attr='tax_id')
    tax_name = indexes.CharField(model_attr='tax_name')
    short_name = indexes.CharField(model_attr='short_name')
    content_auto_taxname = indexes.EdgeNgramField(model_attr='tax_name')
    content_auto_shortname = indexes.EdgeNgramField(model_attr='short_name')
    content_auto_taxid = indexes.EdgeNgramField(model_attr='tax_id')

    def get_model(self):
        return Taxid
		
    def index_queryset(self, using=None):
        return self.get_model().objects.all()
				