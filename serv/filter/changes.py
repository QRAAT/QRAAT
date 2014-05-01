import qraat

VALID_MODES = ('file', 'db', 'fileinc')
QUERY_TEMPLATE = 'insert into estscore (estid, absscore, relscore) values (%s, %s, %s);\n'

#ADD_EVERY = 100
ADD_EVERY = 0

class ChangeHandler:
	def __init__(self, obj, mode):
		self.obj = obj
		self.mode = mode
		assert self.mode in VALID_MODES
		if self.mode == 'db':
			self.buffer = []
			db_con = qraat.util.get_db('writer')
			self.obj = db_con
		elif self.mode == 'fileinc':
			self.obj = obj # A filename is this case
			self.current_index = 1
			self.set_file_handle()
		print 'Object of type {} being handled in mode {}'.format(self.obj.__class__, self.mode)

	def set_file_handle(self):
		assert self.mode == 'fileinc'
		
		filename = '{}{}'.format(self.obj, self.current_index)
		self.current_file_handle = open(filename, 'w')
		
	def increment(self):
		if self.mode != 'fileinc':
			print 'WARNING: Increment noop'
			return
		else:
			self.current_file_handle.close()
			self.current_index += 1
			self.set_file_handle()

	def close(self):
		getattr(self, 'close_' + self.mode)()
	
	def add_score(self, estid, absscore, relscore):
		getattr(self, 'add_score_' + self.mode)(estid, absscore, relscore)

	def flush(self):
		getattr(self, 'flush_' + self.mode)()
		
	# File operations

	def close_file(self):
		self.obj.close()

	def add_score_file(self, estid, absscore, relscore):
		s = QUERY_TEMPLATE % (estid, absscore, relscore)
		self.obj.write(s)

	def flush_file(self):
		self.obj.flush()

	# Fileinc operations

	def close_fileinc(self):
		self.current_file_handle.close()

	def add_score_fileinc(self, estid, absscore, relscore):
		s = QUERY_TEMPLATE % (estid, absscore, relscore)
		self.current_file_handle.write(s)

	def flush_score_fileinc(self):
		self.current_file_handle.flush()

	# Database operations - Not sure if these are correct calls, will have to
	# verify tomorrow.

	# NOTE: The flush() functionality is primarily in place for the database so
	# updates can be cached in the ChangeHandler itself and batch applied for
	# efficiency.

	def close_db(self):
		self.obj.close()

	def add_score_db(self, estid, absscore, relscore):
		if ADD_EVERY == 0:
			# Apply update immediately
			cursor = self.obj.cursor()
			cursor.execute(QUERY_TEMPLATE, (estid, absscore, relscore))
		else:
			self.buffer.append((estid, absscore, relscore))
			if len(self.buffer) >= ADD_EVERY:
				self.flush_db()

	def flush_db(self):
		if len(self.buffer) == 0:
			print 'Unnecessary flush call on DB'
		else:
			print 'Flushing {} scores to DB'.format(len(self.buffer))
			cursor = self.obj.cursor()
			cursor.executemany(self.buffer)
			self.buffer.clear()
