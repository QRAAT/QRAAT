class ConfidenceRegion: 

  def __init__(self, pos, sites, significance_level=0.68, half_span=HALF_SPAN*40, scale=1, p_known=None):
    ''' Compute covariance matrix of position estimater w.r.t true location `p`. 

      Assuming the estimate follows a bivariate normal distribution. 
      This follows [ZB11] equation 2.169. 

      Return a tuple (x, alpha), where x[0] gives the magnitude of the major 
      axis, x[1]s give the magnitude of the minor axis, and alpha gives the 
      angular orientation (relative to the x-axis) of the ellipse in degrees. 
      If C is not positive definite, then the distribution has no density: 
      return (None, None). 

      Based on the blog post: http://www.visiondummy.com/2014/04/draw-error-
      ellipse-representing-covariance-matrix/ by Vincent Spruyt. Note that
      this only applies to *known* covariance, e.g. estimated from multiple
      position estimates. 

    '''
    self.p_hat = pos.p
    self.level = significance_level
    self.half_span = half_span
    self.scale = scale
  
    if p_known: 
      x = transform_coord(p_known, self.p_hat, half_span, scale)
    else: 
      x = transform_coord(self.p_hat, self.p_hat, half_span, scale)
  
    (positions, likelihoods) = compute_likelihood(
                             sites, pos.splines, self.p_hat, scale, half_span)
    
    # Obj function, Hessian matrix, and gradient vector. 
    J = lambda (x) : likelihoods[x[0], x[1]]
    H = nd.Hessian(J)
    Del = nd.Gradient(J)
   
    # Covariance of p_hat.  
    a = Del(x)
    b = np.linalg.inv(H(x))
    C = np.dot(b, np.dot(np.dot(a, np.transpose(a)), b))
  
    # Confidence interval. 
    self.e = compute_conf(self.p_hat, C, significance_level, 
                          half_span, scale, k=1) 
  
  def display(self, p_known=None):
    X, Y = self.e.cartesian()
    X = map(lambda x: int(x), X)
    Y = map(lambda y: int(y), Y)
    self.contour = set(zip(list(X), list(Y)))
    if p_known is not None:
      x_known = transform_coord(p_known, self.p_hat, self.half_span, self.scale)
    else:
      x_known = None
    fella = 20
    for i in range(-fella, fella+1):
      for j in range(-fella, fella+1):
        x = self.e.x + np.array([i,j])
        if x_known is not None and x[0] == x_known[0] and x[1] == x_known[1]: print 'C', 
        elif x[0] == self.e.x[0] and x[1] == self.e.x[1]: print 'P', 
        elif tuple(x) in self.contour: print '.',
        else: print ' ',
      print 

  def plot(self, fn, p_known=None):
    fig = pp.gcf()
    x_hat = self.e.x
  
    #(x_fit, y_fit) = fit_contour(x, y, N=10000)
    (x_fit, y_fit) = self.e.cartesian()  
    pp.plot(x_fit, y_fit, color='k', alpha=0.5)

    # x_hat
    pp.plot(x_hat[0], x_hat[1], color='k', marker='o')
    pp.text(x_hat[0]+0.25, x_hat[1]-0.25, '$\hat{\mathbf{x}}$', fontsize=24)
      
    # x_known
    if p_known:
      x_known = transform_coord(p_known, self.p_hat, self.half_span, self.scale)
      pp.plot([x_known[0]], [x_known[1]],  
              marker='o', color='k', fillstyle='none')
      pp.text(x_known[0]+0.25, x_known[1]-0.25, '$\mathbf{x}^*$', fontsize=24)
    
    pp.savefig(fn)
    pp.clf()

  
  def __contains__(self, p):
    return p in self.e
