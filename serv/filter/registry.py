from collections import defaultdict
import itertools
import matplotlib.pyplot
from numpy import histogram
import numpy
import random
import sys

THRESHOLD_BAND3 = 150
THRESHOLD_BAND10 = 900

class Registry:

	def __init__(self, args):
		self.points = []
		self.arguments = args

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

	def get_matching_points(self, points, **kw):
		print 'Getting matching points out of {}'.format(len(points))
		#counts = defaultdict(int)
		counts = defaultdict(list)

		#filter_freq = filter_range('frequency', kw['frequency'], 2000)



		xs = [x['timestamp'] for x in points]
		histo = histogram(xs, bins=(24 * 60))
		print 'Calculated histogram'

		print '*****************************************'
		print 'Reporting on histogram!'
		print 'histo0:', histo[0]
		print 'histo1:', histo[1]

		inds = [x for x in range(len(histo[0])) if histo[0][x] > 500]
		print 'Got {} high value buckets!'.format(len(inds))
		print '*****************************************'

		bad_points = set()

		enable_prefiltering = True
		if enable_prefiltering:
			print 'Performing prefiltering'
		else:
			print 'WARNING: Prefiltering disabled. Are you sure about this?'

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

		filter_band3 = filter_values_over('band3', THRESHOLD_BAND3)

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

		filter_band10 = filter_values_over('band10', THRESHOLD_BAND10)

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
		print 'type is:', bad_ids[0].__class__
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
		print '|counts| = {}'.format(len(counts))
		for (k, v) in counts.items()[:10]:
			print 'count {} -> {}'.format(k, v)
		return counts, good_points

	def get_bad_points(self, ids, **kw):
		global current_count
		#if current_count == 1:
			#assert False
		#else:
			#current_count += 1
		points = [x for x in self.points if x['ID'] in ids]
		print 'Got {} points that are about to be categorized'.format(len(points))
		print 'get_bad_points() -> get_matching_points()'

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

def filter_values_over(field_name, threshold):
	def filter_func(point, points):
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
