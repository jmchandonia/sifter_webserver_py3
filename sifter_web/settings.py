"""
Django settings for sifter_web project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import importlib.util
import glob
import os
import re

if importlib.util.find_spec('djcelery') is not None:
    import djcelery
    djcelery.setup_loader()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


def get_secret_key(default='development-only-insecure-secret-key'):
    return os.environ.get('DJANGO_SECRET_KEY', default)


def get_env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in ('1', 'true', 'yes', 'on')


def get_env_list(name, default):
    value = os.environ.get(name)
    if not value:
        return default
    return [item.strip() for item in value.split(',') if item.strip()]


def get_env_int(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    return int(value)


def get_data_dir(default_subdir):
    data_dir = os.environ.get('SIFTER_DATA_DIR')
    if data_dir:
        return os.path.join(data_dir, default_subdir)
    return os.path.join(BASE_DIR, 'sifter_web', default_subdir)


def get_db_dir():
    explicit = os.environ.get('SIFTER_DB_DIR')
    if explicit:
        return explicit
    local = os.path.join(BASE_DIR, 'my_dbs')
    if os.path.isdir(local):
        return local
    return os.path.join(os.path.dirname(BASE_DIR), 'my_dbs')


def resolve_db_file(db_dir, preferred_name, pattern=None):
    preferred_path = os.path.join(db_dir, preferred_name)
    if os.path.exists(preferred_path):
        return preferred_path
    if pattern:
        matches = sorted(glob.glob(os.path.join(db_dir, pattern)))
        if matches:
            return matches[-1]
    return preferred_path

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TRACK_STARTED=True
CELERY_IMPORTS = ("sifter_web.tasks",)
CELERY_TASK_ALWAYS_EAGER = get_env_bool('CELERY_TASK_ALWAYS_EAGER', False)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_secret_key()

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = get_env_bool('DJANGO_DEBUG', False)
CELERY_TASK_EAGER_PROPAGATES = get_env_bool('CELERY_TASK_EAGER_PROPAGATES', DEBUG)

TEMPLATE_DEBUG = DEBUG

ALLOWED_HOSTS = get_env_list('ALLOWED_HOSTS', ["sifter.berkeley.edu"])


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
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
]

if importlib.util.find_spec('djcelery') is not None:
    INSTALLED_APPS.append('djcelery')

if importlib.util.find_spec('chartit') is not None:
    INSTALLED_APPS.append('chartit')

MIDDLEWARE_CLASSES = (
#	'django.middleware.common.BrokenLinkEmailsMiddleware',    
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

MIDDLEWARE = MIDDLEWARE_CLASSES

ROOT_URLCONF = 'sifter_web.urls'

WSGI_APPLICATION = 'sifter_web.wsgi.application'

MyDB_DIR = get_db_dir()
SIFTER_INPUT_DIR = os.environ.get('SIFTER_INPUT_DIR', get_data_dir('input'))
SIFTER_OUTPUT_DIR = os.environ.get('SIFTER_OUTPUT_DIR', get_data_dir('output'))
SIFTER_FILE_OWNER = os.environ.get('SIFTER_FILE_OWNER')
SIFTER_FILE_GROUP = os.environ.get('SIFTER_FILE_GROUP')
SIFTER_ENABLE_SOLR_SEARCH = get_env_bool('SIFTER_ENABLE_SOLR_SEARCH', True)
SIFTER_SOLR_TIMEOUT = get_env_int('SIFTER_SOLR_TIMEOUT', 1)
SIFTER_BLAST_EXPECT = float(os.environ.get('SIFTER_BLAST_EXPECT', '1e-2'))
SIFTER_BLAST_HITLIST_SIZE = get_env_int('SIFTER_BLAST_HITLIST_SIZE', 100)
SIFTER_BLAST_MAX_RETRIES = get_env_int('SIFTER_BLAST_MAX_RETRIES', 600)
SIFTER_BLAST_RETRY_SLEEP = get_env_int('SIFTER_BLAST_RETRY_SLEEP', 60)

# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR,"db.sqlite3"),
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
        'NAME': resolve_db_file(MyDB_DIR, "sifter_results_cmp_050715.sqlite3", "sifter_results_cmp_[0-9]*.sqlite3"),
    },
    'term_db': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(MyDB_DIR,"term_db.sqlite3"),
    },
    'taxid_db': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': resolve_db_file(MyDB_DIR, "taxid_db_wP.sqlite3", "taxid_db*.sqlite3"),
    },
    'estimatedb': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(MyDB_DIR,'estimate.sqlite3'),
    },
    'sifter_results_ready_db': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': resolve_db_file(MyDB_DIR, "sifter_results_cmp_ready_leaves_050715.sqlite3", "sifter_results_cmp_ready*.sqlite3"),
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
        'URL': os.environ.get('SIFTER_SOLR_URL', 'http://127.0.0.1:8983/solr'),
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
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': list(TEMPLATE_DIRS),
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'django://')


if DEBUG:
    MEDIA_URL='/media/'
    STATIC_ROOT = os.environ.get('STATIC_ROOT', os.path.join(BASE_DIR,"sifter_web","static","static-only"))
    MEDIA_ROOT = os.environ.get('MEDIA_ROOT', get_data_dir('media'))
    STATICFILES_DIRS = (os.environ.get('STATICFILES_DIR', os.path.join(BASE_DIR,"sifter_web","static","static")),)
else:
    MEDIA_URL = os.environ.get('MEDIA_URL', '/media/')
    STATIC_ROOT = os.environ.get('STATIC_ROOT', os.path.join(BASE_DIR,"staticfiles"))
    MEDIA_ROOT = os.environ.get('MEDIA_ROOT', get_data_dir('media'))
    
    
SERVER_EMAIL= 'sifter@compbio.berkeley.edu'
    
#SEND_BROKEN_LINK_EMAILS=True    
ADMINS = (
    ('SIFTER', 'sifter@compbio.berkeley.edu'),
    ('Mohammad Sahraeian', 'sahraeian.m@gmail.com'),
)
