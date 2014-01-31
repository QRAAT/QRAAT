# est.py - Structure for holding processed .det files. Output 
# formats: .csv and .est. This file is part of QRAAT, an automated 
# animal tracking system based on GNU Radio. 
#
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

from csv import csv, pretty_printer
from det import det
import sys, os, time, errno
import numpy as np
from string import Template

try:
  import MySQLdb as mdb
except ImportError: pass

# Some SQL queries. 

query_insert_est = Template(
  '''INSERT INTO est 
       (siteid, datetime, timestamp, frequency, center, fdsp, 
        fd1r, fd1i, fd2r, fd2i, fd3r, fd3i, fd4r, fd4i, 
        band3, band10, edsp, 
        ed1r, ed1i, ed2r, ed2i, ed3r, ed3i, ed4r, ed4i, 
        ec, tnp, 
        nc11r, nc11i, nc12r, nc12i, nc13r, nc13i, nc14r, nc14i, 
        nc21r, nc21i, nc22r, nc22i, nc23r, nc23i, nc24r, nc24i, 
        nc31r, nc31i, nc32r, nc32i, nc33r, nc33i, nc34r, nc34i, 
        nc41r, nc41i, nc42r, nc42i, nc43r, nc43i, nc44r, nc44i, 
        fdsnr, edsnr, timezone, txid)
      VALUE 
       ($siteid, '$datetime', $timestamp, $frequency, $center, $fdsp, 
        $fd1r, $fd1i, $fd2r, $fd2i, $fd3r, $fd3i, $fd4r, $fd4i, 
        $band3, $band10, $edsp, 
        $ed1r, $ed1i, $ed2r, $ed2i, $ed3r, $ed3i, $ed4r, $ed4i, 
        $ec, $tnp, 
        $nc11r, $nc11i, $nc12r, $nc12i, $nc13r, $nc13i, $nc14r, $nc14i, 
        $nc21r, $nc21i, $nc22r, $nc22i, $nc23r, $nc23i, $nc24r, $nc24i, 
        $nc31r, $nc31i, $nc32r, $nc32i, $nc33r, $nc33i, $nc34r, $nc34i, 
        $nc41r, $nc41i, $nc42r, $nc42i, $nc43r, $nc43i, $nc44r, $nc44i, 
        $fdsnr, $edsnr, '$timezone', $txid)''')

query_update_est = Template( 
  '''UPDATE est SET
      siteid=$siteid, datetime='$datetime', timestamp=$timestamp, 
      frequency=$frequency, center=$center, fdsp=$fdsp,
      fd1r=$fd1r, fd1i=$fd1i, fd2r=$fd2r, fd2i=$fd2i, fd3r=$fd3r, fd3i=$fd3i, fd4r=$fd4r, fd4i=$fd4i, 
      band3=$band3, band10=$band10, edsp=$edsp, 
      ed1r=$ed1r, ed1i=$ed1i, ed2r=$ed2r, ed2i=$ed2i, ed3r=$ed3r, ed3i=$ed3i, ed4r=$ed4r, ed4i=$ed4i, 
      ec=$ec, tnp=$tnp, 
      nc11r=$nc11r, nc11i=$nc11i, nc12r=$nc12r, nc12i=$nc12i, nc13r=$nc13r, nc13i=$nc13i, nc14r=$nc14r, nc14i=$nc14i, 
      nc21r=$nc21r, nc21i=$nc21i, nc22r=$nc22r, nc22i=$nc22i, nc23r=$nc23r, nc23i=$nc23i, nc24r=$nc24r, nc24i=$nc24i, 
      nc31r=$nc31r, nc31i=$nc31i, nc32r=$nc32r, nc32i=$nc32i, nc33r=$nc33r, nc33i=$nc33i, nc34r=$nc34r, nc34i=$nc34i, 
      nc41r=$nc41r, nc41i=$nc41i, nc42r=$nc42r, nc42i=$nc42i, nc43r=$nc43r, nc43i=$nc43i, nc44r=$nc44r, nc44i=$nc44i, 
      fdsnr=$fdsnr, edsnr=$edsnr, timezone='$timezone', txid=$txid
     WHERE ID=$ID''')



