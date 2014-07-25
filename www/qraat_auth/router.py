class AuthRouter(object):
	"""
	A router to control database operations on models in the auth application
	"""
	def __init__(self):
		self.APP_LABEL = "qraat_auth"
		self.DB_NAME = "auth"
	
	def db_for_read(self, model, **hints):
		if model._meta.app_label == self.APP_LABEL:
			return self.DB_NAME
		return None

	def db_for_write(self, model, **hints):
		if model._meta.app_label == self.APP_LABEL:
			return self.DB_NAME #try to change to writer
		return None

	def allow_relation(self, obj1, obj2, **hints):
		if obj1._meta.app_label == self.APP_LABEL or \
		   obj2._meta.app_label == self.APP_LABEL:
			return True
		return None

	def allow_syncdb(self, db, model):
		if db == self.DB_NAME:
			return model._meta.app_label == self.APP_LABEL
		elif model._meta.app_label == self.APP_LABEL:
			return False
		return None
