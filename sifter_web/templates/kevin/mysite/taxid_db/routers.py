class TaxidDbRouter(object):
    """
    A router to control all database operations on models in the
    taxid_db application.
    """
    def db_for_read(self, model, **hints):
        """
        Attempts to read taxid_db models go to taxid_db.
        """
        if model._meta.app_label == 'taxid_db':
            return 'taxid_db'
        return None

    def db_for_write(self, model, **hints):
        """
        Our 'taxid_db' DB is read-only.
        """
        return False

    def allow_relation(self, obj1, obj2, **hints):
        """
        Forbid relations from/to taxid_db to/from other apps.
        """
        obj1_is_legacy = (obj1._meta.app_label == 'taxid_db')
        obj2_is_legacy = (obj2._meta.app_label == 'taxid_db')
        return obj1_is_legacy == obj2_is_legacy

    def allow_migrate(self, db, model):
        """
        Make sure the taxid_db app only appears in the 'taxid_db'
        database.
        """
        if db == 'taxid_db':
           return model._meta.app_label == 'taxid_db'
        elif model._meta.app_label == 'taxid_db':
           return False
        return None
