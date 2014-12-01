from haystack import indexes
from term_db.models import Term


class TermIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    acc = indexes.CharField(model_attr='acc')
    name = indexes.CharField(model_attr='name')
    suggestions = indexes.FacetCharField()
    content_auto_name = indexes.EdgeNgramField(model_attr='name')
    content_auto_acc = indexes.EdgeNgramField(model_attr='acc')	

    def get_model(self):
        return Term
		

    def prepare(self, obj):
        prepared_data = super(TermIndex, self).prepare(obj)
        prepared_data['suggestions'] = prepared_data['text']
        return prepared_data

    def index_queryset(self, using=None):
        return self.get_model().objects.all()
		