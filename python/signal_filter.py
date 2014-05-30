# Copyright (C) 2013 Todd Borrowman, Christopher Patton
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
import matplotlib.pyplot
from numpy import histogram
import numpy
import qraat
import random
import sys
import bisect
import math
import traceback

import util



THRESHOLD_BAND3 = 150
THRESHOLD_BAND10 = 900

# Distance to look for neighbors while scoring
CONFIG_ERROR_ALLOWANCE = 0.2

# Search this many interval distances in both directions of a point for corroborating neighbors
CONFIG_DELTA_AWAY = 3

# False if actually apply changes to database, True if just write script to file (update.sql in cwd)
CONFIG_JUST_STAGE_CHANGES = False

# How long a period the interval should be calculated over
CONFIG_INTERVAL_WINDOW_SIZE = float(3 * 60) # Three minutes (given in seconds)

# Minimum interval percentage difference which must occur from old value to
# trigger superceding of the interval with the new ones and re-scoring of
# slice.
CONFIG_INTERVAL_PERCENT_DIFFERENCE_THRESHOLD = 0.25

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

	def optionally_highlight_all_points(self, ids):
		self.optionally_highlight_some_points(self.points)

	def read_txlist_thresholds(self):

		if self.txlist is None:
			d = {}
			db_con = qraat.util.get_db('reader')
			cur = db_con.cursor()
			q = 'select ID, thresh_band3, thresh_band10 from txlist;'
			rows = cur.execute(q)
			for row in cur.fetchall():
				row = tuple(row)
				d[row[0]] = {'band3':row[1], 'band10':row[2]}
			self.txlist = d
			
			

	def get_matching_points(self, points, **kw):

		self.read_txlist_thresholds()
		print 'Getting matching points out of {}'.format(len(points))
		#counts = defaultdict(int)
		counts = defaultdict(list)

		#filter_freq = filter_range('frequency', kw['frequency'], 2000)



		xs = [x['timestamp'] for x in points]
		histo = histogram(xs, bins=(24 * 60))
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
			print '{} points filtered out by frequency'.format(len(highlighted))
			bad_points.update([x['ID'] for x in highlighted])
			good_points = [x for x in points if x['ID'] not in bad_points]
			print 'That leaves {} good points'.format(len(good_points))
			for h in highlighted:
				counts[h['ID']].append('frequency')
		elif enable_prefiltering:
			print 'Would have prefiltered by rate, but no violations'

		filter_band3 = filter_values_over('band3', self.txlist)

		highlighted = get_matching_points_op(points, filter_band3)
		if enable_prefiltering and highlighted is not None:
			print '{} points filtered out by band3'.format(len(highlighted))
			bad_points.update([x['ID'] for x in highlighted])
			good_points = [x for x in points if x['ID'] not in bad_points]
			print 'That leaves {} good points'.format(len(good_points))
			for h in highlighted:
				counts[h['ID']].append('band3')
		elif enable_prefiltering:
			print 'Would have prefiltered by band3, but no violations'

		filter_band10 = filter_values_over('band10', self.txlist)

		highlighted = get_matching_points_op(points, filter_band10)
		if enable_prefiltering and highlighted is not None:
			print '{} points filtered out by band10'.format(len(highlighted))
			bad_points.update([x['ID'] for x in highlighted])
			good_points = [x for x in points if x['ID'] not in bad_points]
			print 'That leaves {} good points'.format(len(good_points))
			for h in highlighted:
				counts[h['ID']].append('band10')
		elif enable_prefiltering:
			print 'Would have prefiltered by band10, but no violations'

		return counts


	def optionally_highlight_some_points(self, item_to_plot, points, **kw):
		print 'optionally_highlight_some_points() -> get_matching_points()'
		counts = self.get_matching_points(points, **kw)

		for (i, j) in counts.items():
			if j == 0:
				print 'key', i, 'is 0'

		ids_by_count = defaultdict(list)




		colors = ('g', 'r', 'c', 'm', 'k', 'y', 'burlywood', 'chartreuse', \
				'cornflowerblue', 'darkolivegreen', 'indianred', 'greenyellow', \
				'goldenrod', 'indigo', 'limegreen', 'mediumorchid')
		current_unassigned = 0
		links = {}
		current_color = 0
		combos = ('frequency', 'band3', 'band10', 'edsp')
		for i in range(len(combos) + 1):
			for combo in itertools.combinations(combos, i):
				links[combo] = colors[current_color]
				current_color += 1
		color_to_go = defaultdict(list)
		print 'Finished generating structure:', links
		print 'There are {} problematic points'.format(len(counts))
		for (k, v) in counts.items():
			#h = hash(tuple(v))
			h = tuple(v)
			color = links[h]
			color_to_go[color].append(k)
			#if h in links.keys():
				#color = links[h]
				#color_to_go[color].append(k)
			#else:
				#new_color = colors[current_unassigned]
				#links[h] = new_color
				#print 'Assigned color {} to {}'.format(new_color, v)
				#current_unassigned += 1


		for (color, ids) in color_to_go.items():
			plot_against = self.arguments['plotAgainst'] if 'plotAgainst' in self.arguments else 'timestamp'
			my_points = [x for x in points if x['ID'] in ids]
			xs, ys = zip(*[(x[plot_against], x[item_to_plot]) for x in my_points])
			#matplotlib.pyplot.gca().set_yscale('log')
			if kw['log']:
				ys = numpy.log(ys)
			matplotlib.pyplot.scatter(xs, ys, c=color)
			print 'Scattering {} points in color {}'.format(len(xs), color)

		print 'Returning...'
		return

		for (k, v) in points_by_count.items():
			if len(v) == 0:
				print 'Huh?:', k
			plot_against = self.arguments['plotAgainst'] if 'plotAgainst' in self.arguments else 'timestamp'
			xs, ys = zip(*[(x[plot_against], x[item_to_plot]) for x in v])
			# generate color

			color_string = str(1. - (float(k) / max_val))

			#matplotlib.pyplot.scatter(xs, ys, c=color_string)
			matplotlib.pyplot.scatter(xs, ys, c='r')





		print 'length:', len(counts)
		for (k, v) in counts.items():
			ids_by_count[v].append(k)

		points_by_count = {}
		print '&'
		for (k, v) in ids_by_count.items():
			print '!!'
			points_by_count[k] = [x for x in points if x['ID'] in v]
		print '&'

		print len(points_by_count)
		counts = points_by_count.keys()


		if len(counts) == 0:
			print 'Skip this one'
			return

		total_weird_points = 0
		for v in points_by_count.values():
			total_weird_points += len(v)

		print 'Weird points found:', total_weird_points


		offset = min(counts)
		r = max(counts) - offset
		max_val = max(counts)

		colors = ('g', 'r', 'c', 'm')

		for (k, v) in points_by_count.items():
			if len(v) == 0:
				print 'Huh?:', k
			plot_against = self.arguments['plotAgainst'] if 'plotAgainst' in self.arguments else 'timestamp'
			xs, ys = zip(*[(x[plot_against], x[item_to_plot]) for x in v])
			# generate color

			color_string = str(1. - (float(k) / max_val))

			#matplotlib.pyplot.scatter(xs, ys, c=color_string)
			matplotlib.pyplot.scatter(xs, ys, c='r')

	def bw_highlight_some_points(self, item_to_plot, points):
		print 'bw_highlight_some_points -> get_matching_points()'
		counts = self.get_matching_points(points)
		trunc = counts.keys()[:10]
		print 'trunc:', [(x, y) for (x, y) in counts.items() if x in trunc]
		for v in counts.values():
			for e in v:
				xs, ys = zip(*[(x['timestamp'], x[item_to_plot]) for x in v])

				# generate color
				matplotlib.pyplot.scatter(xs, ys, c='r')
		print 'done with bw highlight'

	#def get_good_points(self, item_to_plot, points, **kw):
		#bad_points = self.get_bad_points(item_to_plot, [x[0] for x in points], **kw)
		#good_points = [x for x in points if x[0] not in bad_points]
		#return good_points

	# now I just return a good and a bad list of 3-tuples, so points stay
	# linked to IDs. For more info, see freq.py.
	#((good_xs, good_ys), (bad_xs, bad_ys), good_ids, bad_ids) = registry.screen_bad(item_to_plot, points)
	def screen_bad(self, points, **kw):
		print 'Categorizing {} points'.format(len(points))
		print 'screen_bad() start'
		ids = [x['ID'] for x in points]
		bad_point_map, good_points = self.get_bad_points(ids, **kw)
		print 'done getting bad points ({}) and good points ({})'.format(len(bad_point_map), len(good_points))

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
		print 'bad ids ({}): {}'.format(len(bad_ids), bad_ids[:10])
		if len(bad_ids) > 0: print 'type is:', bad_ids[0].__class__
		#good_ids = [x[0] for x in points if x[0] not in bad_ids]

		good_point_data, bad_point_data = [], []
		bad_points = []
		for point in points:
			if point['ID'] in bad_ids:
				bad_points.append(point)

		#bad_point_data = [x for x in
		#good_point_data = [x for x in points if x[0] not in bad_ids]
		#good_points, bad_points = [], []
		#for point in points:
			#if point[0] in good_ids:
				#good_points.append((point[1], point[2]))
			#else:
				## If it's not good it's bad.
				#bad_points.append((point[1], point[2]))
		##good_points = [(x[1], x[2]) for x in points if x[0] in good_ids]
		##bad_points = [(x[1], x[2]) for x in points if x[0] in bad_ids]
		#if len(good_points) == 0:
			#return None
		## NOTE: Still fail if no good points. I want to be aware of that.
		#good_xs, good_ys = zip(*good_points)

		#bad_xs, bad_ys = [], []
		#try:
			#bad_xs, bad_ys = zip(*bad_points)
		#except ValueError:
			#pass

		#print 'screen_bad() end'
		#return ((good_xs, good_ys), (bad_xs, bad_ys), good_ids, bad_ids)
		#return good_point_data, bad_point_data
		return good_points, bad_points

		#if 'with_id' in kw.keys() and kw['with_id']:
			#return good_point_ids, z
		#else:
			#return z

	# NOTE: Should this be a method?
	def get_matlab_style_points_for_ids(self, ids, x_field, y_field, verbose=False):
		xs, ys = [], []
		if verbose: print 'Iterating through {} points'.format(len(self.points))
		if verbose: print 'Looking for {} IDs, something like: {}'.format(len(ids), ids[:10])
		for point in self.points:
			if point['ID'] in ids:
				xs.append(point[x_field])
				ys.append(point[y_field])
		return xs, ys



	def optionally_highlight_points(self, item_to_plot, ids, **kw):
		points = [x for x in self.points if x['ID'] in ids]
		self.optionally_highlight_some_points(item_to_plot, points, **kw)

	def get_bad_simple(self):
		# Work on all in self.points
		counts = self.get_matching_points(self.points)
		for point in points:
			if point['ID'] not in counts.keys():
				good_points.append(point)
		# print '|counts| = {}'.format(len(counts))
		# for (k, v) in counts.items()[:10]:
		# 	print 'count {} -> {}'.format(k, v)
		return counts, good_points

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
		for point in points:
			if point['ID'] not in counts.keys():
				good_points.append(point)
		print '|counts| = {}'.format(len(counts))
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
		print 'returning none!'
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

		print 'upper:', upper_bound
		print 'lower:', lower_bound

		print 'processing:', point[field_name], field_name
		if point[field_name] < lower_bound or point[field_name] > upper_bound:
			return True
		else:
			print 'something in the middle!'
			return False
	return filter_func

