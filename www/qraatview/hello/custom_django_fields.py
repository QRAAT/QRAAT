from django.db.models import fields
from south.modelsinspector import add_introspection_rules

class BigAutoField(fields.AutoField):
	def db_type(self, connection):
		if 'mysql' in connection.__class__.__module__:
			return 'bigint AUTO_INCREMENT'
		return super(BigAutoField, self).db_type(connection)

add_introspection_rules([], ["^MYAPP\.fields\.BigAutoField"])
