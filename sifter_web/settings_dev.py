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
import re
djcelery.setup_loader()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


def get_secret_key(default='development-only-insecure-secret-key'):
    return os.environ.get('DJANGO_SECRET_KEY', default)

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TRACK_STARTED=True
CELERY_IMPORTS = ("tasks",)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_secret_key()

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
    'pfamdb',    
)

MIDDLEWARE_CLASSES = (
#	'django.middleware.common.BrokenLinkEmailsMiddleware',    
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

MyDB_DIR = os.path.join(os.path.dirname(BASE_DIR),"my_dbs")

# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR,'db.sqlite3'),
    },        
    'term_db': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(MyDB_DIR,"term_db.sqlite3"),
    },
    'weight_db': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(MyDB_DIR,"weight_db.sqlite3"),
    },
    'sifter_results_db': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(MyDB_DIR,"sifter_results_cmp_040315.sqlite3"),
    },
    'term_db': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(MyDB_DIR,"term_db.sqlite3"),
    },
    'taxid_db': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(MyDB_DIR,"taxid_db_wP.sqlite3"),
    },
    'estimatedb': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(MyDB_DIR,'estimate.sqlite3'),
    },
    'sifter_results_ready_db': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(MyDB_DIR,"sifter_results_cmp_ready_leaves_040315.sqlite3"),
    },
    'idmap_db': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(MyDB_DIR,"idmap_db.sqlite3"),
    },
    'pfamdb': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(MyDB_DIR,"pfam_db.sqlite3"),
    },	
}
DATABASE_ROUTERS = [
    'term_db.routers.term_db_router',
    'weight_db.routers.weight_db_router',
    'sifter_results_db.routers.sifter_results_db_router',
    'taxid_db.routers.taxid_db_router',
    'estimatedb.routers.EstimateDbRouter',
    'sifter_results_ready_db.routers.sifter_results_ready_db_router',
    'idmap_db.routers.idmap_db_router',
    'pfamdb.routers.pfamdb_router'    
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
    
SERVER_EMAIL= 'sifter@compbio.berkeley.edu'    
    
#SEND_BROKEN_LINK_EMAILS=True    
ADMINS = (
    ('SIFTER', 'sifter@compbio.berkeley.edu'),
    ('Mohammad Sahraeian', 'sahraeian.m@gmail.com'),
)
