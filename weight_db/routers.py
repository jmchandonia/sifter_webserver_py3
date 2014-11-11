class weight_db_router(object):
    """
    A router to control all database operations on models in the
    weight_db application.
    """
    def db_for_read(self, model, **hints):
        """
        Attempts to read weight_db models go to weight_db.
        """
        if model._meta.app_label == 'weight_db':
            return 'weight_db'
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write weight_db models go to weight_db.
        """
        return False

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in the weight_db app is involved.
        """
        if obj1._meta.app_label == 'weight_db' or \
           obj2._meta.app_label == 'weight_db':
           return True
        return None

    def allow_migrate(self, db, model):
        """
        Make sure the weight_db app only appears in the 'weight_db'
        database.
        """
        if db == 'weight_db':
            return model._meta.app_label == 'weight_db'
        elif model._meta.app_label == 'weight_db':
            return False
        return None
