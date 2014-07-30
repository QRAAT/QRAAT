# signal_filter.py -- Score EST records based on three criteria: 
# 
#  parametric: If signal features of an individual pulse are poor -- 
#              i.e. band3 or band10 values are higher than recommended
#              for that transmitter -- then they are given an absolute 
#              score of -2 and aren't considered in the next filters. 
# 
#  density: If the density of est records over a small window is too 
#           high, the est's in the window are given an absolute score of
#           -1 and the whole window is thrown out (not considred in the 
#           next filter). 
# 
#  time: Calculate the expected interval between pulses and score EST's 
#        based on the number of subsequent pulses in the window match up
#        with it being a true pulse. 
# 
# Copyright (C) 2014 Sean Riddle
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from collections import defaultdict
import collections
import decimal
import itertools
from numpy import histogram
import numpy
import random
import sys
import bisect
import math
import traceback

import MySQLdb as mdb
import qraat 

# Distance to look for neighbors while scoring. If interval is calculated for a
# point less than this, the time score cannot be calculated, so this is given a
# score of -3. TODO what is this? 
CONFIG_ERROR_ALLOWANCE = 0.2

# How long a period the interval should be calculated over (seconds) 
CONFIG_INTERVAL_WINDOW_SIZE = float(3 * 60) 

# Search this many interval distances in both directions of a point for corroborating neighbors.
# Over the large time window, we calculate the expected pulse interval. (Compute pairwise time
# differentials, the most frequent is taken to be the expected pulse interval.) Thus, the 
# optimal number of pulses (hence the highest absscore) is CONFIG_DELTA_AWAY * 2 
# (see _rel_score()). 
CONFIG_DELTA_AWAY = 3

# False if actually apply changes to database, True if just write script to file (update.sql in cwd)
# Warning: Not everything goes through ChangeHandler anymore - this can give
# you an inconsistent DB in addition to an inconsistent "SQL file."
CONFIG_JUST_STAGE_CHANGES = False

# Minimum interval percentage difference which must occur from old value to
# trigger superceding of the interval with the new ones and re-scoring of
# slice.
CONFIG_INTERVAL_PERCENT_DIFFERENCE_THRESHOLD = 0.25

# Minimum number of points before intervals are calculated. If less than this 
# number is found, items are given a score of -1.
CONFIG_MINIMUM_POINT_COUNT = 20


def debug_print(string): 
  if True: 
    print >>sys.stderr, "signal_filter: debug:", string

class Registry:

	def __init__(self, args):
		self.points = []
		self.arguments = args
		self.txlist = None

	def __len__(self):
		return len(self.points)

	def get_ids(self):
		return [x['ID'] for x in self.points]

	def register_point(self, point):
		self.points.append(point)

	def get_all_ids(self):
		return [x['ID'] for x in self.points]

	def get_fields(self, *fields, **kw):
		fields_iter = []
		if 'with_prefixed_id' in kw and kw['with_prefixed_id']:
			fields_iter.append('ID')
		fields_iter.extend(fields)
		new_tuples = []
		for point in self.points:
			new_tuple = []
			for field in fields_iter:
				new_tuple.append(point[field])
			new_tuples.append(tuple(new_tuple))
		return new_tuples


	def read_txlist_thresholds(self):
  
                # TODO global data doesn't need to be computedd 
                # for each interval.

		if self.txlist is None:
                  tx_dict = {}
		  db_con = qraat.util.get_db('reader')
		  cur = db_con.cursor()

                  # Transmitters in active deployments
                  cur.execute('''SELECT deployment.ID, txID, frequency 
                                   FROM deployment
                                   JOIN tx ON tx.ID = txID
                                   JOIN tx_make ON tx_make.ID = tx.tx_makeID
                                  WHERE demod_type = 'pulse' ''')

                  for (dep_id, tx_id, frequency) in cur.fetchall():
                    tx_dict[tx_id] = { 'frequency' : frequency, 'dep_id' : dep_id }

                  # Transmitter parameters
                  cur.execute('''SELECT txID, name, value 
                                   FROM tx_parameters
                                  WHERE txID IN (%s)''' % ', '.join(map(lambda(x) : str(x), 
                                                    tx_dict.keys())))
                                
                  for (tx_id, name, value) in cur.fetchall():
                    tx_dict[tx_id][name] = value
                  
                  self.txlist = {}
                  
                  # Convert band3 and band10 to intergers, store self.txlist dictionary
                  # Set arbitrarily high values for transmitters with no band filter 
                  # paramaters. 
                  for (_, params) in tx_dict.iteritems():
                    d = {}
                    if params['band3'] == '': 
                      d['band3'] = sys.maxint
                    else: d['band3'] = int(params['band3'])
                    if params['band10'] == '': 
                      d['band10'] = sys.maxint
                    else: d['band10'] = int(params['band10'])
                    self.txlist[params['dep_id']] = d

			
			

	def get_matching_points(self, points, **kw):

		self.read_txlist_thresholds()
		#print 'Getting matching points out of {}'.format(len(points))
		min_time, max_time = None, None
		#counts = defaultdict(int)
		counts = defaultdict(list)

		#filter_freq = filter_range('frequency', kw['frequency'], 2000)



		xs = [x['timestamp'] for x in points]
		histo = histogram(xs, bins=(24 * 60))

		for t in xs:
			if min_time is None or t < min_time:
				min_time = t
			if max_time is None or t > max_time:
				max_time = t

		#print 'Total time range: {} - {}'.format(min_time, max_time)

		# bin_size = histo[1][1] - histo[1][0]
		# print 'Calculated histogram'

		# print '*****************************************'
		# print 'Reporting on histogram!'
		# print 'histo0:', histo[0]
		# print 'histo1:', histo[1]

		inds = [x for x in range(len(histo[0])) if histo[0][x] > 500]
		# print 'Got {} high value buckets!'.format(len(inds))
		# print '*****************************************'

		bad_points = set()

		enable_prefiltering = True
		# if enable_prefiltering:
		# 	print 'Performing prefiltering'
		# else:
		# 	print 'WARNING: Prefiltering disabled. Are you sure about this?'

		filter_overall_freq = filter_hist(histo)

		highlighted = get_matching_points_op(points, filter_overall_freq)
		if enable_prefiltering and highlighted is not None:
			#print '{} points filtered out by frequency'.format(len(highlighted))
			bad_points.update([x['ID'] for x in highlighted])
			good_points = [x for x in points if x['ID'] not in bad_points]
			#print 'That leaves {} good points'.format(len(good_points))
			for h in highlighted:
				counts[h['ID']].append('frequency')
		elif enable_prefiltering:
			pass #print 'Would have prefiltered by rate, but no violations'

		filter_band3 = filter_values_over('band3', self.txlist)

		highlighted = get_matching_points_op(points, filter_band3)
		if enable_prefiltering and highlighted is not None:
			#print '{} points filtered out by band3'.format(len(highlighted))
			bad_points.update([x['ID'] for x in highlighted])
			good_points = [x for x in points if x['ID'] not in bad_points]
			#print 'That leaves {} good points'.format(len(good_points))
			for h in highlighted:
				counts[h['ID']].append('band3')
		elif enable_prefiltering:
			pass #print 'Would have prefiltered by band3, but no violations'

		filter_band10 = filter_values_over('band10', self.txlist)

		highlighted = get_matching_points_op(points, filter_band10)
		if enable_prefiltering and highlighted is not None:
			#print '{} points filtered out by band10'.format(len(highlighted))
			bad_points.update([x['ID'] for x in highlighted])
			good_points = [x for x in points if x['ID'] not in bad_points]
			#print 'That leaves {} good points'.format(len(good_points))
			for h in highlighted:
				counts[h['ID']].append('band10')
		elif enable_prefiltering:
			pass #print 'Would have prefiltered by band10, but no violations'

		return counts




	# now I just return a good and a bad list of 3-tuples, so points stay
	# linked to IDs. For more info, see freq.py.
	#((good_xs, good_ys), (bad_xs, bad_ys), good_ids, bad_ids) = registry.screen_bad(item_to_plot, points)
	def screen_bad(self, points, **kw):
		#print 'Categorizing {} points'.format(len(points))
		#print 'screen_bad() start'
		ids = [x['ID'] for x in points]
		bad_point_map, good_points = self.get_bad_points(ids, **kw)
		#print 'done getting bad points ({}) and good points ({})'.format(len(bad_point_map), len(good_points))

		#print 'Reporting on overlap'
		#id_set = set(ids)
		#bad_set = set(bad_points.keys())
		#print 'Total:', len(id_set)
		#print 'Bad set:', len(bad_set)
		#print 'Bad-Total:', len(bad_set.difference(id_set))
		#print 'Total-Bad:', len(id_set.difference(bad_set))
		#print '-----&&&&-----'

		#print 'There are {} total IDs, {} bad IDs, and {} good IDs.'.format(len(set(ids)), len(set(all_bad_points)), len(set(good_point_ids)))
		#print 'I think there are {} good points, like: {}'.format(len(good_point_ids), good_point_ids[:10])
		bad_ids = bad_point_map.keys()
		#print 'bad ids ({}): {}'.format(len(bad_ids), bad_ids[:10])
		if len(bad_ids) > 0: print 'type is:', bad_ids[0].__class__
		#good_ids = [x[0] for x in points if x[0] not in bad_ids]

		good_point_data, bad_point_data = [], []
		bad_points = []
		for point in points:
			if point['ID'] in bad_ids:
				bad_points.append(point)

		return good_points, bad_points

		#if 'with_id' in kw.keys() and kw['with_id']:
			#return good_point_ids, z
		#else:
			#return z

	def get_matlab_style_points_for_ids(self, ids, x_field, y_field, verbose=False):
		xs, ys = [], []
		if verbose: print 'Iterating through {} points'.format(len(self.points))
		if verbose: print 'Looking for {} IDs, something like: {}'.format(len(ids), ids[:10])
		for point in self.points:
			if point['ID'] in ids:
				xs.append(point[x_field])
				ys.append(point[y_field])
		return xs, ys




	def get_bad_points(self, ids, **kw):
		global current_count
		#if current_count == 1:
			#assert False
		#else:
			#current_count += 1
		points = [x for x in self.points if x['ID'] in ids]
		# print 'Got {} points that are about to be categorized'.format(len(points))
		# print 'get_bad_points() -> get_matching_points()'

		good_points = []

		counts = self.get_matching_points(points, **kw)

		#with open('/home/qraat/counts.txt', 'a') as f:
		#	f.write('----------------\n')
		#	f.write('{}\n'.format(counts))
		#	f.write('----------------\n')

		for point in points:
			if point['ID'] not in counts.keys():
				good_points.append(point)
		#print '|counts| = {}'.format(len(counts))
		for (k, v) in counts.items()[:10]:
			print 'count {} -> {}'.format(k, v)
		return counts, good_points