def filter_values_over(field_name, threshold_dict):
	def filter_func(point, points):
		threshold = threshold_dict[point['txid']][field_name]
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
			db_con = util.get_db('writer')
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
	
	def add_score(self, estid, absscore, relscore):
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
		if estid == 214183264:
			f = open('/home/sean/scoreinfo.txt', 'a')
			f.write('single abs={}, rel={}\n'.format(absscore, relscore))
			if absscore == -2:
				f.write('<-- this one is parametrically bad - single execute statement\n')
				# f.close()
				# assert False
			# try:
			# 	assert False
			# except AssertionError:
			# 	# tr = sys.exc_info()[2]
			# 	traceback.print_exc(f)
			# traceback.print_tb(tr, limit=None, file=f)
			f.write('------------------------\n')
			f.close()
			print 'ADDING ESTID'
		print 'Adding score!'
		if ADD_EVERY == 0:
			# Apply update immediately
			cursor = self.obj.cursor()
			cursor.execute(INSERT_TEMPLATE, (estid, absscore, relscore))
			return cursor
		else:
			self.buffer.append((estid, absscore, relscore))
			if len(self.buffer) >= ADD_EVERY:
				self.flush_db()

	def add_sql_db(self, sql_text, sql_args):
		cursor = self.obj.cursor()
		print 'Running query:', sql_text % sql_args
		rows = cursor.execute(sql_text, sql_args)
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
			print 'For requested window offset {} it\'s messed up. Actual index = {}, original request = {}'.format(window_offset, match_ind, orig_match_ind)
		return window.attributes[prop]

	def report(self):
		print 'There are a total of {} windows'.format(len(self.windows))
		for i, window in enumerate(self.windows):
			if 'interval' in window.attributes and window.attributes['interval'] is None:
				print 'Window {} interval malformed'.format(i)

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
					print 'Correcting negative window index Original {} + offset {}'.format(i, offset)
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
				print 'Index nearest (left) to {} is {}'.format(start, start_ind)
				end_ind = bisect.bisect_right(self.xs, end)
				print 'Index nearest (right) to {} is {}'.format(end, end_ind)
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
		print 'adding attribute:', k
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

		argmax = numpy.argmax(histo[0])
		max_likelihood_interval = histo[1][argmax]

		if all(histo[0] == 0):
			print 'Skipping interval detection for {}/{} because no data found'.format(txid, slice_id)
			return None

		assert any(histo[0] != 0)
		print 'Performing interval detection for {}/{}'.format(txid, slice_id)
		candidates = sort_by(histo[0], histo[1])
		#print 'Got {} candidates'.format(len(candidates))
		overtone_results = overtone_vote(candidates)

		most_likely_interval = None
		highest_count = -1
		for (interval, count) in overtone_results.items():
			if count > highest_count:
				highest_count = count
				most_likely_interval = interval

		return most_likely_interval


