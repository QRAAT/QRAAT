Random notes on Django

To test code, run 

$ python manage.py runserver 8000

Then load 'localhost:8000' in your web browser. Note that this is not a 
production server: we'll need to figure out the best way to integrate the
code on to the live QRAAT server. 

We're using mysql for Django's stuff. How should we connect to the QRAAT 
database? It's not clear to me whether there is a more sophisticated way
than using our home-brewed API. 



Useful tutorials

  - Set up/test Django framework: https://docs.djangoproject.com/en/1.6/intro/tutorial01/
  - Apache/mod_wsgi setup: https://docs.djangoproject.com/en/1.2/howto/deployment/modwsgi/

