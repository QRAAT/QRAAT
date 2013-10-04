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

import qraat
import sys, os, time, errno
import numpy as np
import struct
import MySQLdb as mdb
from string import Template


  
  # TODO find a better home for these queries. It was suggested 
  # that we move all of our queries to a single, controlled 
  # file. 

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


class est (qraat.csv):

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

    **NOTE**: the table doesn't maintain order constraints. 

    **NOTE**: for ``write_db()``, we need the txid and siteid for 
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
    """ Write an est file per for each transmitter. 
      
      :param base_dir: Directory for output files. 
      :type base_dir: str
    """
    
    try: # Create target directory. 
      os.makedirs(base_dir)
    except OSError as e:
      if e.errno == errno.EEXIST and os.path.isdir(base_dir): pass
      else: raise
  
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
        ','.join(qraat.pretty_printer(getattr(row, col))
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
    """ Write rows to the database. 
     
       Resolve the transmitter ID by tag name and the site ID by ``site``, 
       if these values aren't present in the table. This allows us to deal 
       with legacy pulse sample metadata. 
    
      :param db_con: DB connector for MySQL. 
      :type db_con: MySQLdb.connections.Connection
      :param site: Name of the site where the signal was recorded. 
      :type site: str
    """

    cur = db_con.cursor()
    cur.execute('''SELECT id, name 
                     FROM txlist''')
    txid_index = { name : id for (id, name) in cur.fetchall() }

    cur.execute('''SELECT id, name 
                     FROM sitelist''')
    siteid_index = { name : id for (id, name) in cur.fetchall() }

    for row in self.table: 
      if row.txid == None: 
        row.txid = txid_index.get(row.tagname)

      if row.siteid == None:
        row.siteid = siteid_index.get(site)

      if row.txid == None or row.siteid == None:
        raise ResolveIdError(row)

      query = query_insert_est if row.ID == None else query_update_est
      row.datetime = qraat.pretty_printer(row.datetime)
      cur.execute(query.substitute(row))

    cur.execute('COMMIT')




  


class data_arrays:

    """ Container class for pulses in signal space. **DEPRECATED**
    
      Store pulses in a table with their signal features. Methods 
      that should be implemented: 

    :param num_channels: number of signal channels in .det files. 
    :type num_channels: int
    :param size: (?)
    :type size: (?)
    """

    def __init__(self, num_channels, size = 0):

        self.num_channels = num_channels
        self.num_records = size

        self.tag_number  = np.ones((size,), np.int)*-1
        self.epoch_time  = np.empty((size,))
        self.center_freq = np.empty((size,))
        self.e_sig       = np.empty((size, num_channels), np.complex)
        self.e_pwr       = np.empty((size,))
        self.confidence  = np.empty((size,))
        self.f_sig       = np.empty((size, num_channels), np.complex)
        self.f_pwr       = np.empty((size,))
        self.f_bw3       = np.empty((size,))
        self.f_bw10      = np.empty((size,))
        self.freq        = np.empty((size,))
        self.n_cov       = np.empty((size, num_channels, num_channels), np.complex)

    def append(self, data):
        """ **TODO:** description required. 
        
        :param data:  
        :type data: data_arrays        
        """

        self.num_records += data.num_records

        self.tag_number  = np.hstack((self.tag_number, data.tag_number))
        self.epoch_time  = np.hstack((self.epoch_time, data.epoch_time))
        self.center_freq = np.hstack((self.center_freq, data.center_freq))
        self.e_sig       = np.vstack((self.e_sig, data.e_sig))
        self.e_pwr       = np.hstack((self.e_pwr, data.e_pwr))
        self.confidence  = np.hstack((self.confidence, data.confidence))
        self.f_sig       = np.vstack((self.f_sig, data.f_sig))
        self.f_pwr       = np.hstack((self.f_pwr, data.f_pwr))
        self.f_bw3       = np.hstack((self.f_bw3, data.f_bw3))
        self.f_bw10      = np.hstack((self.f_bw10, data.f_bw10))
        self.freq        = np.hstack((self.freq, data.freq))
        self.n_cov       = np.vstack((self.n_cov, data.n_cov))
    
    
    def add_det(self, det, tag_index, index):
        """ **TODO:** description required.

        :param det: Pulse data record. 
        :type det: qraat.det.det
        :param tag_index: what is this(?) 
        :type tag_index: (?) 
        :param index: what is this(?) 
        :type index: (?) 
        """

        if index >= self.num_records:
          raise IndexError(
            'Index: {0} exceeded number of records: {1}'.format(
              index, self.num_records))

        det.eig()
        det.f_signal()
        det.noise_cov()
        self.tag_number[index]  = tag_index
        self.epoch_time[index]  = det.time
        self.center_freq[index] = det.params.ctr_freq
        self.e_sig[index,:]     = det.e_sig.transpose()
        self.e_pwr[index]       = det.e_pwr
        self.confidence[index]  = det.e_conf
        self.f_sig[index,:]     = det.f_sig.transpose()
        self.f_pwr[index]       = det.f_pwr
        self.f_bw3[index]       = det.f_bandwidth3
        self.f_bw10[index]      = det.f_bandwidth10
        self.freq[index]        = det.freq
        self.n_cov[index,:,:]   = det.n_cov



    def filter_by_bool(self, tag_filter):
        """ **TODO:** description required. 

        :param tag_filter: what is this(?) 
        :type tag_filter: (?) 
        :rtype: (?) 
        """
        new_data = data_arrays(self.num_channels,np.sum(tag_filter))

        new_data.tag_number  = self.tag_number[tag_filter]
        new_data.epoch_time  = self.epoch_time[tag_filter]
        new_data.center_freq = self.center_freq[tag_filter]
        new_data.e_sig       = self.e_sig[tag_filter,:]
        new_data.e_pwr       = self.e_pwr[tag_filter]
        new_data.confidence  = self.confidence[tag_filter]
        new_data.f_sig       = self.f_sig[tag_filter,:]
        new_data.f_pwr       = self.f_pwr[tag_filter]
        new_data.f_bw3       = self.f_bw3[tag_filter]
        new_data.f_bw10      = self.f_bw10[tag_filter]
        new_data.freq        = self.freq[tag_filter]
        new_data.n_cov       = self.n_cov[tag_filter,:,:]

        return new_data
    

    def filter_by_tag_number(self, number):
        """ **TODO:** description required.

        :param number: (?)
        :type number: (?) 
        :returns: (?)
        """
        tag_filter = self.tag_number == number
        return self.filter_by_bool(tag_filter)


    def filter_non_filled(self):
        """ **TODO:** description required. 

        :returns: (?) 
        """
        tag_filter = ((self.tag_number == -1) == False)
        return self.filter_by_bool(tag_filter)


    def filter_by_bw10(self, threshold = 1000):
        """ **TODO:** description required.

        :param threshold: (?) 
        :type threshold: (?)
        :returns: (?)
        """
        tag_filter = self.f_bw10 < threshold
        return self.filter_by_bool(tag_filter)



#est file class
class est_data:
    """ Encapsulation of .est files. **DEPRECATED** 

    :param filename: filename of the .est file.
    :type filename: string
    :param num_channels: number of channels produced by pulse detector.
    :type num_channels: int
    """

    def __init__(self, num_channels = 4, fn = None):
        
        self.tag_names = []
        self.num_tags = 0
        self.num_channels = num_channels
        self.data = data_arrays(self.num_channels, 0)
        if fn:
          self.read_est(fn)

    def add_det(self, det):
        """ Append pulse record to table. 

        :param det: Pulse data record
        :type det: qraat.det.det
        """

        det.eig()
        det.f_signal()
        det.noise_cov()
        new_data = data_arrays(self.num_channels, 1)
        tag_name = det.tag_name
        try:
            tag_index  = self.tag_names.index(tag_name)
        except ValueError:
            self.tag_names.append(tag_name)
            tag_index = self.num_tags
            self.num_tags += 1
        new_data.add_det(det, tag_index, 0)
        self.data.append(new_data)

    #writes an .est file for each tag
    def write_est(self,dirname = './'):
        """ Writes an .est file for each tag. (Name scheme(?)) 

        :param dirname: output directory of files.
        :type dirname: string
        """

        if not dirname[-1] == '/':
            dirname += '/'
        try:
            os.makedirs(dirname)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(dirname):
                pass
            else: raise
        for tag_index, tag_name in enumerate(self.tag_names):
            filtered_data = self.data.filter_by_tag_number(tag_index)
            #min_time = np.min(filtered_data.epoch_time)
            #min_time_str = time.strftime("%Y%m%d%H%M%S",time.gmtime(min_time))
            #max_time = np.max(filtered_data.epoch_time)
            #max_time_str = time.strftime("%Y%m%d%H%M%S",time.gmtime(max_time))
            #est_filename = tag_name + '-' + min_time_str + '-' + max_time_str + '.est'
            est_filename = tag_name + '.est'
            stat_filename = tag_name + '.stat'

            with open(dirname + est_filename,'w') as estfile:
                estfile.write(struct.pack('i',filtered_data.num_records))
                for index in range(filtered_data.num_records):
                    #estfile.write("det ")
                    estfile.write(struct.pack('i',len(tag_name)))
                    estfile.write(tag_name)
                    estfile.write(struct.pack('i', filtered_data.epoch_time[index]//1))
                    estfile.write(struct.pack('i', (filtered_data.epoch_time[index]%1)*1000000))
                    estfile.write(struct.pack('f',filtered_data.center_freq[index]))
                    estfile.write(struct.pack('i',self.num_channels))
                    for sig in filtered_data.e_sig[index, :]:
                        estfile.write(struct.pack('f',sig.real))
                        estfile.write(struct.pack('f',sig.imag))
                    #print tag_item.e_pwr"][index]
                    estfile.write(struct.pack('f',filtered_data.e_pwr[index]))
                    estfile.write(struct.pack('f',filtered_data.confidence[index]))
                    estfile.write(struct.pack('i',self.num_channels))
                    for sig in filtered_data.f_sig[index,:]:
                        estfile.write(struct.pack('f',sig.real))
                        estfile.write(struct.pack('f',sig.imag))
                    estfile.write(struct.pack('f',filtered_data.f_pwr[index]))
                    estfile.write(struct.pack('f',filtered_data.f_bw3[index]))
                    estfile.write(struct.pack('f',filtered_data.f_bw10[index]))
                    estfile.write(struct.pack('i',int(filtered_data.freq[index])))
                    estfile.write(struct.pack('i',self.num_channels))
                    for sig in filtered_data.n_cov[index,:,:].flat:
                        estfile.write(struct.pack('f',sig.real))
                        estfile.write(struct.pack('f',sig.imag))

            with open(dirname + stat_filename, 'w') as stat_file:
                stat_file.write('Name: {0}\n'.format(tag_name))
                stat_file.write('Number of files: {0}\n'.format(filtered_data.num_records))
                good_data = filtered_data.filter_by_bw10()
                stat_file.write('Number of good pulses: {0}\n'.format(good_data.num_records))
                if good_data.num_records > 0:
                    max_time = np.max(good_data.epoch_time)
                    max_time_str = time.strftime("%Y-%m-%d %H:%M:%S",time.gmtime(max_time))
                    stat_file.write('Last time seen: {0}\n'.format(max_time_str))
                    stat_file.write('Avg. Frequency: {0}\n'.format(np.mean(good_data.freq)))
                    stat_file.write('Avg. Signal Level: {0} dB\n'.format(10*np.log10(np.mean(good_data.f_pwr))))
                    stat_file.write('Std. Dev. Signal Level: {0}\n'.format(np.std(good_data.f_pwr)))


    def write_csv(self, dirname = './'):
        """ Write a .csv file for each tag. 

          **TODO:** Output format(?) Does this contain the same data as .est files(?) 
          Is this obsolete(?)           

        :param dirname: output directory of files.
        :type dirname: string
        """

        if not dirname[-1] == '/':
            dirname += '/'
        try:
            os.makedirs(dirname)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(dirname):
                pass
            else: raise
        for tag_index, tag_name in enumerate(self.tag_names):
            filtered_data = self.data.filter_by_tag_number(tag_index)
            csv_filename = tag_name + '.csv'
            with open(dirname + csv_filename,'w') as csvfile:
                label_str = "Date/Time (UTC), Unix Timestamp (s), Tag Frequency (Hz), Band Center Frequency (Hz), Fourier Decomposition Signal Power, "
                for ch_iter in range(self.num_channels):
                    label_str += "Fourier Decomposition Signal on Channel {0:d} - real part, Fourier Decomposition Signal on Channel {0:d} - imaginary part, ".format(ch_iter + 1)
                label_str += "3dB Bandwidth, 10dB Bandwidth, Eigenvalue Decomposition Signal Power, "
                for ch_iter in range(self.num_channels):
                    label_str += "Eigenvalue Decomposition Signal on Channel {0:d} - real part, Eigenvalue Decomposition Signal on Channel {0:d} - imaginary part, ".format(ch_iter + 1)
                label_str += "Eigenvalue Confidence, Total Noise Power, "
                for ch_iter1 in range(self.num_channels):
                    for ch_iter2 in range(self.num_channels):
                        label_str += "Noise Covariance {0:d}{1:d} - real part, Noise Covariance {0:d}{1:d} - imaginary part, ".format(ch_iter1 + 1, ch_iter2 + 1)
                label_str += "Fourier Decomposition SNR (dB), Eigenvalue Decomposition SNR (dB)\n"
                csvfile.write(label_str)
                for index in range(filtered_data.num_records):
                    line_str = time.strftime("%Y-%m-%d %H:%M:%S",time.gmtime(filtered_data.epoch_time[index]))
                    line_str += ', {0:.6f}'.format(filtered_data.epoch_time[index])
                    line_str += ', {0:.0f}'.format(filtered_data.freq[index])
                    line_str += ', {0:.0f}'.format(filtered_data.center_freq[index])
                    f = filtered_data.f_pwr[index]
                    line_str += ', {0:e}'.format(f)
                    for ch_iter in range(self.num_channels):
                        line_str += ', {0:e}, {1:e}'.format(filtered_data.f_sig[index,ch_iter].real,filtered_data.f_sig[index,ch_iter].imag)
                    line_str += ', {0:.0f}'.format(filtered_data.f_bw3[index])
                    line_str += ', {0:.0f}'.format(filtered_data.f_bw10[index])
                    e = filtered_data.e_pwr[index]
                    line_str += ', {0:e}'.format(e)
                    for ch_iter in range(self.num_channels):
                        line_str += ', {0:e}, {1:e}'.format(filtered_data.e_sig[index,ch_iter].real,filtered_data.e_sig[index,ch_iter].imag)
                    line_str += ', {0:0.5f}'.format(filtered_data.confidence[index])
                    n = np.trace(filtered_data.n_cov[index,:,:]).real
                    line_str += ', {0:e}'.format(n)
                    for ch_iter1 in range(self.num_channels):
                        for ch_iter2 in range(self.num_channels):
                            line_str += ', {0:e}, {1:e}'.format(filtered_data.n_cov[index,ch_iter1,ch_iter2].real, filtered_data.n_cov[index,ch_iter1,ch_iter2].imag)
                    line_str += ', {0:.3f}'.format(10*np.log10(f/n))
                    line_str += ', {0:.3f}\n'.format(10*np.log10(e/n))
                    csvfile.write(line_str)



    #reads data from a est file
    def read_est(self, est_filename):
        """ Read .est file. 

        :param est_filename: filename. 
        :type est_filename: string
        """

        if est_filename[-4:] == ".est":
            with open(est_filename) as estfile:
                (num_entries,) = struct.unpack('i', estfile.read(4))
                #build empty arrays
                temp_data = data_arrays(self.num_channels, num_entries)
                #fill arrays
                for j in range(num_entries):
                    (tag_name_len,) = struct.unpack('i',estfile.read(4))
                    tag_name = estfile.read(tag_name_len)
                    try:
                        tag_index  = self.tag_names.index(tag_name)
                    except ValueError:
                        self.tag_names.append(tag_name)
                        tag_index = self.num_tags
                        self.num_tags += 1
                    temp_data.tag_number[j] = tag_index

                    (time_sec, time_usec) = struct.unpack('ii', estfile.read(8))
                    temp_data.epoch_time[j] = time_sec + time_usec/1000000.0

                    (temp_data.center_freq[j],) = struct.unpack('f', estfile.read(4))

                    (e_sig_len,) = struct.unpack('i', estfile.read(4))
                    if not e_sig_len == self.num_channels:
                        raise ValueError('e_sig_len doesn\'t equal num_channels')
                    for k in range(e_sig_len):
                        (real_part, imaginary_part) = struct.unpack('ff',estfile.read(8))
                        temp_data.e_sig[j,k] = complex(real_part,imaginary_part)

                    (temp_data.e_pwr[j],) = struct.unpack('f', estfile.read(4))

                    (temp_data.confidence[j],) = struct.unpack('f',estfile.read(4))

                    (f_sig_len,) = struct.unpack('i', estfile.read(4))
                    if not f_sig_len == self.num_channels:
                        raise ValueError('f_sig_len doesn\'t equal num_channels')
                    for k in range(f_sig_len):
                        (real_part, imaginary_part) = struct.unpack('ff',estfile.read(8))
                        temp_data.f_sig[j,k] = complex(real_part,imaginary_part)

                    (temp_data.f_pwr[j],) = struct.unpack('f', estfile.read(4))

                    (temp_data.f_bw3[j],) = struct.unpack('f',estfile.read(4))

                    (temp_data.f_bw10[j],) = struct.unpack('f',estfile.read(4))

                    (temp_data.freq[j],) = struct.unpack('i',estfile.read(4))

                    (n_cov_len,) = struct.unpack('i', estfile.read(4))
                    if not n_cov_len == self.num_channels:
                        raise ValueError('n_cov_len doesn\'t equal num_channels')
                    for k in range(n_cov_len):
                        for m in range(n_cov_len):
                            (real_part, imaginary_part) = struct.unpack('ff',estfile.read(8))
                            temp_data.n_cov[j,k,m] = complex(real_part,imaginary_part)

                self.data.append(temp_data)
        else:
            raise IOError, "{0} is not an .est file".format(est_filename)

    def read_dir(self,dirname):
        """ Read all .det files in the given directory.

          **TODO:** recurse into subdirectories(?) 
        
        :param dirname: input directory.
        :type dirname: string
        """

        dir_list = os.listdir(dirname)
        print "{0} files found at {1}".format(len(dir_list), dirname)
        if len(dir_list) > 0:
            dir_list.sort()
            if not dirname[-1] == '/':
                dirname += '/'
            new_data = data_arrays(self.num_channels, len(dir_list))
            count = 0
            for fstr in dir_list:
              if fstr[-4:] == '.det':
                try:
                  det = qraat.det(dirname + fstr)
                  tag_name = det.tag_name
                  try: tag_index  = self.tag_names.index(tag_name)
                  except ValueError:
                    self.tag_names.append(tag_name)
                    tag_index = self.num_tags
                    self.num_tags += 1
                  new_data.add_det(det, tag_index, count)
                  count += 1
                except RuntimeError: pass # same as null_file check. 
                                          # if file can't be read, then
                                          # pulse_data class throws a 
                                          # runtime error. 
            
            self.data.append(new_data.filter_non_filled())



if __name__=="__main__":
  
  try:
    db_con = mdb.connect('localhost', 'root', 'woodland', 'qraat')
    #fella = est(dets=qraat.det.read_dir('test'))
    fella = est()
    fella.read_db(db_con, time.time() - 3600000, time.time())
    print fella
    #fella.write_db(db_con, site='site2')

  except mdb.Error, e:
    print sys.stderr, "error (%d): %s" % (e.args[0], e.args[1])
    sys.exit(1) 