def sort_by(arg1, arg2):
	ret = []
	sorting_inds = arg1.argsort()
	r_sorting_inds = list(reversed(sorting_inds))
	highest_two_vals = [None, None]
	for val in (arg1[x] for x in r_sorting_inds):
		if highest_two_vals[0] is None:
			highest_two_vals[0] = val
		elif highest_two_vals[1] is None and highest_two_vals[0] != val:
			highest_two_vals[1] = val
		else:
			break
	if arg1[r_sorting_inds[0]] == 1:
		# collect all of 1
		return [arg2[x] for x in range(len(arg1)) if arg1[x] == 1]
	else:
		print 'Got highest two values:', highest_two_vals
		return [arg2[x] for x in range(len(arg1)) if arg1[x] in highest_two_vals]

OVERTONE_LIMIT = 8
OVERTONE_ERROR = 0.1

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
#	entry in the est table. Nothing in here should be brand new...a slight delay is applied in the higher-level program that makes sure there is context for scoring/interval calculation.
# Output: none explicit - implicitly, score entries added for each id in ids

def score(ids):
	change_handler = init_change_handler()
	db_con = qraat.util.get_db('writer')

	parametrically_poor = set()

	if len(ids) == 0:
		print 'score() with zero length input...'
		return

	id_set = set(ids)

	data = read_est_records(db_con, ids, expanded=True)

	cur = db_con.cursor()
	ids_template = ', '.join(map(lambda x : '{}', ids))
	id_string = ids_template.format(*ids)
	q = 'SELECT DISTINCT siteid, txid from est WHERE ID IN ({});'.format(id_string)
	rows = cur.execute(q)
	r = cur.fetchone()
	assert rows == 1
	siteid, txid = r

	# Get all of these IDs that might have been scored already and store for
	# after-action report.
	already_scored = already_scored_filter(db_con, ids)

	out_of_order_ids, in_order_ids, id_to_interval = partition_by_interval_calculation(db_con, ids, siteid, txid)

	print 'Found {} out of order, {} in order'.format(len(out_of_order_ids), len(in_order_ids))

	# param filter
	all_that_passed_filter_ids = parametrically_filter(db_con, data)

	passed_filter_ids_set = set(all_that_passed_filter_ids)

	new_filtered_ids = id_set.intersection(passed_filter_ids_set)

	print '{} items passed parametric filter'.format(len(new_filtered_ids))

	# Insert scores for parametrically bad points...
	for id in id_set.difference(all_that_passed_filter_ids):
		change_handler.add_score(id, -2, 0)
		parametrically_poor.add(id)

	interval_chunked = time_chunk_ids(db_con, data, CONFIG_INTERVAL_WINDOW_SIZE)

	unscored_ids_chunked = match_up_to_chunks(interval_chunked, id_set.difference(parametrically_poor))

	interval_map = get_interval_map(out_of_order_ids, interval_chunked, id_to_interval)

	print '---------------------------------'
	for (k, v) in interval_map.items():
		print '{} -> {}'.format(k, v)
	print '---------------------------------'

	# raw_input()


	# Calculate brand new intervals for those which need it
	for k in interval_chunked:
		# b = get_parametric_passed_ids_in_chunk(db_con, k)
		# all_chunk_ids = interval_chunked[k] + get_parametric_passed_ids_in_chunk(db_con, k)
		all_chunk_ids = interval_chunked[k]
		unscored_ids = unscored_ids_chunked[k]
		# all_chunk_ids = a + b

		if k not in interval_map:
			print 'No interval for {} yet.'.format(k)
			interval = calculate_interval(db_con, interval_chunked[k])
			if interval is None:
				print 'Problem with computing interval for this.'
			else:
				print 'Interval computed:', interval
				base, duration, siteid, txid = k
				store_interval_assume(change_handler, interval, base, duration, txid, siteid)
				print 'Stored interval for: {}+{}: {}'.format(base, duration, interval)

				print 'About to time filter now!'
				scores = time_filter(db_con, unscored_ids, in_context_of=all_chunk_ids)
				print 'Did I succeed?'
				insert_scores(change_handler, scores)
		else:
			# For each 'out-of-order' (already computed interval value)
			# chunk, re-compute the interval value and see if it
			# changes very much. If it does, recompute all time scores
			# in this chunk, if it does not, simply compute new scores
			# of unscored points in the chunk using the old interval
			# value.
			print 'displaying interval map:'
			for k, v in interval_map.items():
				print '{} -> {}'.format(k, v)
			print '()()()()()'
			old_interval = interval_map[k]
			print 'Calculating out-of-order interval with {} items'.format(len(interval_chunked[k]))
			new_interval = calculate_interval(db_con, interval_chunked[k])

			print 'New interval: {} ({})'.format(new_interval, new_interval.__class__)
			print 'Old interval: {} ({})'.format(old_interval, old_interval.__class__)

			# Is new interval appreciably different from old interval?
			average = (old_interval + new_interval) / 2.
			abs_val = new_interval - old_interval
			abs_val = -abs_val if abs_val < 0 else abs_val
			percentage_difference = abs_val / average
			if percentage_difference > CONFIG_INTERVAL_PERCENT_DIFFERENCE_THRESHOLD:
				store_interval_update(change_handler, new_interval, base, duration, txid, siteid)
				scores = time_filter(db_con, all_chunk_ids_set)
				insert_scores(change_handler, scores, update=True)
				pass
			else:
				scores = time_filter(db_con, unscored_ids, in_context_of=all_chunk_ids)
				analyze(unscored_ids, all_chunk_ids, scores)
				insert_scores(change_handler, scores)

	# Get all of these IDs that might have been scored already and store for
	# after-action report.
	after_scored = already_scored_filter(db_con, ids)

	print 'Request: Score {} points of which {} are already scored. Result: {} of these are scored'.format(len(ids), len(already_scored), len(after_scored))
	

