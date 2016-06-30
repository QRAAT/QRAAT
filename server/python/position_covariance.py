
#TODO import statements

# Paramters for bootstrap covariance estimation. 
BOOT_MAX_RESAMPLES = 200
BOOT_CONF_LEVELS = [0.68, 0.80, 0.90, 0.95, 0.997]


### class PositionEstimator. ##################################################

class PositionError (Exception): 
  value = 0; msg = ''
  def __str__(self): return '%s (%d)' % (self.msg, self.value)

class SingularError (PositionError):
  value = 2
  msg = 'covariance matrix is singular.'

class PosDefError (PositionError): 
  value = 3
  msg = 'covariance matrix is positive definite.'

class BootstrapError (PositionError): 
  value = 4
  msg = 'not enough samples to perform boostrap.'


#TODO impliment the correct calls to agragate spectrum
if False:
  if ENABLE_BOOTSTRAP3 or ENABLE_ASYMPTOTIC: 
    all_splines = {}
  else: all_splines = None

  if ENABLE_BOOTSTRAP or ENABLE_BOOTSTRAP2:
    sub_splines = {}
  else: sub_splines = None



def CovarianceEstimator(pos, sites, max_resamples=BOOT_MAX_RESAMPLES):  
  ''' Compute covariance of each position in `pos`. 

    Inputs:
      
      pos -- list of `class position.Position` instances. 

      sites -- mapping of siteIDs to receiver locations. 

      max_resamples -- a paramter of the bootstrap covariance estimate, the 
                       number of times to resample from the data. 

    Returns a list of `position.BootstrapCovariance` instances. 
  ''' 
  cov = []
  for P in pos:
    C = BootstrapCovariance3(P, sites, max_resamples)
    cov.append(C)
  return cov

def ReadCovariances(db_con, dep_id, t_start, t_end):
  ''' Read covariances from the database. 
  
    Return a list of `class position.Covariance` instances. 
  ''' 
  cur = db_con.cursor()
  cur.execute('''SELECT status, method, 
                        cov11, cov12, cov21, cov22,
                        w99, w95, w90, w80, w68,
                        easting, northing
                   FROM covariance
                   JOIN position as p ON p.ID = positionID
                  WHERE deploymentID = %s
                    AND timestamp >= %s
                    AND timestamp <= %s
                  ORDER BY timestamp ASC''', (dep_id, t_start, t_end))
  cov = []
  for row in cur.fetchall():
    if row[1] == 'boot':
      C = BootstrapCovariance()
    elif row[2] == 'boot2': 
      C = BootstrapCovariance2()
    if row[0] == 'ok':
      C.C = np.array([[row[2], row[3]], 
                      [row[4], row[5]]])
      C.W[0.997] = row[6]
      C.W[0.95] = row[7]
      C.W[0.90] = row[8]
      C.W[0.80] = row[9]
      C.W[0.68] = row[10]
    C.p_hat = np.complex(row[12], row[11])
    C.status = row[0]
    cov.append(C)
  return cov
  

def ReadConfidenceRegions(db_con, dep_id, t_start, t_end, conf_level): 
  ''' Read confidence regions from the database. 
    
    Input: 
      
      conf_level -- a number in [0 .. 1] (see `position.BOOT_CONF_LEVELS` for 
                    valid choices) giving the desired confidence level. 
                    
    Returns a list of `class position.Ellipse` instances. If the covariance 
    is singular or not positive definite, `None` is given instead.   
  '''
  cur = db_con.cursor()
  cur.execute('''SELECT status, method, 
                        alpha, lambda1, lambda2, w{0},
                        easting, northing
                   FROM covariance
                   JOIN position as p ON p.ID = positionID
                  WHERE deploymentID = %s
                    AND timestamp >= %s
                    AND timestamp <= %s'''.format(int(100*conf_level)), 
                      (dep_id, t_start, t_end))
  conf = []
  for row in cur.fetchall():
    if row[0] == 'ok': 
      alpha = row[2]
      lambda1 = row[3]
      lambda2 = row[4] 
      Qt = row[5]
      p_hat = np.complex(row[7], row[6])
      axes = np.array([np.sqrt(Qt * lambda1), 
                       np.sqrt(Qt * lambda2)])
      E = Ellipse(p_hat, alpha, axes)
      conf.append(E)
    else: conf.append(None)
  return conf