def get_matching_points_op(points, function):
	xs = []
	ys = []
	highlighted_points = []
	for point in points:
		t = highlight_if(point, points, function)
		if t is not None:
			highlighted_points.append(t)
	if len(highlighted_points) > 0:
		return highlighted_points
	else:
		#print 'returning none!'
		return None
			#xs.append(t[0])
			#ys.append(t[1])
	#if len(xs) > 0:
		#print 'highlighting required'
		#return xs, ys
	#else:
		#return None
		#matplotlib.pyplot.scatter(xs, ys, c=color)

def highlight_if(point, points, filter_func):
	if filter_func(point, points):
		# filter_func returns true if it SHOULD be filtered
		return point
	else:
		return None

def already_calculated_interval(siteid, txid, tstamp):
	# Look for records (siteid, txid, tstamp', duration') st. tstamp' <= tstamp <= tstamp' + duration'
	pass

cached_stds = {}
cached_means = {}

def filter_stddev(field_name, std_dev_num):
	def filter_func(point, points):
		#global cached_stds, cached_means

		if field_name not in cached_stds.keys():
			data_points = [x[field_name] for x in points]
			cached_stds[field_name] = numpy.std(data_points)
			cached_means[field_name] = numpy.mean(data_points)

		upper_bound = cached_means[field_name] + (std_dev_num * cached_stds[field_name])
		lower_bound = cached_means[field_name] - (std_dev_num * cached_means[field_name])

		if point[field_name] < lower_bound or point[field_name] > upper_bound:
			return True
		else:
			return False
	return filter_func


def filter_range(field_name, center, delta):
	def filter_func(point, points):
		upper_bound = center + delta
		lower_bound = center - delta

		#print 'upper:', upper_bound
		#print 'lower:', lower_bound

		#print 'processing:', point[field_name], field_name
		if point[field_name] < lower_bound or point[field_name] > upper_bound:
			return True
		else:
			#print 'something in the middle!'
			return False
	return filter_func

def filter_values_over(field_name, threshold_dict):
	def filter_func(point, points):
		threshold = threshold_dict[point['deploymentID']][field_name]
		#print 'Got filter threshold of {} for TXID {} (fieldname={})'.format(threshold, point['txid'], field_name)
		if threshold is None:
			return False
		else:
			return point[field_name] > threshold
	return filter_func

FREQUENCY_THRESHOLD = 400

def filter_hist(histo):
	big_inds = [(histo[1][x], histo[1][x + 1]) for x in range(len(histo[0])) if histo[0][x] > FREQUENCY_THRESHOLD]
	def filter_func(point, points):
		for (start, end) in big_inds:
			if point['timestamp'] >= start and point['timestamp'] < end:
				return True
		return False
	return filter_func

current_count = 0


VALID_MODES = ('file', 'db', 'fileinc')
INSERT_TEMPLATE = 'insert into estscore (estid, absscore, relscore) values (%s, %s, %s);\n'
UPDATE_TEMPLATE = 'update estscore set absscore = %s, relscore = %s where estid = %s;\n'

#ADD_EVERY = 100
ADD_EVERY = 0

class ChangeHandler:
	def __init__(self, obj, mode):
		self.obj = obj
		self.mode = mode
		assert self.mode in VALID_MODES
		if self.mode == 'db':
			self.buffer = []
			self.obj = qraat.util.get_db('writer')
		elif self.mode == 'fileinc':
			self.obj = obj # A filename is this case
			self.current_index = 1
			self.set_file_handle()
		#print 'Object of type {} being handled in mode {}'.format(self.obj.__class__, self.mode)

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

	def db_execute_many(self, template, args):
		matches = [x for x in args if x[0] == 214183264]
		if len(matches) > 0:
			assert len(matches) == 1
			
			f = open('/home/sean/scoreinfo.txt', 'a')
			for match in matches:
				f.write('many-ex abs={}, rel={}\n'.format(match[1], match[2]))
				print match
			assert False
				# if match[1] == -2:
				# 	print 'Determined parametric badness'
				# 	f.write('<-- this one is parametrically bad - many execute statement\n')
			# try:
			# 	assert False
			# except AssertionError:
			# 	# tr = sys.exc_info()[2]
			# 	traceback.print_exc(f)
			# traceback.print_tb(tr, limit=None, file=f)
			f.write('------------------------\n')
			f.close()
		cursor = self.obj.cursor()
		cursor.executemany(template, args)

	def add_sql(self, sql_text, sql_args):
		return getattr(self, 'add_sql_' + self.mode)(sql_text, sql_args)