def analyze(ids_for_scoring, all_ids, scores):
	set_a = set(ids_for_scoring)
	set_b = set(all_ids)
	set_c = set(scores)
	c = False
	if 214183264 in set_a:
		print 'Scoring the point! This should not happen!'
		c = True
	if 214183264 in set_b:
		print 'It\'s in the context, not necessarily a problem'
		c = True
	if not c:
		print 'Nothing much to say'
	print 'analyze()'
	print 'a {} -> {}'.format(len(ids_for_scoring), len(set_a))
	print 'b {} -> {}'.format(len(all_ids), len(set_b))
	print 'c {} -> {}'.format(len(scores), len(set_c))

	print 'Scoring IDs that are not contained in all IDs:', len(set_a.difference(set_b))
	print 'Scores that are not in IDs to be scored:', len(set_c.difference(set_a))
	print 'IDs to be scored that are not in scores:', len(set_a.difference(set_c))

	# if c: raw_input()

def match_up_to_chunks(chunked, ids):
	id_set = set(ids)
	d = {}
	for (k, v) in chunked.items():
		new_v = [x for x in v if x in id_set]
		d[k] = new_v

	return d


# Pre-condition: intervals must exist in the database covering all the items in ids

def time_filter(db_con, ids, in_context_of=None):

	if len(ids) == 0: return {}

	context = ids if in_context_of is None else in_context_of

	data = read_est_records(db_con, context)


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

	print 'Context not accounted for:', len(l1)
	print 'IDs not accounted for:', len(l2)

	i_set = set(ids)
	c_set = set(context)

	print 'i-c:', len(i_set.difference(c_set))
	print 'c-i:', c_set.difference(i_set)
	print 'i&c:', len(i_set.intersection(c_set))
	print 'i|c:', len(i_set.union(c_set))

	assert c_set >= i_set

	# raw_input('abc')

	all_timestamps = sorted([x['timestamp'] for x in data.values()])

	scores = defaultdict(int)

	intervals = get_intervals_from_db(db_con, ids, insert_as_needed=True)
	orphan_keys = [x for x in ids if x not in intervals.keys()]
	if len(orphan_keys) > 0:
		print 'Orphan keys #:', len(orphan_keys)
		assert False

	print 'Would write out data'

	print 'Intervals computed for DB:', len(intervals)

	for id in ids:

		score = None
		
		if id not in intervals:
			score = -1
			print 'No interval found for:', id
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

			for start, end in search_space:
				start_ind = bisect.bisect_left(all_timestamps, start)
				end_ind = bisect.bisect_right(all_timestamps, end)
				if start_ind == end_ind:
					# No points found
					pass
				else:
					score += 1
			scores[id] = score

	return scores




