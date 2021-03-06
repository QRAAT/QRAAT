# est.py - Structure for processing .det files. Output to file 
# (.qraat.csv.csv) or database. This file is part of QRAAT, an automated 
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
# 
# TODO 
#  - Deal with legacy headers in reading .csv files. 

import qraat
import sys, os, time, errno
import numpy as np
from string import Template

# Some SQL queries. 

query_insert_est = Template(
  '''INSERT INTO est 
       (siteid, timestamp, frequency, center, fdsp, 
        fd1r, fd1i, fd2r, fd2i, fd3r, fd3i, fd4r, fd4i, 
        band3, band10, edsp, 
        ed1r, ed1i, ed2r, ed2i, ed3r, ed3i, ed4r, ed4i, 
        ec, tnp, 
        nc11r, nc11i, nc12r, nc12i, nc13r, nc13i, nc14r, nc14i, 
        nc21r, nc21i, nc22r, nc22i, nc23r, nc23i, nc24r, nc24i, 
        nc31r, nc31i, nc32r, nc32i, nc33r, nc33i, nc34r, nc34i, 
        nc41r, nc41i, nc42r, nc42i, nc43r, nc43i, nc44r, nc44i, 
        fdsnr, edsnr, deploymentID)
      VALUE 
       ($siteid, $timestamp, $frequency, $center, $fdsp, 
        $fd1r, $fd1i, $fd2r, $fd2i, $fd3r, $fd3i, $fd4r, $fd4i, 
        $band3, $band10, $edsp, 
        $ed1r, $ed1i, $ed2r, $ed2i, $ed3r, $ed3i, $ed4r, $ed4i, 
        $ec, $tnp, 
        $nc11r, $nc11i, $nc12r, $nc12i, $nc13r, $nc13i, $nc14r, $nc14i, 
        $nc21r, $nc21i, $nc22r, $nc22i, $nc23r, $nc23i, $nc24r, $nc24i, 
        $nc31r, $nc31i, $nc32r, $nc32i, $nc33r, $nc33i, $nc34r, $nc34i, 
        $nc41r, $nc41i, $nc42r, $nc42i, $nc43r, $nc43i, $nc44r, $nc44i, 
        $fdsnr, $edsnr, $txid)''')

query_update_est = Template( 
  '''UPDATE est SET
      siteid=$siteid, timestamp=$timestamp, 
      frequency=$frequency, center=$center, fdsp=$fdsp,
      fd1r=$fd1r, fd1i=$fd1i, fd2r=$fd2r, fd2i=$fd2i, fd3r=$fd3r, fd3i=$fd3i, fd4r=$fd4r, fd4i=$fd4i, 
      band3=$band3, band10=$band10, edsp=$edsp, 
      ed1r=$ed1r, ed1i=$ed1i, ed2r=$ed2r, ed2i=$ed2i, ed3r=$ed3r, ed3i=$ed3i, ed4r=$ed4r, ed4i=$ed4i, 
      ec=$ec, tnp=$tnp, 
      nc11r=$nc11r, nc11i=$nc11i, nc12r=$nc12r, nc12i=$nc12i, nc13r=$nc13r, nc13i=$nc13i, nc14r=$nc14r, nc14i=$nc14i, 
      nc21r=$nc21r, nc21i=$nc21i, nc22r=$nc22r, nc22i=$nc22i, nc23r=$nc23r, nc23i=$nc23i, nc24r=$nc24r, nc24i=$nc24i, 
      nc31r=$nc31r, nc31i=$nc31i, nc32r=$nc32r, nc32i=$nc32i, nc33r=$nc33r, nc33i=$nc33i, nc34r=$nc34r, nc34i=$nc34i, 
      nc41r=$nc41r, nc41i=$nc41i, nc42r=$nc42r, nc42i=$nc42i, nc43r=$nc43r, nc43i=$nc43i, nc44r=$nc44r, nc44i=$nc44i, 
      fdsnr=$fdsnr, edsnr=$edsnr, deploymentID=$txid
     WHERE ID=$ID''')