### class Ellipse. ###################################################

class Ellipse:

  def __init__(self, p_hat, angle, axes, half_span=0, scale=1):
    ''' Representation of an ellipse. 
    
      A confidence region for normally distributed data. 
      
      Input: 
      
        p_hat -- UTM position estimate represented as a complex number. This is the
                 center of the ellipse. 

        angle -- orientation of the ellipse, represented as the angle (in radians, 
                 where 0 indicates east) between the x-axis and the major axis.

        axes -- vector of length 2: `axes[0]` is half the length of the major axis 
                and `axes[1]` is half the length of the minor axis. 

        half_span, scale -- if the ellipse is to be scaled in a weird way.
      ''' 
    self.p_hat = p_hat
    self.angle = angle
    self.axes = axes
    self.half_span = half_span
    self.scale = scale
    self.x = np.array([half_span, half_span])

  def area(self):
    ''' Return the area of the ellipse. ''' 
    return np.pi * self.axes[0] * self.axes[1] 

  def eccentricity(self):
    ''' Return the eccentricity of the ellipse. ''' 
    return np.sqrt(1 - ((self.axes[1]/2)**2) / ((self.axes[0]/2)**2))

  def cartesian(self): 
    ''' Convert the ellipse to (x,y) coordinates. ''' 
    theta = np.linspace(0,2*np.pi, 360)
    X = self.x[0] + self.axes[0]*np.cos(theta)*np.cos(self.angle) - \
                    self.axes[1]*np.sin(theta)*np.sin(self.angle)
    Y = self.x[1] + self.axes[0]*np.cos(theta)*np.sin(self.angle) + \
                    self.axes[1]*np.sin(theta)*np.cos(self.angle)
    return (X, Y)

  def __contains__(self, p):
    ''' Return `True` if the ellipse contains the point. 

      Input: p -- UTM position represented as a complex number.
    '''
    x = transform_coord(p, self.p_hat, self.half_span, self.scale)
    R = np.array([[ np.cos(self.angle), np.sin(self.angle) ],
                  [-np.sin(self.angle), np.cos(self.angle) ]])   
    y = np.dot(R, x - self.x)
    return ((y[0] / self.axes[0])**2 + (y[1] / self.axes[1])**2) <= 1 

  def display(self, p_known=None):
    ''' Ugly console renderring of confidence region. ''' 
    X, Y = self.cartesian()
    X = map(lambda x: int(x), X)
    Y = map(lambda y: int(y), Y)
    self.contour = set(zip(list(X), list(Y)))
    if p_known is not None:
      x_known = transform_coord(p_known, self.p_hat, self.half_span, self.scale)
    else:
      x_known = None
    dim = 20
    for i in range(-dim, dim+1):
      for j in range(-dim, dim+1):
        x = self.x + np.array([i,j])
        if x_known is not None and x[0] == x_known[0] and x[1] == x_known[1]: print 'C', 
        elif x[0] == self.x[0] and x[1] == self.x[1]: print 'P', 
        elif tuple(x) in self.contour: print '.',
        else: print ' ',
      print 

  def plot(self, fn, p_known=None):
    ''' A pretty plot of confidence region. ''' 
    pp.rc('text', usetex=True)
    pp.rc('font', family='serif')
    
    fig = pp.gcf()
    x_hat = self.x
 
    ax = fig.add_subplot(111)
    ax.axis('equal')

    #(x_fit, y_fit) = fit_contour(x, y, N=10000)
    X = np.vstack(self.cartesian())
    pp.plot(X[0,:], X[1,:], color='k')

    # Major, minor axes
    D = (lambda d: np.sqrt(
          (d[0] - x_hat[0])**2 + (d[1] - x_hat[1])**2))(X)
    x_major = X[:,np.argmax(D)]
    x_minor = X[:,np.argmin(D)]
    pp.plot([x_hat[0], x_major[0]], [x_hat[1], x_major[1]], '-', label='major $\sqrt{\lambda_1 Q_\gamma}$')
    pp.plot([x_hat[0], x_minor[0]], [x_hat[1], x_minor[1]], '-', label='minor $\sqrt{\lambda_2 Q_\gamma}$')

    #x_hat
    pp.plot(x_hat[0], x_hat[1], color='k', marker='o')
    pp.text(x_hat[0]-1.25, x_hat[1]-0.5, '$\hat{\mathbf{x}}$', fontsize=18)
      
    # x_known
    offset = 0.5
    if p_known:
      x_known = transform_coord(p_known, self.p_hat, self.half_span, self.scale)
      pp.plot([x_known[0]], [x_known[1]],  
              marker='o', color='k', fillstyle='none')
      pp.text(x_known[0]+offset, x_known[1]-offset, '$\mathbf{x}^*$', fontsize=18)
    
    ax.set_xlabel('easting (m)')
    ax.set_ylabel('northing (m)')
    pp.legend(title="Axis length")
    pp.savefig(fn, dpi=150, bbox_inches='tight')
    pp.clf()