def time_chunk_ids(db_con, all_data, duration):

	if len(all_data) == 0: return {}

	sorted_pairs = get_sorted_timestamps_from_data(all_data.values())
	chunks = defaultdict(list)
	for (timestamp, id) in sorted_pairs:
		datum = all_data[id]
		# k = (basetime, duration)
		d, m = divmod(timestamp, duration)
		base = d * duration
		k = (base, duration, datum['siteid'], datum['txid'])
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
	q = 'select t.ID from (select ID from est where timestamp >= %s and timestamp <= %s and siteid = %s and txid = %s) t LEFT JOIN estscore ON t.ID = estscore.estid AND absscore < 0;'
	cur.execute(q, (base, base + duration, siteid, txid))

	ids = []

	while True:
		r = cur.fetchone()
		if r is None: break
		r = tuple(r)
		ids.append(r[0])

	return ids

def store_interval_assume(change_handler, interval, base, duration, txid, siteid):
	print 'Storing interval={}, {}+{}'.format(interval, base, duration)
	q = 'insert into interval_cache (period, start, valid_duration, txid, siteid) values (%s, %s, %s, %s, %s);'
	change_handler.add_sql(q, (interval, base, duration, txid, siteid))

def store_interval_update(change_handler, interval, base, duration, txid, siteid):
	print 'Updating interval={}, {}+{}'.format(interval, base, duration)
	q = 'update interval_cache set interval = %s where base = %s and duration = %s and txid = %s and siteid = %s;'
	change_handler.add_sql(q, (interval, base, duration, txid, siteid))


