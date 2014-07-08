"""
Django settings for qraatview project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '8%a3r^oveg!z)o^%-87*+kns2c$qma^(=g@%_7ua19q9ug&=5+'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
	'hello',
	'qraat_auth',
	'qraat_site',
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
AUTHENTICATION_BACKENDS = ('django.contrib.auth.backends.ModelBackend', 
			'qraat_auth.models.QraatUserBackend',)

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
	'auth': {
		'ENGINE': 'django.db.backends.mysql',
		'NAME': 'auth',
		'USER': 'authuser',
		'PASSWORD': 'authpassword',
	},
}

DATABASE_ROUTERS = [ 'qraat_site.router.DatabaseAppsRouter',]
DATABASE_APPS_MAPPING = {'qraat_site':'auth',
			 'qraat_auth': 'auth', 'hello': 'qraat',
			}	

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