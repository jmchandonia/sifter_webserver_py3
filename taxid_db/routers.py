class taxid_db_router(object):
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
        Attempts to write taxid_db models go to taxid_db.
        """
        return False

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in the taxid_db app is involved.
        """
        if obj1._meta.app_label == 'taxid_db' or \
           obj2._meta.app_label == 'taxid_db':
           return True
        return None

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
