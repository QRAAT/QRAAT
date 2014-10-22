import qraat, qraat.srv
import MySQLdb as mdb
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as pp
from scipy.optimize import curve_fit
import os, sys, time
import pickle

EST_SCORE_THRESHOLD = float(sys.argv[1])

(X, Y, pos, neg) = pickle.load(open('result%0.1f' % EST_SCORE_THRESHOLD))
extent = [0.0, 4.0, 
          0.0, 0.2]


pos_norm = 1#float(np.max(pos.flat))
neg_norm = 1#float(np.max(neg.flat))

C_p = 10
C_n = 1 
opt = []
for i in range(X.shape[0]):
  min_score = sys.maxint
  min_index = 0 
  for j in range(Y.shape[0]): 
    score = (C_p * (pos[j,i] / pos_norm)) + (C_n * (neg[j,i] / neg_norm)) 
    if score < min_score:
      min_index = j
      min_score = score
  opt.append(Y[min_index])

Y = np.array(opt)

# Fit a curve to the optimal false positive / negative trade-off. 
class F:

  def __call__(self, x, a, b, c): 
    return (a / (x + b)) + c

  def inverse(self, y, a, b, c):
    return (a / (y - c)) - b 

  def get(self, popt):
    return "lambda(x) : (%0.4f / (x + %0.4f)) + %0.4f" % tuple(popt)

f = F() 
popt, pcov = curve_fit(f.__call__, X, Y)

print "SCORE_ERROR =", f.get(popt)
print "Limit: %0.4f" % (0.20 - f(1000, *popt))


# False positives
pp.imshow(pos, extent=extent, aspect='auto', interpolation='nearest')
pp.plot(X, 0.2 - f(X, *popt), 'k-', label="Fitted curve")
pp.plot(X, 0.2 - Y, 'wo', label='Optimal trade-off')
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
pp.imshow(np.log(neg), extent=extent, aspect='auto', interpolation='nearest')
pp.plot(X, 0.2 - f(X, *popt), 'k-', label="Fitted curve")
pp.plot(X, 0.2 - Y, 'wo', label='Optimal trade-off')
fig = pp.gcf()
fig.set_size_inches(16,12)
cb = pp.colorbar()
cb.set_label("Total (log scale)")
pp.savefig('false_negatives_%0.1f.png' % EST_SCORE_THRESHOLD)
pp.title("Frequency of false negatives (threshold = %0.1f" % EST_SCORE_THRESHOLD)
pp.xlabel("Variation")
pp.ylabel("Score error")
pp.clf()