### Covariance. ###############################################################

class likelihood_function:
  def __init__(self, sites, splines):
    self.sites = sites
    self.splines = splines

  def evaluate(self, x):
    ''' Compute the likelihood of position `x`. ''' 
    likelihood = 0
    for siteID in self.splines.keys():
      bearing = np.angle(x - self.sites[siteID]) * 180 / np.pi
      likelihood += self.splines[siteID](bearing)
    return likelihood



class Covariance:
  
  def __init__(self, *args, **kwargs):
    ''' Asymptotic covariance of position estimate. 

      If arguments are provided, then `position.Covariance.calc()` is called. 
    '''
    self.method = 'asym'
    self.p_hat = None
    self.half_span = None
    self.scale = None
    self.m = None
    self.C = None

    if len(args) >= 2: 
      self.calc(*args, **kwargs)
  
  def calc(self, pos, sites, p_known=None, half_span=75, scale=0.5):
    ''' Confidence region from asymptotic covariance. 
    
      Note that this expression only works if the `NORMALIZE_SPECTRUM` flag at the
      top of this program is set to `True`. 
    ''' 
    assert NORMALIZE_SPECTRUM
    assert ENABLE_ASYMPTOTIC
  
    self.p_hat = pos.p
    self.half_span = half_span
    self.scale = scale
    n = sum(map(lambda l : len(l), pos.sub_splines.values())) 
    self.m = n / pos.num_sites
  
    if p_known:
      p = p_known
    else: 
      p = pos.p
    x = np.array([half_span, half_span])
   
    likelihood = likelihood_function(sites, pos.splines)

    # Hessian
    #(positions, likelihoods) = compute_likelihood_grid(
    #                         sites, pos.splines, p, scale, half_span)
    #J = lambda (x) : likelihoods[x[0], x[1]]
    H = nd.Hessian(likelihood.evaluate)(p)
    A = np.linalg.inv(H)

    # Gradient TODO TAB
    B = np.zeros((2,2), dtype=np.float64)
    for i in range(self.m):
      splines = { id : p[i] for (id, p) in pos.all_splines.iteritems() }
      likelihood = likelihood_function(sites, splines)
      #(positions, likelihoods) = compute_likelihood_grid(
      #                         sites, splines, p, scale, half_span)
      #J = lambda (x) : likelihoods[x[0], x[1]]
      b = np.array([nd.Gradient(likelihood.evaluate)(x)]).T
      B += np.dot(b, b.T)
    B = B / self.m
    
    self.C = np.dot(A, np.dot(B, A))

  def __getitem__(self, index):
    ''' Return an element of the covariance matrix. ''' 
    return self.C[index]

  def conf(self, level): 
    ''' Emit confidence interval at the (1-conf_level) significance level. ''' 
    Qt = scipy.stats.chi2.ppf(level, 2) 
    (angle, axes) = compute_conf(self.C, 2 * Qt / self.m, 1) 
    return Ellipse(self.p_hat, angle, axes, 0, 1)


