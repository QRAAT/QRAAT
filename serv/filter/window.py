import bisect
import collections
import math
import numpy


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

	def get_property_for_point(self, point, prop):
		for window in self.windows:
			lower, upper = window.get_bounds()
			#print 'Checking {} against window ({}, {})'.format(point, lower, upper)
			if upper is None:
				assert point >= lower
				return window.attributes[prop]
			else:
				if point >= lower and point < upper:
					return window.attributes[prop]
		assert False

	def get_window_count(self):
		if len(self.points) == 0:
			return 0
		((min_x, min_id), (max_x, max_id)) = self.points[0], self.points[-1]
		total_range = max_x - min_x

		interval_window_count = int(math.ceil(total_range / self.window_size))
		return interval_window_count

	def get_window_for_point(self, point, offset=0):
		# Return the Window object of index i+offset, where i is the index of
		# the window within which point falls.
		for window in self:
			if point in window:
				# found the window
				pass
			w = window.get_window_for_point(point, offset=-1)

	def init_windows(self):
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
		t_start = self.points[self.start_ind][0]
		t_end = self.points[self.end_ind][0]

		print 'performing contains {}...{}...{}'.format(v, t_start, t_end)
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