# Have 5s: [206779849L, 206779850L, 206779851L]
	
	def add_score(self, estid, absscore, relscore):
		# if estid in (206779849, 206779850, 206779851):
		# 	_log(estid, absscore, relscore)
		return getattr(self, 'add_score_' + self.mode)(estid, absscore, relscore)

	def flush(self):
		return getattr(self, 'flush_' + self.mode)()
		
	# File operations

	def close_file(self):
		self.obj.close()

	def add_score_file(self, estid, absscore, relscore):
		s = INSERT_TEMPLATE % (estid, absscore, relscore)
		self.obj.write(s)

	def add_sql_file(self, sql_text, sql_args):
		self.obj.write((sql_text % sql_args) + '\n')
		return -1

	def flush_file(self):
		self.obj.flush()

	# Fileinc operations

	def close_fileinc(self):
		self.current_file_handle.close()

	def add_score_fileinc(self, estid, absscore, relscore):
		s = INSERT_TEMPLATE % (estid, absscore, relscore)
		self.current_file_handle.write(s)

	def add_sql_fileinc(self, sql_text, sql_args):
		self.current_file_handle.write((sql_text % sql_args) + '\n')

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
		#print 'Adding score!'
		if ADD_EVERY == 0:
			# Apply update immediately
			cursor = self.obj.cursor()
			try:
				cursor.execute(INSERT_TEMPLATE, (estid, absscore, relscore))
                        except mdb.Error, e:
                                if e.args[0] != 1062: # Ignore duplicate entry warnings.  
                                  debug_print("time filter: warning: [%d] %s" % (e.args[0], e.args[1]))
                                #c = self.obj.cursor()
				#rows = c.execute('select absscore, relscore from estscore where estid = %s', (estid,))
				#with open('/home/qraat/duplicate.log', 'a') as f:
				#	f.write('Rows returned for ID={} while attempting to score as {}/{}: {}\n'.format(estid, absscore, relscore, rows))
				#	while True:
				#		t = c.fetchone()
				#		if t is None:
				#			break
				#		else:
				#			f.write('\t* {}\n'.format(t))
				#	f.write('Done with exception handling...\n')
                        except Exception:
                                debug_print("time filter: something went wrong in add_score_db().")
			return cursor
		else:
			self.buffer.append((estid, absscore, relscore))
			if len(self.buffer) >= ADD_EVERY:
				self.flush_db()

	def add_sql_db(self, sql_text, sql_args):
		cursor = self.obj.cursor()
		#print 'Running query:', sql_text % sql_args
		rows = cursor.execute(sql_text, sql_args)
		#print 'SQL statement returned:', rows
		return cursor

	def flush_db(self):
		if len(self.buffer) == 0:
			print 'Unnecessary flush call on DB'
		else:
			print 'Flushing {} scores to DB'.format(len(self.buffer))
			cursor = self.obj.cursor()
			cursor.executemany(self.buffer)
			self.buffer.clear()

class WindowIterator:
	#def __init__(self, points, window_size, min_ind=0, max_ind=len(points)):
	def __init__(self, points, window_size):
		self.points = points
		self.xs = [x[0] for x in self.points]
		self.ids = [x[1] for x in self.points]
		# TODO: Replace with a (probably) more efficient call to zip
		self.window_size = window_size
		self.windows = None
		self.init_windows()

	def get_property_for_point(self, point, prop, window_offset=0):
		match_ind, orig_match_ind, window = self.get_window_for_point(point, offset=window_offset)
		if window.attributes[prop] is None:
			pass #print 'For requested window offset {} it\'s messed up. Actual index = {}, original request = {}'.format(window_offset, match_ind, orig_match_ind)
		return window.attributes[prop]

	def report(self):
		#print 'There are a total of {} windows'.format(len(self.windows))
		for i, window in enumerate(self.windows):
			if 'interval' in window.attributes and window.attributes['interval'] is None:
				pass #print 'Window {} interval malformed'.format(i)

	def get_window_count(self):
		if len(self.points) == 0:
			return 0
		((min_x, min_id), (max_x, max_id)) = self.points[0], self.points[-1]
		total_range = max_x - min_x

		interval_window_count = int(math.ceil(total_range / self.window_size))
		return interval_window_count

	def get_window_for_point(self, point, offset=0):
		found_window = False
		the_window = None
		# Return the Window object of index i+offset, where i is the index of
		# the window within which point falls.
		match_ind = None
		original_match_ind = None
		for i, window in enumerate(self):
			if point in window:
				original_match_ind = i
				# found the window
				assert not found_window
				found_window = True
				ind = i + offset
				if ind < 0:
					#print 'Correcting negative window index Original {} + offset {}'.format(i, offset)
					ind = 0
				match_ind = ind
				the_window = self.windows[ind]
		assert found_window
		return match_ind, original_match_ind, the_window

	def init_windows(self):
		if self.window_size is None:
			# One gigantic window.
			self.windows = [Window(self.points, 0, len(self.points))]
			return

		#print 'Called iter generator'
		inds = []
		#print 'The window count is:', self.get_window_count()
		#print 'A selection from xs:', self.xs[:50]
		if len(self.points) == 0:
			self.windows = []
		else:
			offset = self.points[0][0]
			for i in range(self.get_window_count()):
				#print 'iter'
				start = i * self.window_size + offset
				end = (i + 1) * self.window_size + offset
				start_ind = bisect.bisect_left(self.xs, start)
				#print 'Index nearest (left) to {} is {}'.format(start, start_ind)
				end_ind = bisect.bisect_right(self.xs, end)
				#print 'Index nearest (right) to {} is {}'.format(end, end_ind)
				inds.append((start_ind, end_ind))
			self.windows = [Window(self.points, x, y) for (x, y) in inds]
			#return iter([Window(self.points, x, y) for (x, y) in inds])


	def __iter__(self):
		return iter(self.windows)


class Window:
	def __init__(self, points, start_ind, end_ind):
		self.points = points
		self.start_ind = start_ind
		self.end_ind = end_ind
		self.attributes = {}

	def value(self):
		return self.points[self.start_ind:self.end_ind]

	# Returns True if property is replaced, False if new
	def attach_property(self, k, v):
		already_has_key = k in self.attributes.keys()
		self.attributes[k] = v
		#print 'adding attribute:', k
		return already_has_key

	def get_bounds(self):
		if self.end_ind < len(self.points):
			return (self.points[self.start_ind][0], self.points[self.end_ind][0])
		else:
			return (self.points[self.start_ind][0], None)

	def __contains__(self, v):
		# print 'Window starts {}, ends {}, length {}'.format(self.start_ind, self.end_ind, len(self.points))
		t_start = self.points[self.start_ind][0]
		t_end = self.points[self.end_ind - 1][0]

		# print 'performing contains {}...{}...{}'.format(v, t_start, t_end)
		return v >= t_start and v <= t_end

	def calculate_interval_from(self, txid='(unknown)', slice_id='(unknown)'):
		v = self.value()
		u = [x[0] for x in v]
		intervals = [(u[i+1] - u[i]) for i in range(len(u) - 1)]

		#print 'Processing {} intervals, bucket {}, for {} seconds'.format(len(v), k, range_division)
		#print 'Raw values:\n--------\n{}\n--------'.format(v)

		histo = numpy.histogram(intervals, bins=500, range=(0., 60.))

		# print 'Raw histo [0]:', histo[0]
		# print 'Raw histo [1]:', histo[1]

		argmax = numpy.argmax(histo[0])
		max_likelihood_interval = histo[1][argmax]

		#print 'The maximum likelihood interval is:', max_likelihood_interval

		if all(histo[0] == 0):
			#print 'Skipping interval detection for {}/{} because no data found'.format(txid, slice_id)
			return None

		assert any(histo[0] != 0)
		#print 'Performing interval detection for {}/{}'.format(txid, slice_id)
		candidates = sort_by(histo[0], histo[1])

		#print 'Candidates:', candidates

		#print 'Got {} candidates'.format(len(candidates))
		overtone_results = overtone_vote(candidates)

		most_likely_interval = None
		highest_count = -1
		for (interval, count) in overtone_results.items():
			if count > highest_count:
				highest_count = count
				most_likely_interval = interval

		return most_likely_interval


