class EstimateDbRouter(object):
    """
    A router to control all database operations on models in the
    estimatedb application.
    """
    def db_for_read(self, model, **hints):
        """
        Attempts to read estimatedb models go to estimatedb.
        """
        if model._meta.app_label == 'estimatedb':
            return 'estimatedb'
        return None

    def db_for_write(self, model, **hints):
        """
        Our 'estimatedb' DB is read-only.
        """
        return False

    def allow_relation(self, obj1, obj2, **hints):
        """
        Forbid relations from/to estimatedb to/from other apps.
        """
        obj1_is_legacy = (obj1._meta.app_label == 'estimatedb')
        obj2_is_legacy = (obj2._meta.app_label == 'estimatedb')
        return obj1_is_legacy == obj2_is_legacy

    def allow_migrate(self, db, model):
        """
        Make sure the estimatedb app only appears in the 'estimatedb'
        database.
        """
        if db == 'estimatedb':
           return model._meta.app_label == 'estimatedb'
        elif model._meta.app_label == 'estimatedb':
           return False
        return None
