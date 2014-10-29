import qraat, qraat.srv
import MySQLdb as mdb
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as pp
from scipy.optimize import curve_fit
import os, sys, time
import pickle

for EST_SCORE_THRESHOLD in map(lambda(x) : float(x), sys.argv[1:]):

  print "Reading result%0.2f" % EST_SCORE_THRESHOLD
  (X, Y, pos, neg) = pickle.load(open('result%0.2f' % EST_SCORE_THRESHOLD))
  extent = [0.0, 4.0, 
            0.0, 0.2]

  C_p = 2 
  C_n = 1
  tradeoff = np.zeros(pos.shape)
  for i in range(X.shape[0]):
    for j in range(Y.shape[0]):
      tradeoff[j,i] = abs((C_p * pos[j,i]) - (C_n * neg[j,i]))

  opt = []
  for i in range(X.shape[0]):
    opt.append(Y[-np.argmin(tradeoff[:,i])])

  Y = np.array(opt)
  print "Optimal trade-off:\n", Y 


  # Fit a curve to the optimal false positive / negative trade-off. 
  class F:

    def __call__(self, x, a, b, c): 
      return (a / (x + b)) + c

    def inverse(self, y, a, b, c):
      return (a / (y - c)) - b 

    def get(self, popt):
      return "lambda(x) : (%0.4f / (x + %0.4f)) + %0.4f" % tuple(popt)

  try: 
    f = F()
    popt, pcov = curve_fit(f.__call__, X, Y)
    print "SCORE_ERROR =", f.get(popt)
  except RuntimeError: 
    f = None
    print "SCORE_ERROR = no fit" 

  coeff = np.polyfit(X, Y, 6)
  p = np.poly1d(coeff) 
  print "SCORE_ERROR = np.poly1d(%s)" % map(lambda x : round(x, 5), list(coeff))
  #print "p(0) = %0.4f" % p(0)
  #print "p(1) = %0.4f" % p(1)
  #print "p(2) = %0.4f" % p(2)
  #print "p(3) = %0.4f" % p(3)
  #print "p(4) = %0.4f" % p(4)
  print

  # False positives
  pp.imshow(pos, extent=extent, aspect='auto', interpolation='nearest')
  pp.plot(X, Y, 'wo', label='Optimal trade-off')
  pp.plot(X, p(X), 'k-', label="Fitted curve")
  if f: pp.plot(X, f(X, *popt), 'k.', label="Fitted curve")
  fig = pp.gcf()
  fig.set_size_inches(16,12)
  cb = pp.colorbar()
  cb.set_label("Total")
  pp.savefig('false_positives_%0.2f.png' % EST_SCORE_THRESHOLD)
  pp.title("Frequency of false positives (threshold = %0.2f" % EST_SCORE_THRESHOLD)
  pp.xlabel("Variation")
  pp.ylabel("Score error")
  pp.clf()

  # False negatives
  pp.imshow(neg, extent=extent, aspect='auto', interpolation='nearest')
  pp.plot(X, Y, 'wo', label='Optimal trade-off')
  pp.plot(X, p(X), 'k-', label="Fitted curve")
  if f: pp.plot(X, f(X, *popt), 'k.', label="Fitted curve")
  fig = pp.gcf()
  fig.set_size_inches(16,12)
  cb = pp.colorbar()
  cb.set_label("Total")
  pp.savefig('false_negatives_%0.2f.png' % EST_SCORE_THRESHOLD)
  pp.title("Frequency of false negatives (threshold = %0.2f" % EST_SCORE_THRESHOLD)
  pp.xlabel("Variation")
  pp.ylabel("Score error")
  pp.clf()

  # Trade-off space
  pp.imshow(tradeoff, extent=extent, aspect='auto', interpolation='nearest')
  pp.plot(X, Y, 'wo', label='Optimal trade-off')
  pp.plot(X, p(X), 'k-', label="Fitted curve")
  if f: pp.plot(X, f(X, *popt), 'k.', label="Fitted curve")
  fig = pp.gcf()
  fig.set_size_inches(16,12)
  cb = pp.colorbar()
  cb.set_label("Total")
  pp.savefig('tradeoff_%0.2f.png' % EST_SCORE_THRESHOLD)
  pp.title("Tradeo off space (threshold = %0.2f" % EST_SCORE_THRESHOLD)
  pp.xlabel("Variation")
  pp.ylabel("Score error")
  pp.clf()