def calculate_interval(db_con, ids):

	print 'calculate_interval for {} values'.format(len(ids))

	sorted_pairs = get_sorted_timestamps_from_ids(db_con, ids)
	# print 'Got {} sorted pairs'.format(len(sorted_pairs))
	print '---Calculating interval from {} points'.format(len(sorted_pairs))
	# for (i, (timestamp, val)) in enumerate(sorted_pairs):
	# 	print '{}. {}'.format(i + 1, timestamp)
	# print '---'

	interval_windows = qraat.signal_filter.WindowIterator(sorted_pairs, None)

	intervals = []

	# There should only be one.
	for (i, w) in enumerate(interval_windows):
		print 'Processed interval window:', (i+1)
		interval = w.calculate_interval_from()
		print 'Produced interval:', interval
		intervals.append(interval)
	assert len(intervals) == 1
	return intervals[0]


def init_change_handler():
	change_handler = None
	if CONFIG_JUST_STAGE_CHANGES:
		sql_output_filename = 'update.sql'
		sql_w = open(sql_output_filename, 'w')
		change_handler = qraat.signal_filter.ChangeHandler(sql_w, 'file')
	else:
		# NOTE: I don't declare the db connection here, because passing it
		# between modules seems to mess things up.
		change_handler = qraat.signal_filter.ChangeHandler(None, 'db')
	return change_handler


