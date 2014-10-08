import qraat, qraat.srv
import MySQLdb as mdb
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as pp
import os, sys, time
import pickle

EST_SCORE_THRESHOLD = float(sys.argv[1])

(x, y, pos, neg) = pickle.load(open('result%0.1f' % EST_SCORE_THRESHOLD))
extent = [np.min(x), np.max(x), 
          np.min(y), np.max(y)]
#extent = [x[0], x[-1], y[0], y[-1]]

#print x
#print '-------------------'
#print y
#print '-------------------'
#print pos


pp.imshow(pos, extent=extent, aspect='auto', interpolation='nearest')
pp.plot(x, qraat.srv.signal.SCORE_ERROR(x), 'w-')
fig = pp.gcf()
fig.set_size_inches(16,12)
cb = pp.colorbar()
cb.set_label("Total")
pp.savefig('false_positives_%0.1f.png' % EST_SCORE_THRESHOLD)
pp.title("Frequency of false positives (threshold = %0.1f" % EST_SCORE_THRESHOLD)
pp.xlabel("Variation")
pp.ylabel("Score error")
pp.clf()

pp.imshow(neg, extent=extent, aspect='auto', interpolation='nearest')
pp.plot(x, qraat.srv.signal.SCORE_ERROR(x), 'w-')
fig = pp.gcf()
fig.set_size_inches(16,12)
cb = pp.colorbar()
cb.set_label("Total")
pp.savefig('false_negatives_%0.1f.png' % EST_SCORE_THRESHOLD)
pp.title("Frequency of false negatives (threshold = %0.1f" % EST_SCORE_THRESHOLD)
pp.xlabel("Variation")
pp.ylabel("Score error")
pp.clf()
