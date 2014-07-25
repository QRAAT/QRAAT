class QraatRouter(object):
	"""
	A router to control database operations on models in the qraat application
	"""
	def __init__(self):
		self.QRAAT_LABEL = "qraat_ui"
		self.QRAAT_DB = "qraat"
	
	def db_for_read(self, model, **hints):
		if model._meta.app_label == self.QRAAT_LABEL:
			return self.QRAAT_DB
		return None

	def db_for_write(self, model, **hints):
		if model._meta.app_label == self.QRAAT_LABEL:
			return self.QRAAT_DB #try to chang to writer
		return None

	def allow_relation(self, obj1, obj2, **hints):
		if obj1._meta.app_label == self.QRAAT_LABEL or \
		   obj2._meta.app_label == self.QRAAT_LABEL:
			return True
		return None

	def allow_syncdb(self, db, model):
		if db == self.QRAAT_DB:
			return model._meta.app_label == self.QRAAT_LABEL
		elif model._meta.app_label == self.QRAAT_LABEL:
			return False
		return None