def read_est_records(db_con, ids, expanded=False):

	if len(ids) == 0:
		return []

	cur = db_con.cursor()

	fields = ('ID', 'band3', 'band10', 'timestamp', 'siteid', 'txid')

	rows = None

	field_string = ', '.join(fields)

	if expanded:
		q = 'SELECT min(timestamp), max(timestamp) FROM est;'
		rows = cur.execute(q)
		r = cur.fetchone()
		r = tuple(r)
		min, max = r
		cur = db_con.cursor()
		q = 'SELECT {} FROM est WHERE timestamp >= %s and timestamp <= %s'
		rows = cur.execute(q.format(field_string), (min, max))
	else:
		ids_template = ', '.join(map(lambda x : '{}', ids))
		id_string = ids_template.format(*ids)
		# print 'Going to read {} ids'.format(len(ids))
		q = 'SELECT {} FROM est WHERE ID IN ({});'.format(field_string, id_string)
		rows = cur.execute(q.format(field_string, id_string))
	
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


def partition_by_interval_calculation(db_con, ids, siteid, txid):
	print 'partition_by_interval_calculation()'

	cur = db_con.cursor()

	ids_template = ', '.join(map(lambda x : '{}', ids))
	id_string = ids_template.format(*ids)

	query_template = 'select t.ID as ID, interval_cache.period as period from (select ID, timestamp from est where ID in ({})) t LEFT JOIN interval_cache ON (t.timestamp >= interval_cache.start and t.timestamp <= interval_cache.start + interval_cache.valid_duration and interval_cache.txid = %s and interval_cache.siteid = %s)'
	query = query_template.format(id_string)

	print 'txid={}, siteid={}'.format(txid, siteid)
	print 'Query about to be run: "{}"'.format(query)

	cur.execute(query, (txid, siteid))

	out_of_order_ids, in_order_ids = [], []

	id_to_interval = {}

	while True:
		r = cur.fetchone()
		if r is None: break
		r = tuple(r)
		id, period = r
		print 'Raw:', r
		print 'Period:', period
		if period is None:
			in_order_ids.append(id)
		else:
			out_of_order_ids.append(id)
			id_to_interval[id] = period

	print 'partition_by_interval_calculation() end'
	return out_of_order_ids, in_order_ids, id_to_interval


# Returns a list of IDs which pass the filter
def parametrically_filter(db_con, data):

	registry = qraat.signal_filter.Registry(None)
	for point in data.values():
		registry.register_point(point)

	# ids = registry.get_all_ids()

	scored_points = None

	good_stuff, bad_stuff, good_ids, bad_ids, good_points, bad_points, good_xs, bad_xs, = None, None, None, None, None, None, None, None

	good_stuff, bad_stuff = registry.screen_bad(registry.points)
	print 'Got {} good items and {} bad items'.format(len(good_stuff), len(bad_stuff))

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
			print 'None of these are eligible right now, no interval found.'
			continue
		else:
			print 'WARNING: Mixed up situation, some in, some out...problematic. Not processing these IDs.'
			continue
		
		interval = None
		try:
			interval = _get_interval_map_entry(ids, id_to_interval)
			assert interval is not None
			intervals[k] = interval
		except NotAllSameValueError:
			print 'Uh oh! Not all the same!'

	return intervals