class est (qraat.csv.csv):

  """ 
  
    Encapsulation of pulses in signal space. Store the signal features 
    calculated by :class:`qraat.det.det` in a table mirroring the database 
    schema. This class serves as an interface between pulse records (.det 
    files), the MySQL database, and can read/write its contents from/to file. 
    Some example usage:  

      * | Read a directory of pulse records from disk and dump into database. 
        | ``e = qraat.est.est(dets=qraat.det.det.read_dir('det_files/site1/1998/12/04/21/34'))``
        | ``e.write_db(db_con, site='site1')``
      * | Read the last hour of ests in database and output to file. 
        | ``f = qraat.est.est()``
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

    qraat.csv.csv.__init__(self)  
    self.txid_index = self.siteid_index = None

    # TODO deal with 'datetime' (before 'timestamp')  and 'timezone' (before 'txid') in old est archives. 
    # NOTE deploymentID called txid for legacy reasons. 
    headers = [ 'ID', 'siteid', 'timestamp', 'frequency', 'center', 'fdsp', 
                     'fd1r', 'fd1i', 'fd2r', 'fd2i', 'fd3r', 'fd3i', 'fd4r', 'fd4i', 
                     'band3', 'band10', 'edsp', 
                     'ed1r', 'ed1i', 'ed2r', 'ed2i', 'ed3r', 'ed3i', 'ed4r', 'ed4i', 
                     'ec', 'tnp', 
                     'nc11r', 'nc11i', 'nc12r', 'nc12i', 'nc13r', 'nc13i', 'nc14r', 'nc14i', 
                     'nc21r', 'nc21i', 'nc22r', 'nc22i', 'nc23r', 'nc23i', 'nc24r', 'nc24i', 
                     'nc31r', 'nc31i', 'nc32r', 'nc32i', 'nc33r', 'nc33i', 'nc34r', 'nc34i', 
                     'nc41r', 'nc41i', 'nc42r', 'nc42i', 'nc43r', 'nc43i', 'nc44r', 'nc44i', 
                     'fdsnr', 'edsnr', 'txid', 
                     'tagname', 'fn' ]

    lengths = self._csv__build_header(headers)
    self._csv__build_row_template(lengths)

    if fn: 
      self.read(fn, build_header=False)#This only works if the file has the same headers as above

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
  
    fds = {} # tagname -> file descriptor index

    for row in self.table:
      fd = fds.get(row.tagname)
      if not fd:
        fn = '%s/%s.csv' % (base_dir, row.tagname)
        if os.path.isfile(fn):
          fds[row.tagname] = fd = open(fn, 'a')
        else: 
          fds[row.tagname] = fd = open(fn, 'w')
          fd.write(','.join(self.headers) + '\n')
          
      fd.write( 
        ','.join(qraat.csv.pretty_printer(getattr(row, col))
          for col in self.headers) + '\n')

  
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
    new_row.timestamp = det.time
    new_row.frequency = det.freq
    new_row.center    = det.ctr_freq
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

    if new_row.tagname[:2] == "ID":
      new_row.txid = int(new_row.tagname[2:])
    else:
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

    cur = db_con.cursor()

    # Select pulses produced over the specified range and populate table. 
    cur.execute('''SELECT *
                     FROM est 
                    WHERE (%f <= timestamp) AND (timestamp <= %f)''' % (i, j))
    for row in cur.fetchall():
      new_row = self.Row()
      for j in range(len(row)):
        setattr(new_row, cur.description[j][0], row[j])
      new_row.tagname = 'ID' + new_row.txid
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

    if row.txid is None: 
      if self.txid_index is None: 
        cur.execute('''SELECT deployment.ID, tx.name FROM tx 
                         JOIN deployment ON deployment.txID = tx.ID''')
        self.txid_index = { name : id for (id, name) in cur.fetchall() }
      try:
        row.txid = self.txid_index[row.tagname]
      except KeyError:
        raise qraat.error.ResolveIdError('txid',row.tagname,row.fn)  

    if row.siteid is None:
      if self.siteid_index is None: 
        cur.execute('SELECT id, name FROM site')
        self.siteid_index = { name : id for (id, name) in cur.fetchall() }
      try:
        row.siteid = self.siteid_index[site]
      except KeyError:
        raise qraat.error.ResolveIdError('siteid',site,row.fn)

    query = query_insert_est if row.ID is None else query_update_est
    # When the template string performs the substitution, it casts 
    # floats to strings with `str(val)`. This rounds the decimal 
    # value if the string is too long. This screws with our precision 
    # for the timestamp. The following line turns the timestamp into 
    # a string with unrounded value. 
    row.timestamp = repr(row.timestamp) 
    cur.execute(query.substitute(row))


if __name__=="__main__":

  import MySQLdb as mdb

  try:
    db_con = mdb.connect('localhost', 'root', 'woodland', 'qraat')

    guy = est()
    guy.read_db(db_con, 1376420800.0, 1376427800.0)
    print np.array( [
      [ np.complex(guy[23].nc11r, guy[23].nc11i), 
        np.complex(guy[23].nc12r, guy[23].nc12i), 
        np.complex(guy[23].nc13r, guy[23].nc13i), 
        np.complex(guy[23].nc14r, guy[23].nc14i) ],
      [ np.complex(guy[23].nc21r, guy[23].nc21i), 
        np.complex(guy[23].nc22r, guy[23].nc22i), 
        np.complex(guy[23].nc23r, guy[23].nc23i), 
        np.complex(guy[23].nc24r, guy[23].nc24i) ],
      [ np.complex(guy[23].nc31r, guy[23].nc31i), 
        np.complex(guy[23].nc32r, guy[23].nc32i), 
        np.complex(guy[23].nc33r, guy[23].nc33i), 
        np.complex(guy[23].nc34r, guy[23].nc34i) ],
      [ np.complex(guy[23].nc41r, guy[23].nc41i), 
        np.complex(guy[23].nc42r, guy[23].nc42i), 
        np.complex(guy[23].nc43r, guy[23].nc43i), 
        np.complex(guy[23].nc44r, guy[23].nc44i) ],
        ] )

    fella = est2(db_con, 1376420800.0, 1376427800.0)
    print fella.nc[23]


  except mdb.Error, e:
    print sys.stderr, "error (%d): %s" % (e.args[0], e.args[1])
    sys.exit(1) 