class ResolveIdError (Exception):
  """ Exception class for resolving database IDs for est entries. """

  def __init__(self, row):
    self.filename = row.fn
    self.txid     = row.txid
    self.siteid   = row.siteid
     
  def __str__(self):
    return "could not resolve foreign key(s) for est table row (txid='%s', siteid='%s')" % (
      self.txid, self.siteid)


class est (csv):

  """ 
  
    Encapsulation of pulses in signal space. Store the signal features 
    calculated by :class:`qraat.det.det` in a table mirroring the database 
    schema. This class serves as an interface between pulse records (.det 
    files), the MySQL database, and can read/write its contents from/to file. 
    Some example usage:  

      * | Read a directory of pulse records from disk and dump into database. 
        | ``e = qraat.est(dets=qraat.det.read_dir('det_files/site1/1998/12/04/21/34'))``
        | ``e.write_db(db_con, site='site1')``
      * | Read the last hour of ests in database and output to file. 
        | ``f = qraat.est()``
        | ``f.read_db(db_con, time() - 3600, time())``
        | ``f.write('est_files')``

    .. note:: 
      The table doesn't maintain order constraints. 

    .. note:: 
      For ``write_db()``, we need the txid and siteid for 
      each row. The txid can be resolved with det.tag_name, but the 
      site from which the pulse was produced must be inferred from the
      directory structure at the moment. When we update the det 
      metadata, we will have tx_id and site_id be fields, but for the
      moment it's necessary to specify the name of the site where the 
      pulse was recorded. See :func:`est.write_db`. 

    :param det: A pulse record.
    :type det: qraat.det.det
    :param dets: A set of pulse records.
    :type dets: qraat.det.det 
    :param fn: Filename to read est table from. 
    :type fn: str
    
  """
    
  #: The DB schema is hard-coded to handle four channels. For this 
  #: reason, this value is also hard-coded here. 
  channel_ct = 4 

  def __init__(self, det=None, dets=None, fn=None):
  
    self.txid_index = self.siteid_index = None
    self.table = []

    self.headers = [ 'ID', 'siteid', 'datetime', 'timestamp', 'frequency', 'center', 'fdsp', 
                     'fd1r', 'fd1i', 'fd2r', 'fd2i', 'fd3r', 'fd3i', 'fd4r', 'fd4i', 
                     'band3', 'band10', 'edsp', 
                     'ed1r', 'ed1i', 'ed2r', 'ed2i', 'ed3r', 'ed3i', 'ed4r', 'ed4i', 
                     'ec', 'tnp', 
                     'nc11r', 'nc11i', 'nc12r', 'nc12i', 'nc13r', 'nc13i', 'nc14r', 'nc14i', 
                     'nc21r', 'nc21i', 'nc22r', 'nc22i', 'nc23r', 'nc23i', 'nc24r', 'nc24i', 
                     'nc31r', 'nc31i', 'nc32r', 'nc32i', 'nc33r', 'nc33i', 'nc34r', 'nc34i', 
                     'nc41r', 'nc41i', 'nc42r', 'nc42i', 'nc43r', 'nc43i', 'nc44r', 'nc44i', 
                     'fdsnr', 'edsnr', 'timezone', 'txid', 
                     'tagname', 'fn' ]

    self.Row = type('Row', (object,), { h : None for h in self.headers })
    self.Row.headers = self.headers

    def f(self):
      for h in self.headers:
         yield getattr(self, h)
    self.Row.__iter__ = f
    def g(self, i):
      return getattr(self, i)
    self.Row.__getitem__ = g

    self._row_template = "%10s " * len(self.headers)

    if fn: 
      self.read(fn)

    if det:
      self.append(det)

    if dets:
      for det in dets: 
        self.append(det)


  def write(self, base_dir='./'): 
    """ Write an est file for each transmitter.

      If file exists, than append; otherwise, create a new 
      file and write the column headers. 
      
      :param base_dir: Directory for output files. 
      :type base_dir: str
    """
    
    try: # Create target directory. 
      os.makedirs(base_dir)
    except OSError, e:
      if e.errno != errno.EEXIST: 
        raise e
  
    # Exclude some headers when writing to file. 
    headers = [col for col in self.headers if col not in [
      'ID', 'txid', 'siteid', 'timezone']]
    fds = {} # tagname -> file descriptor index

    for row in self.table:
      fd = fds.get(row.tagname)
      if not fd:
        fn = '%s/%s.csv' % (base_dir, row.tagname)
        if os.path.isfile(fn):
          fds[row.tagname] = fd = open(fn, 'a')
        else: 
          fds[row.tagname] = fd = open(fn, 'w')
          fd.write(','.join(headers) + '\n')
          
      fd.write( 
        ','.join(pretty_printer(getattr(row, col))
          for col in headers) + '\n')

  
  def append(self, det):
    """ Append pulse signal to table.

    :param det: Pulse record. 
    :type det: qraat.det.det
    """
    
    det.eig()
    det.f_signal()
    det.noise_cov()
    new_row = self.Row()
    new_row.tagname   = det.tag_name
    new_row.datetime  = time.gmtime(det.time)
    new_row.timezone  = 'UTC' #TODO Is this value always UTC? 
    new_row.timestamp = det.time
    new_row.frequency = det.freq
    new_row.center    = det.params.ctr_freq
    new_row.fn        = det.fn

    # Fourier decomposistion
    new_row.fdsp        = det.f_pwr
    det.f_sig = det.f_sig.transpose()
    for i in range(self.channel_ct): 
      setattr(new_row, 'fd%dr' % (i+1), det.f_sig[0,i].real)
      setattr(new_row, 'fd%di' % (i+1), det.f_sig[0,i].imag)
  
    new_row.band3  = det.f_bandwidth3
    new_row.band10 = det.f_bandwidth10

    # Eigenvalue decomposition 
    new_row.edsp   = det.e_pwr
    det.e_sig = det.e_sig.transpose()
    for i in range(self.channel_ct): 
      setattr(new_row, 'ed%dr' % (i+1), det.e_sig[0,i].real)
      setattr(new_row, 'ed%di' % (i+1), det.e_sig[0,i].imag)
  
    # Eigenvalue confidince
    new_row.ec  = det.e_conf

    # Noise covariance
    new_row.tnp = np.trace(det.n_cov).real  # ??
    for i in range(self.channel_ct):
      for j in range(self.channel_ct): 
        setattr(new_row, 'nc%d%dr' % (i+1, j+1), det.n_cov[i,j].real)
        setattr(new_row, 'nc%d%di' % (i+1, j+1), det.n_cov[i,j].imag)

    # Fourier decomposition signal-noise ratio (SNR)
    new_row.fdsnr = 10 * np.log10(det.f_pwr / new_row.tnp)

    # Eigenvalue decomposition SNR
    new_row.edsnr = 10 * np.log10(det.e_pwr / new_row.tnp)

    new_row.txid = None  
    new_row.siteid = None

    self.table.append(new_row)


  def clear(self): 
    """ Clear table. """
    self.table = []


  def read_db(self, db_con, i, j):
    """ Read rows from the database over the time interval ``[i, j]``. 
    
      :param db_con: DB connector for MySQL. 
      :type db_con: MySQLdb.connections.Connection
      :param i: Time start (Unix). 
      :type i: float 
      :param j: Time end (Unix).
      :type j: float
    """
    cur = db_con.cursor(mdb.cursors.DictCursor)

    # Create tagname index. 
    cur.execute('''SELECT id, name 
                     FROM txlist''')
    tagname_index = { row['id'] : row['name'] for row in cur.fetchall() }

    # Select pulses produced over the specified range and populate table. 
    cur.execute('''SELECT *
                     FROM est 
                    WHERE (%f <= timestamp) AND (timestamp <= %f)''' % (i, j))
    for row in cur.fetchall():
      new_row = self.Row()
      for (col, val) in row.iteritems():
        setattr(new_row, col, val)
      new_row.tagname = tagname_index[new_row.txid]
      self.table.append(new_row)
    
  def write_db(self, db_con, site=None):
    """ Write rows to the database and commit. 
     
      :param db_con: DB connector for MySQL. 
      :type db_con: MySQLdb.connections.Connection
      :param site: Name of the site where the signal was recorded. 
      :type site: str
    """

    cur = db_con.cursor()
    for row in self.table: 
      self.write_db_row(cur, row, site) 
    cur.execute('COMMIT')

  def write_db_row(self, cur, row, site=None):
    """ Write a row to the database. 
       
      Resolve the transmitter ID by tag name and the site ID by ``site``, 
      if these values aren't present in the table. This allows us to deal 
      with legacy pulse sample metadata. 
         
      :param cur: DB cursor for MySQL. 
      :type cur: MySQLdb.cursors.Cursor
      :param row: The row.  
      :type row: est.Row
    """

    if self.txid_index == None: 
      cur.execute('SELECT id, name FROM txlist')
      self.txid_index = { name : id for (id, name) in cur.fetchall() }

    if self.siteid_index == None: 
      cur.execute('SELECT id, name FROM sitelist')
      self.siteid_index = { name : id for (id, name) in cur.fetchall() }

    if row.txid == None: 
      row.txid = self.txid_index.get(row.tagname)

    if row.siteid == None:
      row.siteid = self.siteid_index.get(site)

    if row.txid == None or row.siteid == None:
      raise ResolveIdError(row)

    query = query_insert_est if row.ID == None else query_update_est
    # When the template string performs the substitution, it casts 
    # floats to strings with `str(val)`. This rounds the decimal 
    # value if the string is too long. This screws with our precision 
    # for the timestamp. The following line turns the timestamp into 
    # a string with unrounded value. 
    row.timestamp = repr(row.timestamp) 
    row.datetime = pretty_printer(row.datetime)
    cur.execute(query.substitute(row))