class BootstrapCovariance (Covariance):

  def __init__(self, *args, **kwargs):
    ''' Bootstrap method for estimating covariance of a position estimate. 

      If arguments are provided, then `position.BootstrapCovariance.calc()` is 
      called.
    '''
    self.method = 'boot'
    self.C = None
    self.W = {}
    self.p_hat = None
    if len(args) >= 2: 
      self.calc(*args, **kwargs)
 

  def calc(self, pos, sites, max_resamples=BOOT_MAX_RESAMPLES):
    '''  Bootstrap estimation of covariance. 

      Generate at most `max_resamples` position estimates by resampling the signals used
      in computing `pos`.

      Inputs:
          
        pos -- instance of `class position.Position`. 

        sites -- mapping of siteIDs to positions of receivers. 

        max_resamples -- number of times to resample the data.
    '''
    assert ENABLE_BOOTSTRAP
    self.p_hat = pos.p

    # Generate sub samples.
    P = np.array(bootstrap_resample_sites(pos, sites, 
                                  max_resamples, pos.objective_function, pos.splines.keys()))
    if len(P) > 0:  
      A = np.array(P[len(P)/2:])
      B = np.array(P[:len(P)/2])
     
      # Estimate covariance. 
      self.C = np.cov(np.imag(A), np.real(A))
      n = sum(map(lambda l : len(l), pos.sub_splines.values())) 
      self.m = float(n) / pos.num_sites
      
      # Mahalanobis distance of remaining estimates. 
      try: 
        W = []
        D = np.linalg.inv(self.C)
        p_bar = np.mean(B)
        x_bar = np.array([p_bar.imag, p_bar.real])
        x_hat = np.array([pos.p.imag, pos.p.real])
        for x in map(lambda p: np.array([p.imag, p.real]), iter(B)): 
          y = x - x_bar
          w = np.dot(np.transpose(y), np.dot(self.m * D, y)) 
          W.append(w)
       
        # Store just a few distances. 
        W = np.array(sorted(W))
        self.W = {}
        for level in BOOT_CONF_LEVELS:
          self.W[level] = W[int(len(W) * level)] * 2
        self.status = 'ok'
      
      except np.linalg.linalg.LinAlgError: # Singular 
        self.status = 'singular'

    else: # not enough samples
      self.status = 'undefined'

  def insert_db(self, db_con, pos_id): 
    ''' Insert covariance into the database. 
    
      Input: 

        pos_id -- positionID, serial identifier of position estimate in 
                  the database. 
    '''
    if self.status == 'ok':
      
      cov11, cov12, cov21, cov22 = self.C[0,0], self.C[0,1], self.C[1,0], self.C[1,1]
      w99, w95, w90, w80, w68 = (
             self.W[0.997], self.W[0.95], self.W[0.90], self.W[0.80], self.W[0.68])
    
      w, v = np.linalg.eig(self.C)
      if w[0] > 0 and w[1] > 0: # Positive definite. 

        i = np.argmax(w) # Major w[i], v[:,i]
        j = np.argmin(w) # Minor w[i], v[:,j]

        alpha = np.arctan2(v[:,i][1], v[:,i][0]) 
        lambda1 = w[i]
        lambda2 = w[j]
        self.status = 'ok'

      else: 
        alpha = lambda1 = lambda2 = None
        self.status = 'nonposdef'

    else: 
      cov11, cov12, cov21, cov22 = None, None, None, None
      w99, w95, w90, w80, w68 = None, None, None, None, None
      alpha = lambda1 = lambda2 = None
  
    cur = db_con.cursor()
    cur.execute('''INSERT INTO covariance
                   (positionID, status, method, 
                    cov11, cov12, cov21, cov22,
                    lambda1, lambda2, alpha, 
                    w99, w95, w90, w80, w68)
                 VALUES (%s, %s, %s, 
                         %s, %s, %s, %s, 
                         %s, %s, %s, 
                         %s, %s, %s, %s, %s)''', 
            (pos_id, self.status, self.method,
             cov11, cov12, cov21, cov22,
             lambda1, lambda2, alpha, 
             w99, w95, w90, w80, w68))
    return cur.lastrowid
      
  def conf(self, level): 
    ''' Emit confidence interval at the (1-conf_level) significance level. ''' 
    if self.status == 'ok':
      Qt = self.W[level] 
      (angle, axes) = compute_conf(self.C, Qt, 1) 
      return Ellipse(self.p_hat, angle, axes, 0, 1)
    elif self.status == 'singular':
      raise SingularError
    elif self.status == 'undefined':
      raise BootstrapError


