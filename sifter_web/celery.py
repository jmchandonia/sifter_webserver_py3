from __future__ import absolute_import

from celery import Celery
from django.conf import settings

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sifter_web.settings')


def get_broker_url():
    return os.environ.get('CELERY_BROKER_URL', 'memory://')


def get_result_backend():
    return os.environ.get('CELERY_RESULT_BACKEND', 'cache+memory://')


app = Celery('sifter_web',
             broker=get_broker_url(),
             backend=get_result_backend(),
             include=['sifter_web.tasks'])
app.config_from_object('django.conf:settings', namespace='CELERY')

# Optional configuration, see the application user guide.
app.conf.update(
    task_result_expires=36000,
    task_always_eager=getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False),
    task_eager_propagates=getattr(settings, 'CELERY_TASK_EAGER_PROPAGATES', False),
)


if __name__ == '__main__':
    app.start()