def sort_by(counts, range_starts):
	ret = []
	sorting_inds = counts.argsort()
	r_sorting_inds = list(reversed(sorting_inds))
	highest_two_vals = [None, None]
	for val in (counts[x] for x in r_sorting_inds):
		if highest_two_vals[0] is None:
			highest_two_vals[0] = val
		elif highest_two_vals[1] is None and highest_two_vals[0] != val:
			highest_two_vals[1] = val
		else:
			break
	if counts[r_sorting_inds[0]] == 1:
		# collect all of 1
		return [range_starts[x] for x in range(len(counts)) if counts[x] == 1]
	else:
		highest_two_vals = [x for x in highest_two_vals if x != 0]
		return [range_starts[x] for x in range(len(counts)) if counts[x] in highest_two_vals]

OVERTONE_LIMIT = 8
OVERTONE_ERROR = 0.1

# Tally the frequency of items but consider integral multiples of the value to
# count as support toward it.

def overtone_vote(candidates):
	votes = collections.defaultdict(int)
	candidates = list(sorted(candidates))

	for (i, candidate) in enumerate(candidates):
		#previous = candidates[:i]
		# Have to look at at least some elements ahead in the list to catch
		# items within the range for multiple 1
		previous = list(candidates)
		for multiple in range(1, OVERTONE_LIMIT + 1):
			# Includes 1 to detect things near to the current one
			looking_for = candidate / multiple
			looking_min, looking_max = looking_for - OVERTONE_ERROR, looking_for + OVERTONE_ERROR
			in_range = lambda x: x >= looking_min and x <= looking_max
			for item in previous:
				if in_range(item):
					votes[item] += 1

	return votes


def already_scored_filter(db_con, ids):

	ids_template = ', '.join(map(lambda x : '{}', ids))
	id_string = ids_template.format(*ids)

	already_scored = []
	cur = db_con.cursor()
	q = 'SELECT estid from estscore WHERE estid IN ({});'.format(id_string)
	rows = cur.execute(q)
	while True:
		r = cur.fetchone()
		if r is None: break
		already_scored.append(r[0])

	return already_scored
	




# Input: a sequence of ids, each of which is the value of the ID field of an
#	 entry in the est table. Nothing in here should be brand new...a slight
#        delay is applied in the higher-level program that makes sure there is 
#        context for scoring/interval calculation. Inputs are for one transmitter
#        and one receiver. 

# Output: none explicit - implicitly, score entries added for each id in ids

