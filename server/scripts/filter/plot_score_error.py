import qraat, qraat.srv
import MySQLdb as mdb
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as pp
import os, sys, time
import pickle

EST_SCORE_THRESHOLD = float(sys.argv[1])

(X, Y, pos, neg) = pickle.load(open('result%0.1f' % EST_SCORE_THRESHOLD))
extent = [np.min(X), np.max(X), 
          np.min(Y), np.max(Y)]


pos_norm = float(np.max(pos.flat))
neg_norm = float(np.max(neg.flat))

C_p = 2 
C_n = 1
opt = []
for i in range(len(X)):
  min_score = float("+inf")
  min_index = 0 
  for j in range(len(Y)): 
    score = (C_p * (pos[j,i] / pos_norm)) + (C_n * (neg[j,i] / neg_norm)) 
    if score < min_score:
      min_index = j
      min_score = score
  opt.append(Y[min_index])

#X = np.array(list(reversed(X)))
#opt = list(reversed(opt))

# False positives
pp.imshow(pos, extent=extent, aspect='auto', interpolation='nearest')
pp.plot(X, qraat.srv.signal.SCORE_ERROR(X), 'k-')
pp.plot(X, opt, 'wo')
fig = pp.gcf()
fig.set_size_inches(16,12)
cb = pp.colorbar()
cb.set_label("Total")
pp.savefig('false_positives_%0.1f.png' % EST_SCORE_THRESHOLD)
pp.title("Frequency of false positives (threshold = %0.1f" % EST_SCORE_THRESHOLD)
pp.xlabel("Variation")
pp.ylabel("Score error")
pp.clf()

# False negatives
pp.imshow(neg, extent=extent, aspect='auto', interpolation='nearest')
pp.plot(X, qraat.srv.signal.SCORE_ERROR(X), 'k-')
pp.plot(X, opt, 'wo')
fig = pp.gcf()
fig.set_size_inches(16,12)
cb = pp.colorbar()
cb.set_label("Total")
pp.savefig('false_negatives_%0.1f.png' % EST_SCORE_THRESHOLD)
pp.title("Frequency of false negatives (threshold = %0.1f" % EST_SCORE_THRESHOLD)
pp.xlabel("Variation")
pp.ylabel("Score error")
pp.clf()
