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
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),os.pardir))
#BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
try:
  base = qraat.csv.csv(os.environ['RMG_WEB_SERVER_UI_KEYS']).get(name='django_base')
  web_writer= qraat.csv.csv(os.environ['RMG_WEB_SERVER_DB_AUTH']).get(view='web_writer')
  web_reader = qraat.csv.csv(os.environ['RMG_WEB_SERVER_DB_AUTH']).get(view='web_reader')
  django_admin = qraat.csv.csv(os.environ['RMG_WEB_SERVER_DB_AUTH']).get(view='admin')

except KeyError:
  raise qraat.error.QraatError("undefined environment variables. Try `source rmg_env`")
  
except IOError, e:
  raise qraat.error.QraatError("missing DB credential file '%s'" % e.filename)

SECRET_KEY = base.key

# SECURITY WARNING: don't run with debug turned on in production!
# NOTE For testing purposes, this must be set to True in order 
# to run 'python manage.py runserver'. 
DEBUG = TEMPLATE_DEBUG = True 

TEMPLATE_DIRS = [os.path.join(BASE_DIR, 'templates')]

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = (
    'map',
    'account',
    'graph',
    'project',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
#    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'gaat.urls'

WSGI_APPLICATION = 'gaat.wsgi.application'

SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'qraat',
        'USER': django_admin.user,
	'PASSWORD': django_admin.password, 
        },
	'writer': {
		'ENGINE': 'django.db.backends.mysql',
		'NAME': 'qraat',
		'USER': web_writer.user,
		'PASSWORD': web_writer.password,
	},
	'reader': {
		'ENGINE': 'django.db.backends.mysql',
		'NAME': 'qraat',
		'USER': web_reader.user,
		'PASSWORD': web_reader.password,
	},
}

DATABASE_ROUTERS = [ 'project.router.DatabaseAppsRouter',]
DATABASE_APPS_MAPPING = {'map': 'reader', 'project': 'writer', 'graph': 'reader' }	

#LOGGING = {
#    'disable_existing_loggers': False,
#    'version': 1,
#    'handlers': {
#        'console': {
#            # logging handler that outputs log messages to terminal
#            'class': 'logging.StreamHandler',
#            'level': 'DEBUG', # message level to be written to console
#        },
#    },
#    'loggers': {
#        '': {
#            # this sets root level logger to log debug and higher level
#            # logs to console. All other loggers inherit settings from
#            # root level logger.
#            'handlers': ['console'],
#            'level': 'DEBUG',
#            'propagate': False, # this tells logger to send logging message
#                                # to its parent (will send if set to True)
#        },
#        'django.db': {
#            # django also has database level logging
#        },
#    },
#}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/Los_Angeles'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = "/var/www/qraat_site/static/"
STATICFILES_DIRS = ( os.path.join(BASE_DIR, "static") ,)