def score(ids):
	global reasoning
	reasoning = defaultdict(list)
	debug_print('Initial call to score {} ID(s)'.format(len(ids)))
	change_handler = init_change_handler()
	db_con = qraat.util.get_db('writer')

	parametrically_poor = set()

	if len(ids) == 0:
		print 'score() with zero length input...'
		return

	id_set = set(ids)

	#debug_print('Got ID set:' + str(id_set))

	# Get the data from the est table for these IDs and any other est records
	# associated with something within the time range defined by these IDs.
	# Context is the number of seconds around the min and max timestamp defined
	# by the ID set to include in the data returned. (Only affects things if
	# expanded=true).
	data = read_est_records(db_con, ids, expanded=True, context=300) # Returns a map estID -> est

	# I assume that all IDs being scored in a call to score() are from the same
	# txid and siteid. This restriction can probably be relaxed, but this will
	# make people explicitly aware when this is done.
	cur = db_con.cursor()
	ids_template = ', '.join(map(lambda x : '{}', ids))
	id_string = ids_template.format(*ids)
	#print 'Preparing to hit database again'
	q = 'SELECT DISTINCT siteID, deploymentID from est WHERE ID IN ({});'.format(id_string)
	rows = cur.execute(q)
	r = cur.fetchone()
	assert rows == 1
	siteid, txid = r
	#print 'Got siteid={}, txid={}'.format(siteid, txid)

	# Get all of these IDs that might have been scored already and store for
	# after-action report.
	already_scored = already_scored_filter(db_con, ids)
        debug_print('{} points were already scored'.format(len(already_scored)))

	# Returns a tuple (a, b, c) where a is the sequence of out-of-order IDs
	# (those occurring in a region with an already defined interval value), b
	# is the sequence of in-order IDs (those occurring in a region with no
	# defined interval value), and c is a map from ID to interval for those IDs
	# that can be associated with an already-computed interval.

	# Note: id_to_interval.keys() == out_of_order_ids.

	out_of_order_ids, in_order_ids, id_to_interval = partition_by_interval_calculation(db_con, ids, siteid, txid)
	debug_print('{} out of order IDs, {} in order IDs'.format(len(out_of_order_ids), len(in_order_ids)))

	# test_condition = set(id_to_interval.keys()) == set(out_of_order_ids)
	# if not test_condition:
	# 	import code
	# 	code.interact(local=locals())
	# assert test_condition

	#print 'Found {} out of order, {} in order'.format(len(out_of_order_ids), len(in_order_ids))

	# Returns the subset of keys of data which represent data which passes the
	# parametric filters (lowpass filters on band3 and band10 and a rate
	# limiting filter).
        all_that_passed_filter_ids = parametrically_filter(db_con, data)
	debug_print('data contains {} parametrically good points'.format(len(all_that_passed_filter_ids)))
	passed_filter_ids_set = set(all_that_passed_filter_ids)
	debug_print('discounting duplicates, we get ' + str( len(passed_filter_ids_set)))
        # TODO why would there be duplicates from parametrically_filte? 
        
	# The larger set of parametrically passing points is needed during scoring,
	# but the intersection of this and the original ID set defines those that
	# require time filtering.
	new_filtered_ids = id_set.intersection(passed_filter_ids_set)
	debug_print('we will time filter {} points'.format( len(new_filtered_ids)))

	# This is the set that requires time filtering, but the scores must be updated, not inserted
	updatable_ids = passed_filter_ids_set.difference(id_set)
	debug_print('{} items passed parametric filter'.format(len(new_filtered_ids)))
  
	
	# import code
	# code.interact(local=locals())

	# Insert scores for parametrically bad points...
	# The IDs in the ID set that did not pass the filter are given a sentinel
	# absolute value in absscore of -2 and a relscore that meets the
	# assumptions of that value (non-negative).
	for id in id_set.difference(all_that_passed_filter_ids):
		change_handler.add_score(id, -2, 0)
		reasoning[id].append('parametrically bad')
		parametrically_poor.add(id)

	# Buckets the IDs that occur as keys of data into different lists depending
	# on the timestamp in data for that ID. The returned structure is of the
	# form:

	# {(start_time, duration, siteid, txid):[IDs with associated timestamps t st. base <= t <= base + duration ]}

	# Note that IDs contained in a bucket must also match on siteid and txid.
	# This must be true at the moment, as all the IDs passed to score() deal
	# with a single (siteid, txid) pair.

	interval_chunked = time_chunk_ids(db_con, data, CONFIG_INTERVAL_WINDOW_SIZE)

	# Compute the chunked by interval IDs of interval_chunked, but restricted
	# to items in id_set. This is the set of intervals that might need to be
	# updated
	update_chunks = {}
	for (k, v) in interval_chunked.items():
		filtered = [x for x in v if x in id_set]
		if len(filtered) > 0:
			update_chunks[k] = filtered

	# Filters each bucket by restricting to unscored IDs.
	# unscored_ids_chunked = match_up_to_chunks(interval_chunked, all_to_score)

	# all_to_score = new_filtered_ids + updatable_ids
	# Parametric passed:
	parametrically_good_chunked = match_up_to_chunks(interval_chunked, all_that_passed_filter_ids)
	updatable_chunked = match_up_to_chunks(interval_chunked, updatable_ids)

	# Creates a mapping from interval keys to intervals from the mapping from
	# individual IDs to intervals. Ensures that all IDs associated with a given
	# interval key have the same interval.
	
        # NOTE Got here
        interval_map = get_interval_map(out_of_order_ids, interval_chunked, id_to_interval)

	key_neighborhood = compute_interval_neighborhood(interval_chunked.keys())


	# Figure out scores that might need updating. Look through
	# all_that_passed_filter_ids for those that are near something in id. These
	# will need to be rescored, with the scores being updated.
	# find_near(all_that_passed_filter_ids, id_set, 5)


	# Calculate brand new intervals for those which need it
	# Normally would have to go to the trouble of ensuring context is imported.
	# Still might. At least the information is available. It has been
	# parametrically filtered already.

	for k in interval_chunked:
                #debug_print('------ Time filter -------------------------------')
		all_chunk_ids = interval_chunked[k]

		# For each chunk's key, throw in the data for that and surrounding
		# chunks. Used to make sure the 'edge' of the window is caught.
		all_chunk_neighborhood = []
		for neighbor_key in key_neighborhood[k]:
			all_chunk_neighborhood.extend(parametrically_good_chunked[neighbor_key])
		

		# stuff to score:
		for_scoring = parametrically_good_chunked[k]
		updatables = updatable_chunked[k]

		if k not in interval_map:
			# This chunk has no interval computed yet, so compute one
			#print 'No interval for {} yet.'.format(k)
			interval = calculate_interval(db_con, interval_chunked[k])
			if interval < CONFIG_ERROR_ALLOWANCE:
				debug_print('time filter: Interval too low! Double-counting of the point in question will occur (i.e., the point will be considered its own neighbor)')
				# Give these a score of -3
				for id in parametrically_good_chunked[k]:
					reasoning[id].append('low interval')
					change_handler.add_score(id, -3, 0)
				continue

			if len(interval_chunked[k]) < CONFIG_MINIMUM_POINT_COUNT:
				# Score of -1
				for id in parametrically_good_chunked[k]:
					reasoning[id].append('few points')
					change_handler.add_score(id, -1, 0)
				continue

			if interval is None:
				debug_print ('time filter: Problem with computing.')
				# For now, crash and burn; this will make me aware of this
				# situation when it occurs.
				assert False
			else:
                                debug_print ('time filter: Interval computed: ' + str(interval))
				base, duration, siteid, txid = k
				if interval < CONFIG_ERROR_ALLOWANCE:
					debug_print ('time filter: Interval too low! Double-counting of the point in question will occur (i.e., the point will be considered its own neighbor)')
					# Give these a score of -3
					for id in parametrically_good_chunked[k]:
						reasoning[id].append('low interval 2')
						change_handler.add_score(id, -3, 0)
					continue

				# Store interval in database. Note: this just inserts (does no
				# checking for already existing interval), because it is known
				# at this point that no such interval exists.
				rows = explicit_check(change_handler, interval, base, duration, txid, siteid)
				if rows > 0:
					assert rows == 1
					store_interval_update(change_handler, interval, base, duration, txid, siteid)
					debug_print ('Updated interval for: {}+{}: {}'.format(base, duration, interval))
					# print 'Warning: About to call store_interval_assume for {}+{}={} when there is/are already {} existent interval(s)'.format(base, duration, interval, rows)
					
				else:
					#print 'Storing an interval when rows={}'.format(rows)
					store_interval_assume(change_handler, interval, base, duration, txid, siteid)
					#print 'Stored new interval for: {}+{}: {}'.format(base, duration, interval)

				# Time filter parametrically good data in the context of
				# parametrically good data from this and surrounding chunks.
				scores = time_filter(db_con, for_scoring, in_context_of=all_chunk_neighborhood)
				#print 'tf1'
				#print 'Have 5s:', [x for (x, y) in scores.items() if y == 5]
				#print 'Got scores returned:', set(scores.values())

				insert_scores(change_handler, scores, update_as_needed=True)
		else:
			# For each 'out-of-order' (already computed interval value)
			# chunk, re-compute the interval value and see if it
			# changes very much. If it does, recompute all time scores
			# in this chunk, if it does not, simply compute new scores
			# of unscored points in the chunk using the old interval
			# value.

			old_interval = interval_map[k]
			#print 'Calculating out-of-order interval with {} items'.format(len(interval_chunked[k]))
			new_interval = calculate_interval(db_con, interval_chunked[k])

			#print 'New interval: {} ({})'.format(new_interval, new_interval.__class__)
			#print 'Old interval: {} ({})'.format(old_interval, old_interval.__class__)

			# Is new interval appreciably different from old interval?
			average = (old_interval + new_interval) / 2.

			abs_val = new_interval - old_interval
			abs_val = -abs_val if abs_val < 0 else abs_val

			percentage_difference = abs_val / average
			#print 'Percentage difference:', percentage_difference

			if percentage_difference > CONFIG_INTERVAL_PERCENT_DIFFERENCE_THRESHOLD:
				#print 'Updating existing interval!'
				base, duration, siteid, txid = k
				store_interval_update(change_handler, new_interval, base, duration, txid, siteid)

				# Re-score all parametrically good data

				scores = time_filter(db_con, for_scoring, in_context_of=all_chunk_neighborhood)
				#print 'tf2'


				insert_scores(change_handler, scores, update_as_needed=True)
			else:
				debug_print( 'time filter: Not different enough!')
				# TODO

				scores = time_filter(db_con, for_scoring, in_context_of=all_chunk_neighborhood)
				#print 'tf3'

				# This does the extra work of updating the values that are
				# already in the database and will definitely not change. This
				# could be made more efficient by removing those values from
				# score. That would also remove the need for using the
				# update_set keyword arg of insert_scores (since nothing would
				# be updated, only insertions).
				insert_scores(change_handler, scores, update_set=updatables)
                #debug_print('------ End. --------------------------------------')

	# Get all of these IDs that might have been scored already and store for
	# after-action report.
	after_scored = already_scored_filter(db_con, ids)

	#print 'Request: Score {} points of which {} are already scored. Result: {} of these are scored'.format(len(ids), len(already_scored), len(after_scored))
	
