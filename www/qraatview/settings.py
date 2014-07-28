"""
Django settings for qraatview project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

import os
import qraat

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
try:
  base = qraat.csv.csv(os.environ['RMG_SERVER_UI_KEYS']).get(name='django_base')

except KeyError:
  raise qraat.error.QraatError("undefined environment variables. Try `source rmg_env`")
  
except IOError, e:
  raise qraat.error.QraatError("missing DB credential file '%s'" % e.filename)

SECRET_KEY = base.key

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True
TEMPLATE_DIRS = [os.path.join(BASE_DIR, 'templates')]


ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'qraat_ui',
    'qraat_auth',
    'qraatview'
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
#    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'qraatview.urls'

WSGI_APPLICATION = 'qraatview.wsgi.application'
#AUTH_USER_MODEL = 'qraat_auth.QraatUser'

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'django',
        'USER': 'root',
	'PASSWORD': 'woodland', 
        },
	'qraat': {
		'ENGINE': 'django.db.backends.mysql',
		'NAME': 'qraat',
		'USER': 'root',
		'PASSWORD': 'woodland',
	},
}

DATABASE_ROUTERS = [ 'qraatview.router.DatabaseAppsRouter',]
DATABASE_APPS_MAPPING = {'qraat_ui': 'qraat', 'qraatview': 'qraat' }	

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = "/var/www/qraat_site/static/"