def get_intervals_from_db(db_con, ids, insert_as_needed=False):

	# change handler
	change_handler = ChangeHandler(db_con, 'db')

	# print 'get intervals for:', ids

	cur = db_con.cursor()

	ids_template = ', '.join(map(lambda x : '{}', ids))
	id_string = ids_template.format(*ids)
	q = 'select t.ID, interval_cache.period from interval_cache RIGHT JOIN (select ID, timestamp, siteid, txid from est where ID in ({})) as t ON (t.siteid = interval_cache.siteid and t.txid = interval_cache.txid and t.timestamp >= interval_cache.start and t.timestamp <= interval_cache.start + interval_cache.valid_duration) where interval_cache.start IS NOT NULL;'

	row = cur.execute(q.format(id_string))

	intervals = {}

	while True:
		r = cur.fetchone()
		if r is None: break
		r = tuple(r)
		intervals[r[0]] = float(r[1])

	print 'Intervals returned from DB:', intervals

	ids_with_intervals = intervals.keys()

	ids_with_no_interval = [x for x in ids if x not in ids_with_intervals]
	if len(ids_with_no_interval) == 0:
		if insert_as_needed:
			data = read_est_records(db_con, ids)
			interval_chunked = time_chunk_ids(db_con, data, CONFIG_INTERVAL_WINDOW_SIZE)
			for interval_key, interval_ids in interval_chunked.items():
				base, duration, siteid, txid = interval_key
				interval = calculate_interval(db_con, interval_ids)
				store_interval_assume(change_handler, interval, base, duration, txid, siteid)
		else:
			assert False

	return intervals


def insert_scores(change_handler, scores, update=False):

	db_con = change_handler.obj

	args = []
	for (id, score) in scores.items():
		rel_score = _rel_score(score)
		args.append((id, score, rel_score))

	if update:

		all_to_insert = set(scores.keys())
		cur = db_con.cursor()
		ids_template = ', '.join(map(lambda x : '{}', ids))
		id_string = ids_template.format(*ids)
		q = 'SELECT estid in estscore WHERE estid IN ({})'.format(id_string)
		rows = cur.execute(q)
		already_there = set()
		while True:
			r = cur.fetchone()
			if r is None: break
			r = tuple(r)
			already_there.add(r[0])

		newly_there = all_to_insert.difference(already_there)

		updates = []
		for id in already_there:
			score = scores[id]
			rel_score = _rel_score(score)
			updates.append((score, rel_score, id))
		cur = db_con.cursor()
		cur.executemany(qraat.signal_filter.UPDATE_TEMPLATE, updates)

		inserts = []
		for id in newly_there:
			score = scores[id]
			rel_score = _rel_score(score)
			inserts.append((id, score, rel_score))
		cur = db_con.cursor()
		cur.executemany(qraat.signal_filter.INSERT_TEMPLATE, inserts)
		

		pass
	else:
		change_handler.db_execute_many(qraat.signal_filter.INSERT_TEMPLATE, args)

class NotAllSameValueError(Exception):
	def __init__(self):
		pass

def _get_interval_map_entry(ids, id_to_interval):
	for id in ids:
		assert id in id_to_interval
	vals = [id_to_interval[x] if x in id_to_interval else None for x in ids]
	if not all([x == vals[0] for x in vals]):
		raise NotAllSameValueError()
	return vals[0]

def _rel_score(score):
	rel_score_to_scale = score if score > 0 else 0
	# change_handler.add_score(id, score, float(rel_score_to_scale) / (CONFIG_DELTA_AWAY * 2))
	rel_score = float(rel_score_to_scale) / (CONFIG_DELTA_AWAY * 2)
	return rel_score