# For each interval key in interval_keys, find all other keys that could
# influence an area within amount_to_ensure. For example (just start and
# duration here), with (5, 5), (15, 5), (21, 5), and amount_to_ensure=10, (5,
# 5) would map to a sequence including itself (each always includes itself) and
# (15, 5), since 5-10 and 15-20 are less than 10 apart. It would not include
# (21, 5), since (5, 10) and (21, 26) are more than 10 apart.
def compute_interval_neighborhood(interval_keys, amount_to_ensure=10):
	neighborhood = {}
	#print 'compute_interval_neighborhood()'
	#print 'keys:'

	for k in interval_keys:
		# Find all 'neighbors' of k
		start, duration, siteid, txid = k
		#print 'siteid={}, txid={}'.format(siteid, txid)
		assert duration > 0
		interest_start, interest_end = start - amount_to_ensure, start + duration + amount_to_ensure

		key_neighborhood = []

		# Collect all interval keys that deal with anything in the
		# interest_start to interest_end range
		for l in interval_keys:
			_start, _duration, _siteid, _txid = l
			assert _duration > 0
			if _siteid != siteid or _txid != txid:
				# This should not be triggered until the single txid-siteid
				# pair restriction is relaxed. But it doesn't hurt putting it
				# in now.
				continue
			_range_start, _range_end = _start, _start + _duration
			
			# Check for overlap

			# Is there no overlap because the interest area falls entirely
			# before this key? I'm very conservative on comparison here, you
			# could just only compare one point; it will only fail if something
			# weird happens like a negative duration. Still, what's one more
			# comparison?

			if interest_start < _range_start and interest_end < _range_start:
				continue

			# Or is the interest area entirely after this key's range?

			if interest_start > _range_end and interest_end > _range_end:
				continue

			key_neighborhood.append(l)

		neighborhood[k] = key_neighborhood

	return neighborhood

# Returns a structure with the same keys as chunked, but with each sequence
# value of chunked replaced with this value restricted to values in ids

def match_up_to_chunks(chunked, ids):
	id_set = set(ids)
	d = {}
	for (k, v) in chunked.items():
		new_v = [x for x in v if x in id_set]
		d[k] = new_v

	return d

# Returns true if timestamp is within +- r of the goal value.
def within(timestamp, r, goal):
	return timestamp >= (goal - r) and timestamp <= (goal + r)


# Perform time filtering on IDs, possibly in the context of a larger set of IDs
# specified in in_context_of.
def time_filter(db_con, ids, in_context_of=None):
	#print '--------TIME FILTER--------'
	# raw_input('%')

	if len(ids) == 0: return {}

	context = ids if in_context_of is None else in_context_of

	data = read_est_records(db_con, context)

	#print 'Is it in the data now?'
	is_it_there = False
	for datum in data.values():
		if within(datum['timestamp'], 1, 700):
			#print 'Yes! :)'
			is_it_there = True
			break
	if not is_it_there:
		pass #print 'No. :('


	# is all that is in context accounted for in data?
	l1 = []
	for i in context:
		if i not in data.keys():
			l1.append(i)

	# is all that is in ids accounted for in data?
	l2 = []
	for i in ids:
		if i not in data.keys():
			l2.append(i)

	#print 'Context not accounted for:', len(l1)
	#print 'IDs not accounted for:', len(l2)

	i_set = set(ids)
	c_set = set(context)

	#print 'i-c:', len(i_set.difference(c_set))
	#print 'c-i:', c_set.difference(i_set)
	#print 'i&c:', len(i_set.intersection(c_set))
	#print 'i|c:', len(i_set.union(c_set))

	assert c_set >= i_set

	# raw_input('abc')

	all_timestamps = sorted([x['timestamp'] for x in data.values()])

	#print 'All the timestamps:', all_timestamps

	scores = defaultdict(int)

	intervals = get_intervals_from_db(db_con, ids, insert_as_needed=True)
	orphan_keys = [x for x in ids if x not in intervals.keys()]
	if len(orphan_keys) > 0:
		print 'Orphan keys #:', len(orphan_keys)
		assert False

	#print 'Would write out data'

	#print 'Intervals computed for DB:', len(intervals)

	for id in ids:

		debug = False

		score = None
		
		if id not in intervals:
			score = -1
			#print 'No interval found for:', id
			assert False
		else:
			score = 0
			# calculate possible center points to investigate
			interval = intervals[id]
			tstamp = data[id]['timestamp']
			factors = [x for x in range(-CONFIG_DELTA_AWAY, CONFIG_DELTA_AWAY + 1) if x != 0]
			offsets = [x * interval for x in factors]
			absolute = [tstamp + x for x in offsets]
			search_space = [(x - CONFIG_ERROR_ALLOWANCE, x + CONFIG_ERROR_ALLOWANCE) for x in absolute]
			# Maybe drop into interpreter, might help
				
			# Perform binary search through sorted data.

			for start, end in search_space:
				start_ind = bisect.bisect_left(all_timestamps, start)
				end_ind = bisect.bisect_right(all_timestamps, end)
				if start_ind == end_ind:
					# No points found
					pass
					if debug: print 'Found NOTHING in ({}, {})'.format(start, end)
				else:
					score += 1
					if debug: print 'Found something in ({}, {})'.format(start, end)
			scores[id] = score

	#print 'Returning {} score entries'.format(len(scores))
			
	return scores


# Bucket IDs into groups depending on their siteid and txid (which should
# currently be the same for all values in a run) and start_time and duration
# such that the timestamp falls in the range [start_time, start_time +
# duration).

def time_chunk_ids(db_con, all_data, duration):

	if len(all_data) == 0: return {}

	sorted_pairs = get_sorted_timestamps_from_data(all_data.values())
	chunks = defaultdict(list)
	for (timestamp, id) in sorted_pairs:
		datum = all_data[id]
		# k = (basetime, duration)
		d, m = divmod(timestamp, duration)
		base = d * duration
		k = (base, duration, datum['siteID'], datum['deploymentID'])
		# chunks[k].append(datum)
		chunks[k].append(id)

	return chunks


def get_sorted_timestamps_from_ids(db_con, ids):
	records = read_est_records(db_con, ids)
	return get_sorted_timestamps_from_data(records.values())

def get_sorted_timestamps_from_data(data):
	pairs = []
	for datum in data:
		# print 'datum:', datum
		t = (datum['timestamp'], datum['ID'])
		pairs.append(t)

	sorted_pairs = sorted(pairs)

	return sorted_pairs



def get_parametric_passed_ids_in_chunk(db_con, k):
	cur = db_con.cursor()
	base, duration, siteid, txid = k
	q = 'select t.ID from (select ID from est where timestamp >= %s and timestamp <= %s and siteID = %s and deploymentID = %s) t LEFT JOIN estscore ON t.ID = estscore.estid AND absscore < 0;'
	cur.execute(q, (base, base + duration, siteid, txid))

	ids = []

	while True:
		r = cur.fetchone()
		if r is None: break
		r = tuple(r)
		ids.append(r[0])

	return ids

# Stores an interval value; assumes that a value for this (siteid, txid, base,
# duration) does not exist.
def store_interval_assume(change_handler, interval, base, duration, txid, siteid):
	#print 'assume args: txid={}, siteid={}'.format(txid, siteid)
	db_con = change_handler.obj
	cur = db_con.cursor()
	query_string = 'select * from interval_cache where start = %s and valid_duration = %s and deploymentID = %s and siteID = %s' % (str(base), str(duration), str(txid), str(siteid))
	#print 'Query that is expected to have no rows is "{}"'.format(query_string)
	rows = cur.execute('select * from interval_cache where start = %s and valid_duration = %s and deploymentID = %s and siteID = %s', (base, duration, txid, siteid))
	if rows > 0:
		print 'Violation of assumption for {}+{}'.format(base, duration)
	assert rows == 0
	#print 'Storing interval={}, {}+{}'.format(interval, base, duration)
	q = 'insert into interval_cache (period, start, valid_duration, deploymentID, siteID) values (%s, %s, %s, %s, %s);'
	change_handler.add_sql(q, (interval, base, duration, txid, siteid))