class BootstrapCovariance2 (BootstrapCovariance):

  def __init__(self, *args, **kwargs):
    ''' Bootstrap method originally proposed by the stats group.

      Resample by using pairs of sites to compute estimates. 
    '''
    self.method = 'boot2'
    self.C = None
    self.W = {}
    self.p_hat = None
    if len(args) >= 2: 
      self.calc(*args, **kwargs)

  def calc(self, pos, sites, max_resamples=BOOT_MAX_RESAMPLES):
    assert ENABLE_BOOTSTRAP2
    self.p_hat = pos.p

    # Generate sub samples.
    P = np.array(bootstrap_resample(pos, sites, max_resamples, pos.objective_function))
    
    if len(P) > 0: 
      A = np.array(P[len(P)/2:])
      B = np.array(P[:len(P)/2])
      
      # Estimate covariance. 
      self.C = np.cov(np.imag(A), np.real(A)) 
      n = sum(map(lambda l : len(l), pos.sub_splines.values())) 
      self.m = float(n) / pos.num_sites
      
      # Mahalanobis distance of remaining estimates. 
      try:
        W = []
        D = np.linalg.inv(self.C)
        p_bar = np.mean(B)
        x_bar = np.array([p_bar.imag, p_bar.real])
        x_hat = np.array([pos.p.imag, pos.p.real])
        for x in map(lambda p: np.array([p.imag, p.real]), iter(B)): 
          y = x - x_bar
          w = np.dot(np.transpose(y), np.dot(D, y)) 
          W.append(w)
       
        # Store just a few distances. 
        W = np.array(sorted(W))
        self.W = {}
        for level in BOOT_CONF_LEVELS:
          self.W[level] = W[int(len(W) * level)]
        self.status = 'ok'
        
      except np.linalg.linalg.LinAlgError: # Singular 
        self.status = "singular"
    
    else: # not enough samples
      self.status = 'undefined'