class est2:
  ''' Encapsulate pulse signal data. 
  
    I'm evaluating what functionality I want from the est object so 
    that the data is more chewable in bearing and position calculation.
    My thinking now is that this could replace est entirely and be 
    the interface between det's, DB, and file. For now, it will serve
    useful for exploring. 
  ''' 

  #: Number of channels. 
  N = 4

  def __init__(self, db_con, t_start, t_end, tx_id=None):

    # Store eigenvalue decomposition vectors and noise covariance
    # matrices in NumPy arrays. 
    cur = db_con.cursor()
    cur.execute('''SELECT ID, siteid, txid, timestamp,
                          edsp, ed1r, ed1i, ed2r, ed2i, ed3r, ed3i, ed4r, ed4i, 
                          nc11r, nc11i, nc12r, nc12i, nc13r, nc13i, nc14r, nc14i, 
                          nc21r, nc21i, nc22r, nc22i, nc23r, nc23i, nc24r, nc24i, 
                          nc31r, nc31i, nc32r, nc32i, nc33r, nc33i, nc34r, nc34i, 
                          nc41r, nc41i, nc42r, nc42i, nc43r, nc43i, nc44r, nc44i
                     FROM est
                    WHERE (%f <= timestamp) AND (timestamp <= %f) %s''' % (
                            t_start, t_end, 
                           ('AND txid=%d' % tx_id) if tx_id else ''))
  
    raw = np.array(cur.fetchall(), dtype=float)
    
    # Metadata. 
    (self.id, 
     self.site_id, 
     self.tx_id) = (np.array(raw[:,i], dtype=int) for i in range(0,3))
    self.timestamp = raw[:,3]
    raw = raw[:,5:]

    # Signal power. 
    self.edsp = raw[:,0]
    raw = raw[:,0:]

    # Signal vector, N x 1.
    self.ed = raw[:,0:8:2] + np.complex(0,-1) * raw[:,1:8:2]
    raw = raw[:,8:]

    # Noise covariance matrix, N x N. 
    self.nc = raw[:,0::2] + np.complex(0,-1) * raw[:,1::2]
    self.nc = self.nc.reshape(raw.shape[0], self.N, self.N)




if __name__=="__main__":

  try:
    db_con = mdb.connect('localhost', 'root', 'woodland', 'qraat')
    fella = est2(db_con, 1376420800.0, 1376427800.0)
    print fella.edsp

    guy = est()
    guy.read_db(db_con, 1376420800.0, 1376427800.0)
    for i in range(len(guy)):
      print guy[i].edsp

  except mdb.Error, e:
    print sys.stderr, "error (%d): %s" % (e.args[0], e.args[1])
    sys.exit(1) 
