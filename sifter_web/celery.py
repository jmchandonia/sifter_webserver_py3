from __future__ import absolute_import

from celery import Celery

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sifter_web.settings')


app = Celery('sifter_web',
             broker='amqp://',
             backend='amqp://',
             include=['sifter_web.tasks'])

# Optional configuration, see the application user guide.
app.conf.update(
    CELERY_TASK_RESULT_EXPIRES=36000,
)


if __name__ == '__main__':
    app.start()