# Stores an interval value; assumes that a value for this (siteid, txid, base,
# duration) does exist.
def store_interval_update(change_handler, interval, base, duration, txid, siteid):
	if txid == 2:
		assert False
	#print 'update args: deploymentID={}, siteID={}'.format(txid, siteid)
	#print 'Updating interval={}, {}+{}'.format(interval, base, duration)
	q = 'update interval_cache set period = %s where start = %s and valid_duration = %s and deploymentID = %s and siteID = %s;'
	change_handler.add_sql(q, (interval, base, duration, txid, siteid))

# Calculate an interval from the IDs in the list ids (which will be all
# parametrically passing points in a time range, most likely).
def calculate_interval(db_con, ids):

	#print 'calculate_interval for {} values: {}'.format(len(ids), ids)

	sorted_pairs = get_sorted_timestamps_from_ids(db_con, ids)
	# print 'Got {} sorted pairs'.format(len(sorted_pairs))
	#print '---Calculating interval from {} points'.format(len(sorted_pairs))
	# raw_input('')
	# for (i, (timestamp, val)) in enumerate(sorted_pairs):
	# 	print '{}. {}'.format(i + 1, timestamp)
	# print '---'

	interval_windows = WindowIterator(sorted_pairs, None)

	intervals = []

	# There should only be one.
	for (i, w) in enumerate(interval_windows):
		#print 'Processed interval window:', (i+1)
		interval = w.calculate_interval_from()
		#print 'Produced interval:', interval
		intervals.append(interval)
	assert len(intervals) == 1

	# Writing out to log
	#with open('/home/qraat/interval_log.txt', 'a') as f:
	#	f.write('interval: {} ({})\n'.format(intervals[0], len(ids)))

	return intervals[0]


def init_change_handler():
	change_handler = None
	if CONFIG_JUST_STAGE_CHANGES:
		sql_output_filename = 'update.sql'
		sql_w = open(sql_output_filename, 'w')
		change_handler = ChangeHandler(sql_w, 'file')
	else:
		# NOTE: I don't declare the db connection here, because passing it
		# between modules seems to mess things up.
		change_handler = ChangeHandler(None, 'db')
	return change_handler

# Read and format into a dictionary structure a range of est records from the database.
def read_est_records_time_range(db_con, start, end, siteid, txid):
	assert start <= end
	cur = db_con.cursor()
	
	fields = ('ID', 'band3', 'band10', 'timestamp', 'siteID', 'deploymentID')

	rows = None

	field_string = ', '.join(fields)
	q = 'SELECT {} FROM est WHERE timestamp >= %s and timestamp <= %s and siteid = %s and txid = %s;'.format(field_string, siteid, txid)
	rows = cur.execute(q.format(field_string), (start, end))
	
	site_data = {}
	r = None
	while True:
		r = cur.fetchone()
		if r is None: break
		r = tuple(r)
		named_row = dict(zip(fields, r))
		for k in named_row:
			if named_row[k].__class__ == decimal.Decimal:
				named_row[k] = float(named_row[k])
		site_data[named_row['ID']] = named_row
	return site_data

# Read est records into a dictionary data structure. If expanded is true, then
# ids defines a time range, everything within which is retrieved. Otherwise,
# data exactly for records in ids are returned. Context only functions if
# expanded is True, and expands the time range (both into the past and the
# future) by context seconds.

# Precondition: All ids should represent records from a single txid/siteid pair

def read_est_records(db_con, ids, expanded=False, context=0):

	if len(ids) == 0:
		return {}

	cur = db_con.cursor()

	fields = ('ID', 'band3', 'band10', 'timestamp', 'siteID', 'deploymentID')

	rows = None

	field_string = ', '.join(fields)

	if expanded:
		#print 'Performing timestamp query'
		id_string = ', '.join([str(x) for x in ids])
		q = 'SELECT min(timestamp), max(timestamp), siteID, deploymentID FROM est WHERE ID IN ({});'.format(id_string)
		rows = cur.execute(q)
		r = cur.fetchone()
		r = tuple(r)
		min, max, siteid, txid = r
		min -= context
		max += context
		#print 'Done with that'
		#print 'Performing large est query'
		cur = db_con.cursor()
		q = 'SELECT {} FROM est WHERE timestamp >= %s and timestamp < %s and siteID = %s and deploymentID = %s'.format(field_string)
		rows = cur.execute(q, (min, max, siteid, txid))
	else:
		#print 'Querying IDs in particular'
		ids_template = ', '.join(map(lambda x : '{}', ids))
		id_string = ids_template.format(*ids)
		# print 'Going to read {} ids'.format(len(ids))
		q = 'SELECT {} FROM est WHERE ID IN ({});'.format(field_string, id_string)
		rows = cur.execute(q.format(field_string, id_string))
	
	#print 'Done'
	site_data = {}
	r = None
	#print 'Traversing cursor'
	while True:
		r = cur.fetchone()
		if r is None: break
		r = tuple(r)
		named_row = dict(zip(fields, r))
		for k in named_row:
			if named_row[k].__class__ == decimal.Decimal:
				named_row[k] = float(named_row[k])
		site_data[named_row['ID']] = named_row
	#print 'All done'

	return site_data

# Returns a 3-tuple of out-of-order IDs (those associated with a time range
# with a computed interval value), in-order IDs (those associated with a time
# range with no computed interval value), and a map from IDs in out-of-order
# IDs to the computed interval value.
def partition_by_interval_calculation(db_con, ids, siteid, txid):
	#print 'partition_by_interval_calculation()'

	cur = db_con.cursor()

	ids_template = ', '.join(map(lambda x : '{}', ids))
	id_string = ids_template.format(*ids)

	query_template = '''SELECT t.ID as ID, interval_cache.period as period 
                              FROM (SELECT ID, timestamp 
                                      FROM est 
                                     WHERE ID in ({})) t 
                              LEFT JOIN interval_cache 
                                     ON (t.timestamp >= interval_cache.start 
                                     AND t.timestamp < interval_cache.start + interval_cache.valid_duration 
                                     AND interval_cache.deploymentID = %s 
                                     AND interval_cache.siteid = %s)'''
	query = query_template.format(id_string)

	#print 'dep_id={}, site_id={}'.format(txid, siteid)
	#print 'Query about to be run: "{}"'.format(query)

	cur.execute(query, (txid, siteid))

	out_of_order_ids, in_order_ids = [], []

	id_to_interval = {}

	while True:
		r = cur.fetchone()
		if r is None: break
		r = tuple(r)
		id, period = r
		#print 'Raw:', r
		#print 'Period:', period
		if period is None:
			in_order_ids.append(id)
		else:
			out_of_order_ids.append(id)
			id_to_interval[id] = period

	#print 'partition_by_interval_calculation() end'
        return out_of_order_ids, in_order_ids, id_to_interval


# Returns a list of IDs which pass the filter
def parametrically_filter(db_con, data):

	registry = Registry(None)
	for point in data.values():
		registry.register_point(point)

	# ids = registry.get_all_ids()

	scored_points = None

	good_stuff, bad_stuff, good_ids, bad_ids, good_points, bad_points, good_xs, bad_xs, = None, None, None, None, None, None, None, None

	good_stuff, bad_stuff = registry.screen_bad(registry.points)
	#print 'Got {} good items and {} bad items'.format(len(good_stuff), len(bad_stuff))

	good_ids = [x['ID'] for x in good_stuff]
	bad_ids = [x['ID'] for x in bad_stuff]

	return good_ids


