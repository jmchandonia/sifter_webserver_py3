class term_db_router(object):
    """
    A router to control all database operations on models in the
    term_db application.
    """
    def db_for_read(self, model, **hints):
        """
        Attempts to read term_db models go to term_db.
        """
        if model._meta.app_label == 'term_db':
            return 'term_db'
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write term_db models go to term_db.
        """
        return False

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in the term_db app is involved.
        """
        if obj1._meta.app_label == 'term_db' or \
           obj2._meta.app_label == 'term_db':
           return True
        return None

    def allow_migrate(self, db, model):
        """
        Make sure the term_db app only appears in the 'term_db'
        database.
        """
        if db == 'term_db':
            return model._meta.app_label == 'term_db'
        elif model._meta.app_label == 'term_db':
            return False
        return None
