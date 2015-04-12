class pfamdb_router(object):
    """
    A router to control all database operations on models in the
    pfamdb application.
    """
    def db_for_read(self, model, **hints):
        """
        Attempts to read pfamdb models go to pfamdb.
        """
        if model._meta.app_label == 'pfamdb':
            return 'pfamdb'
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write pfamdb models go to pfamdb.
        """
        return False

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in the pfamdb app is involved.
        """
        if obj1._meta.app_label == 'pfamdb' or \
           obj2._meta.app_label == 'pfamdb':
           return True
        return None

    def allow_migrate(self, db, model):
        """
        Make sure the pfamdb app only appears in the 'pfamdb'
        database.
        """
        if db == 'pfamdb':
            return model._meta.app_label == 'pfamdb'
        elif model._meta.app_label == 'pfamdb':
            return False
        return None