# Returns interval_map, which has keys from interval_chunked mapping to the
# interval that is given by id_to_interval for ids in value of interval_chunked
# (should all be the same; this is checked through assertions).

def get_interval_map(eligible_ids, interval_chunked, id_to_interval):

	# intervals = defaultdict(list)
	intervals = {}

	for (k, ids) in interval_chunked.items():

		# Assert in or out
		
		is_eligible = [x in eligible_ids for x in ids]
		all_eligible = all(is_eligible)
		none_eligible = not any(is_eligible)
		if all_eligible:
			pass
		elif none_eligible:
			#print 'None of these are eligible right now, no interval found.'
			continue
		else:
			debug_print('time filter: WARNING: Mixed up situation, some eligible, some ineligible...restricting to eligible...')
			orig_len = len(ids)
			ids = [x for x in ids if x in eligible_ids]
			new_len = len(ids)
			#print 'Reduced items from {} to {}'.format(orig_len, new_len)
			
			#
			# print 'Key info of mixed up chunk:', k
			# print 'This chunk has {} IDs eligible for processing and {} not eligible'.format(len([x for x in is_eligible if x]), len([x for x in is_eligible if not x]))
			# assert False
		
		interval = None
		try:
			# Throws exception if all ids in ids do not map to the same value
			# in id_to_interval
			interval = _get_interval_map_entry(ids, id_to_interval)
			assert interval is not None
			intervals[k] = interval
		except NotAllSameValueError:
			print 'Uh oh! Not all the same!'
			assert False

	return intervals

# Gets a dictionary from IDs in ids to interval values, either retrieved
# already computed from the database, or if they do not exist, computed and
# then stored in the database.
def get_intervals_from_db(db_con, ids, insert_as_needed=False):
	# TODO: can pipe in all the data needed as an argument once rather than
	# getting it on demand in the function itself.

	# change handler
	change_handler = ChangeHandler(db_con, 'db')

	# print 'get intervals for:', ids

	cur = db_con.cursor()

	ids_template = ', '.join(map(lambda x : '{}', ids))
	id_string = ids_template.format(*ids)
	q = 'select t.ID, interval_cache.period from interval_cache RIGHT JOIN (select ID, timestamp, siteID, deploymentID from est where ID in ({})) as t ON (t.siteid = interval_cache.siteid and t.deploymentID = interval_cache.deploymentID and t.timestamp >= interval_cache.start and t.timestamp < interval_cache.start + interval_cache.valid_duration) where interval_cache.start IS NOT NULL;'

	row = cur.execute(q.format(id_string))

	intervals = {}

	while True:
		r = cur.fetchone()
		if r is None: break
		r = tuple(r)
		intervals[r[0]] = float(r[1])

	#print 'Intervals returned from DB:', intervals

	ids_with_intervals = intervals.keys()

	ids_with_no_interval = [x for x in ids if x not in ids_with_intervals]
	

	# create interval keys for these - some assumptions about where windows end
	# are here...
	data = read_est_records(db_con, ids_with_no_interval)
	intervals_to_compute = set()
	for id, record in data.items():
		siteid = record['siteid']
		txid = record['txid']
		timestamp = record['timestamp']
		duration = CONFIG_INTERVAL_WINDOW_SIZE
		base = timestamp - (timestamp % duration)
		key = (base, duration, siteid, txid)
		intervals_to_compute.add(key)
	
	if len(intervals_to_compute) > 0:
		if not insert_as_needed:
			# Cannot continue
			assert False
		else:
			for (base, duration, siteid, txid) in intervals_to_compute:
				# Get all data within this interval and parametrically score.
				# Take all passing and calculate interval.
				interval_data = read_est_records_time_range(db_con, base, base + duration, siteid, txid)
				passed_ids = parametrically_filter(db_con, interval_data)
				interval = calculate_interval(db_con, passed_ids)
				assert interval != 0
				import code
				code.interact(local=locals())
				store_interval_assume(change_handler, interval, base, duration, txid, siteid)

	return intervals

# Insert scores (a dictionary from ID to absolute score) into the database. If
# update_as_needed is True, the database will be queried for all scores, and
# those for which a record currently exists will be updated, while all others
# will be inserted. If update_as_needed is False, then IDs that are in
# update_set will be updated and all others will be inserted. The default
# values specify that all scores will be inserted.
def insert_scores(change_handler, scores, update_as_needed=False, update_set=set()):

        db_con = change_handler.obj
	scores = dict(scores)

        deletes = []; inserts = []
        for (est_id, score) in scores.iteritems():
          deletes.append(str(est_id))
          inserts.append((est_id, score, _rel_score(score)))

        cur = db_con.cursor()
        cur.execute('DELETE FROM estscore WHERE estID IN ({})'.format(
                            ', '.join(deletes)))
	cur.executemany(INSERT_TEMPLATE, inserts)

class NotAllSameValueError(Exception):
	def __init__(self):
		pass

# Get the single value which all IDs in ids map to in id_to_interval. If no
# such single value exists, throw an exception.
def _get_interval_map_entry(ids, id_to_interval):
	for id in ids:
		assert id in id_to_interval
	vals = [id_to_interval[x] if x in id_to_interval else None for x in ids]
	if not all([x == vals[0] for x in vals]):
		raise NotAllSameValueError()
	return vals[0]

# Calculate relative score from absolute score.
def _rel_score(score):
	rel_score_to_scale = score if score > 0 else 0
	# change_handler.add_score(id, score, float(rel_score_to_scale) / (CONFIG_DELTA_AWAY * 2))
	rel_score = float(rel_score_to_scale) / (CONFIG_DELTA_AWAY * 2)
	return rel_score

# Get cursor value from database. Returns a default value if no such cursor
# value exists.
def get_cursor_value(handler, name):
	q = 'select value from `cursor` where name = %s'
	db_con = handler.obj
	cur = db_con.cursor()
	rows = cur.execute(q, (name,))
	if rows == 0:
		# Default value
		return 0
	elif rows == 1:
		r = cur.fetchone()
		r = tuple(r)
		return r[0]
	else:
		raise Exception('Ambiguous cursor value (found {}) for "{}"'.format(rows, name))

# Inserts (with a fallback to update) the cursor with the specified name and
# value.
def update_cursor_value(handler, name, value):
	q = 'insert into `cursor` (name, value) VALUES (%s, %s) ON DUPLICATE KEY UPDATE value = %s'
	db_con = handler.obj
	cur = db_con.cursor()
	rows = cur.execute(q, (name, value, value))
	print 'Update cursor "{}" returns: {}'.format(name, rows)

# Returns number of rows matching. Hoping for zero.
def explicit_check(change_handler, interval, base, duration, txid, siteid):
	db_con = change_handler.obj
	q = 'SELECT * from interval_cache where start = %s and valid_duration = %s and deploymentID = %s and siteID = %s'
	cur = db_con.cursor()
	#print 'Performing explicit check query: "{}"'.format(q % (str(base), str(duration), str(txid), str(siteid)))
	rows = cur.execute(q, (base, duration, txid, siteid))
	return rows


def _log(id, score, rel_score):
	with open('/home/qraat/5scorer.txt', 'a') as f:
		f.write('id: {}, abs: {}, rel: {}\n'.format(id, score, rel_score))
