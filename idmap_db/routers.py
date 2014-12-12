class idmap_db_router(object):
    """
    A router to control all database operations on models in the
    idmap_db application.
    """
    def db_for_read(self, model, **hints):
        """
        Attempts to read idmap_db models go to idmap_db.
        """
        if model._meta.app_label == 'idmap_db':
            return 'idmap_db'
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write idmap_db models go to idmap_db.
        """
        return False

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in the idmap_db app is involved.
        """
        if obj1._meta.app_label == 'idmap_db' or \
           obj2._meta.app_label == 'idmap_db':
           return True
        return None

    def allow_migrate(self, db, model):
        """
        Make sure the idmap_db app only appears in the 'idmap_db'
        database.
        """
        if db == 'idmap_db':
            return model._meta.app_label == 'idmap_db'
        elif model._meta.app_label == 'idmap_db':
            return False
        return None
