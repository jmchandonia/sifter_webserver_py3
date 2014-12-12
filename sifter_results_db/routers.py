class sifter_results_db_router(object):
    """
    A router to control all database operations on models in the
    sifter_results_db application.
    """
    def db_for_read(self, model, **hints):
        """
        Attempts to read sifter_results_db models go to sifter_results_db.
        """
        if model._meta.app_label == 'sifter_results_db':
            return 'sifter_results_db'
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write sifter_results_db models go to sifter_results_db.
        """
        return False

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in the sifter_results_db app is involved.
        """
        if obj1._meta.app_label == 'sifter_results_db' or \
           obj2._meta.app_label == 'sifter_results_db':
           return True
        return None

    def allow_migrate(self, db, model):
        """
        Make sure the sifter_results_db app only appears in the 'sifter_results_db'
        database.
        """
        if db == 'sifter_results_db':
            return model._meta.app_label == 'sifter_results_db'
        elif model._meta.app_label == 'sifter_results_db':
            return False
        return None
