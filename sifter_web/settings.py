"""
Django settings for sifter_web project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import djcelery
djcelery.setup_loader()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TRACK_STARTED=True

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '=e@&t9o*8k%hxyuc6x8==!&ujxocc@1^(czt7p4urb+1m$#5xm'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'autocomplete_light',
    'djcelery',
    'chartit',
	'haystack',
    'results',
    'graphs',
    'term_db',
    'weight_db',
    'sifter_results_db',
    'taxid_db',
    'estimatedb',
    'sifter_results_ready_db',
    'idmap_db',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'sifter_web.urls'

WSGI_APPLICATION = 'sifter_web.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    },        
    'term_db': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, "my_dbs","term_db.sqlite3"),
    },
    'weight_db': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, "my_dbs","weight_db.sqlite3"),
    },
    'sifter_results_db': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, "my_dbs","sifter_results_cmp_small.sqlite3"),
    },
    'term_db': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, "my_dbs","term_db.sqlite3"),
    },
    'taxid_db': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, "my_dbs","taxid_db.sqlite3"),
    },
    'estimatedb': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, "my_dbs",'estimate.sqlite3'),
    },
    'sifter_results_ready_db': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/lab/app/python/python_mohammad/SIFTER_jobs/webserver/sifter_results_cmp_ready_leaves.sqlite3',
    },
    'idmap_db': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/lab/app/python/python_mohammad/SIFTER_jobs/webserver/idmap_db.sqlite3',
    },
}
DATABASE_ROUTERS = [
    'term_db.routers.term_db_router',
    'weight_db.routers.weight_db_router',
    'sifter_results_db.routers.sifter_results_db_router',
    'taxid_db.routers.taxid_db_router',
    'estimatedb.routers.EstimateDbRouter',
    'sifter_results_ready_db.routers.sifter_results_ready_db_router',
    'idmap_db.routers.idmap_db_router'
    ]
	
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
        'URL': 'http://127.0.0.1:8983/solr',
        # ...or for multicore...
        # 'URL': 'http://127.0.0.1:8983/solr/mysite',
    },
}

	
# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'

TEMPLATE_DIRS= (os.path.join(BASE_DIR,"sifter_web","templates"),)

BROKER_URL = 'django://'


if DEBUG:
    MEDIA_URL='/media/'
    STATIC_ROOT = os.path.join(BASE_DIR,"sifter_web","static","static-only")
    MEDIA_ROOT = os.path.join(BASE_DIR,"sifter_web","static","media")
    STATICFILES_DIRS = (os.path.join(BASE_DIR,"sifter_web","static","static"),)
    
    
    