class BootstrapCovariance3 (BootstrapCovariance):

  def __init__(self, *args, **kwargs):
    ''' Bootstrap method from Todd.

      Resample with replacement such that resample has same size as original. 
    '''
    self.method = 'boot3'
    self.C = None
    self.W = {}
    self.p_hat = None
    if len(args) >= 2: 
      self.calc(*args, **kwargs)

  def calc(self, pos, sites, max_resamples=BOOT_MAX_RESAMPLES):
    assert ENABLE_BOOTSTRAP3
    self.p_hat = pos.p

    # Generate sub samples.
    resampled_positions = np.array(bootstrap_case_resample(pos, sites, max_resamples, pos.objective_function))
    num_resampled_positions = len(resampled_positions)
    if num_resampled_positions > 1:
      if num_resampled_positions > 100:
        A = np.array(resampled_positions[num_resampled_positions/2:])
        B = np.array(resampled_positions[:num_resampled_positions/2])
      else:
        A = np.array(resampled_positions)
        B = np.array(resampled_positions)
      
      # Estimate covariance. 
      self.C = np.cov(np.imag(A), np.real(A)) 
      #n = sum(map(lambda l : len(l), pos.sub_splines.values())) 
      #self.m = float(n) / pos.num_sites
      
      # Mahalanobis distance of remaining estimates. 
      distances = []
      try:
        inv_C = np.linalg.inv(self.C)
      except np.linalg.linalg.LinAlgError: # Singular 
        self.status = "singular"
      else:
        p_bar = np.mean(B)
        x_bar = np.array([p_bar.imag, p_bar.real])
        for x in map(lambda p: np.array([p.imag, p.real]), iter(B)): 
          y = x - x_bar
          w = np.dot(np.transpose(y), np.dot(inv_C, y)) 
          distances.append(w)
       
        # Store just a few distances. 
        sorted_distances = np.array(sorted(distances))
        self.W = {}
        for level in BOOT_CONF_LEVELS:
          self.W[level] = sorted_distances[int(len(sorted_distances) * level)]
        self.status = 'ok'
        
          
    else: # not enough samples
      self.status = 'undefined'

def bootstrap_resample(pos, sites, max_resamples, objective_function):
  ''' Generate positionn estimates by sub sampling signal data. 

    Construct an objective function from a subset of the pulses (one pulse per site)
    and optimize over the search space. Repeat this at most `max_resamples / samples` 
    for each pair of sites where `samples` is the number of such pairs. 
  '''
  resamples = max(1, max_resamples / (pos.num_sites * (pos.num_sites - 1) / 2))
  P = []
  for site_ids in itertools.combinations(pos.splines.keys(), 2):
    P += bootstrap_resample_sites(pos, sites, resamples, objective_function, site_ids)
  random.shuffle(P)
  return P

def bootstrap_resample_sites(pos, sites, resamples, objective_function, site_ids):
  ''' Resample from a specific set of sites. ''' 
  N = reduce(int.__mul__, [1] + map(lambda S : len(S), pos.sub_splines.values()))
  if N < 2 or pos.p is None: # Number of pulse combinations
    return []

#  a = 1 if objective_function == np.argmin else -1
#  x0 = np.array([pos.p.imag, pos.p.real])
  P = []
  for i in range(resamples):
    splines = {}
    for id in site_ids:
      j = random.randint(0, len(pos.sub_splines[id])-1)
      splines[id] = pos.sub_splines[id][j]
#    f = lambda(x) : a * compute_likelihood(sites, splines, np.complex(x[1], x[0]))    
#    res = scipy.optimize.minimize(f, x0)
#    p = np.complex(res.x[1], res.x[0])
    (p, _) = compute_position(sites, splines, pos.p, objective_function,
              s=POS_EST_S, m=POS_EST_M-1, n=POS_EST_N, delta=POS_EST_DELTA) 
    P.append(p)
  return P

def bootstrap_case_resample(pos, sites, max_resamples, objective_function):
  ''' Bootstrap case resampling:
        https://en.wikipedia.org/wiki/Bootstrapping_(statistics)#Case_resampling '''


  #N = reduce(int.__mul__, [1] + map(lambda S : len(S), pos.all_splines.values()))
  if pos.p is None or pos.num_sites < 2: # Number of pulse combinations
    return []

  bootstrap_resampled_positions = []
  site_list = pos.all_splines.keys()  
  number_of_ests_dict = {}

  #number of exhaustive combinations
  N=1
  for siteid in site_list:
    number_of_ests_dict[siteid] = len(pos.all_splines[siteid])
    N *= np.math.factorial(2*number_of_ests_dict[siteid]-1)/np.math.factorial(number_of_ests_dict[siteid])/np.math.factorial(number_of_ests_dict[siteid]-1)



  if (N < max_resamples): #exhaustive search
    #combinator generator
    combinator_iter_list = []
    for siteid in site_list:
      combinator_iter_list.append(
          itertools.combinations_with_replacement(
            [ (siteid, j) for j in range(number_of_ests_dict[siteid]) ], number_of_ests_dict[siteid]
              )
                )
    combinator_generator = itertools.product(*combinator_iter_list)

    for site_spline_tuple_list in combinator_generator:
      spline_dict = {}
      for siteid in site_list:
        spline_dict[siteid] = []
      for site_spline_tuples in site_spline_tuple_list:
        for site, est_index in site_spline_tuples:
          spline_dict[site].append(pos.all_splines[site][est_index])
      (p, _) = compute_position(sites, spline_dict, pos.p, objective_function,
              s=POS_EST_S, m=POS_EST_M-1, n=POS_EST_N, delta=POS_EST_DELTA)#FIXME
      bootstrap_resampled_positions.append(p)

    
  else: #monte carlo
    #combo_pool = tuple(combinator_generator)
    number_of_combos = N#len(combo_pool)
    
    uniqueness_dict = {}
    for j in range(max_resamples):
      spline_dict = {}
      for site in site_list:
        spline_dict[site] = []

      unique = False
      while not unique:
        #pick random sample
        current_combo = []
        for site in site_list:
          current_est_choices = []
          for k in range(number_of_ests_dict[site]):
            current_est_choices.append(random.randrange(number_of_ests_dict[site]))
          current_est_choices.sort()
          current_combo.append(tuple(current_est_choices))
        #test if chosen before
        if not tuple(current_combo) in uniqueness_dict:
          uniqueness_dict[tuple(current_combo)]=1
          unique = True
          

      #build splines
      for k, site in enumerate(site_list):
        est_choices = current_combo[k]
        for m in est_choices:
          spline_dict[site].append(pos.all_splines[site][m])
      #for site_spline_tuples in current_combo:#combo_pool[index]:
        #for site, est_index in site_spline_tuples:
        #  spline_dict[site].append(pos.all_splines[site][est_index])
      #compute position
      (p, _) = compute_position(sites, spline_dict, pos.p, objective_function,
              s=POS_EST_S, m=POS_EST_M-1, n=POS_EST_N, delta=POS_EST_DELTA)
      bootstrap_resampled_positions.append(p)






    #indices = sorted(random.sample(xrange(number_of_combos), max_resamples))
    #count = 0
    #current_combo = combinator_generator.next()
    #for index in indices:
    #  while count < index:
    #    count +=1
    #    current_combo = combinator_generator.next()
      
  return bootstrap_resampled_positions

def compute_conf(C, Qt, scale=1):
  ''' Compute confidence region from covariance matrix.
    
    Method due to http://www.visiondummy.com/2014/04/
      draw-error-ellipse-representing-covariance-matrix/. 
    
    C -- covariance matrix.

    Qt -- is typically the cumulative probability of `t` from the chi-square 
          distribution with two degrees of freedom. This is also the Mahalanobis
          distance in the case of the bootstrap.

    scale -- In case weird scaling was used. 
  '''
  w, v = np.linalg.eig(C)
  if w[0] > 0 and w[1] > 0: # Positive definite. 

    i = np.argmax(w) # Major w[i], v[:,i]
    j = np.argmin(w) # Minor w[i], v[:,j]

    angle = np.arctan2(v[:,i][1], v[:,i][0]) 
    x = np.array([np.sqrt(Qt * w[i]), 
                  np.sqrt(Qt * w[j])])

    axes = x * scale

  else: raise PosDefError
  
  return (angle, axes)

def transform_coord(p, center, half_span, scale):
  ''' Transform position as a complex number to some coordinate system. ''' 
  x = [int((p.imag - center.imag) / scale) + half_span,
       int((p.real - center.real) / scale) + half_span]
  return np.array(x)

def transform_coord_inv(x, center, half_span, scale):
  ''' Transform position as a complex number to some coordinate system (inverse) ''' 
  p = np.complex( (((x[1] - half_span) * scale) + center.real), 
                  (((x[0] - half_span) * scale) + center.imag) )
  return p

  
