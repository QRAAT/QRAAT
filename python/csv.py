# csv.py - Handler classes for QRAAT metadata, such as configuration
# files, log files, etc. This program is part of the # QRAAT system. 
#
# Copyright (C) 2013 Christopher Patton
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

import sys, time, numpy.float64
import copy

def pretty_printer(val):
  """ 
    Convert table cell value to a pretty string suitable for displaying. 
  """ 
  if type(val) in [float, numpy.float64]:
    if len(str(val)) > 6: 
      return '{0:e}'.format(val)
    else: return str(val)
  elif type(val) == time.struct_time: 
    return time.strftime("%Y-%m-%d %H:%M:%S", val)
  elif val == None: 
    return '' 
  else:
    return str(val)

class csv: 
  
  """ 
    Encapsulate a CSV file. The rows are accessed via the [] operator. 
    Each row is a Row object, whose attributes correspond to the CSV 
    columns. This class's constructor accepts a file, e.g. 
    ``txist = csv('tx.list')``, or DB connector class and the name 
    of a table, e.g. ``txlist = csv(db_con=db_con, table='txlist')``. 

  :param fn: Input file name or file descriptor. 
  :type fn: str, file
  :param db_con: DB connector. 
  :type db_con: MySQLdb.connections.Conneection
  :param table: Table name. 
  :type table: str
  """
  
  #: The CSV table.
  table = []

  #: Type for table rows. In the constructor, attributes corresponding 
  #: to table columns are assigned. 
  Row = type('Row', (object,), {})
  
  def __init__(self, fn=None, db_con=None, db_table=None):

    #: The CSV table.
    self.table = []
  
    if fn: 
      self.read(fn)

    elif db_con and db_table: 
      self.read_db(db_con, db_table)


  def read(self, fn): 
    """ Read a CSV file. 
    
      :param fn: Input file name. 
      :type fn: str
    """

    if type(fn) == str: 
      fd = open(fn, 'r')
    elif type(fn) == file: 
      fd = fn
    else: raise TypeError # Provide a message. 

    lengths = self.__build_header(fd.readline().strip().split(','))

    # Populate the table.
    for line in map(lambda l: l.strip().split(','), fd.readlines()):
      self.table.append(self.Row())
      for i in range(len(self.headers)): 
        if lengths[i] < len(line[i]):
          lengths[i] = len(line[i])
        setattr(self.table[-1], self.headers[i], line[i])
    fd.close()
    self.__build_row_template(lengths)


  def read_db(self, db_con, table): 
    """ Read a small database table. 

      :param db_con: DB connector. 
      :type db_con: MySQLdb.connections.Conneection
      :param table: Table name. 
      :type table: str
    """
    
    cur = db_con.cursor()
    cur.execute('''SELECT `COLUMN_NAME`
                     FROM `INFORMATION_SCHEMA`.`COLUMNS`
                    wHERE `TABLE_NAME` = '%s' ''' % table)
    lengths = self.__build_header(map(lambda val: val[0], cur.fetchall()))

    # Populate the table. 
    cur.execute('SELECT * FROM %s' % table)
    for row in cur.fetchall(): 
      self.table.append(self.Row())
      for i in range(len(self.headers)): 
        if lengths[i] < len(str(row[i])):
          lengths[i] = len(str(row[i]))
        setattr(self.table[-1], self.headers[i], row[i])
    self.__build_row_template(lengths)


  def write(self, fn, exclude=[]): 
    """ Write data table to CSV file.

      :param fn: Output file name. 
      :type fn: str
      :param exclude: Columns to exclude when writing the table. 
      :type exclude: str list
    """
    
    headers = [col for col in self.headers if col not in exclude]
    
    if type(fn) == str: 
      fd = open(fn, 'w')
    elif type(fn) == file: 
      fd = fn
    else: raise TypeError # Provide a message. 

    res = ','.join(headers) + '\n'
    res += '\n'.join(
      ','.join(pretty_printer(getattr(row, col)) 
        for col in headers) 
       for row in self.table)
    fd.write(res + '\n')
    

  def get(self, **cols):
    """ Get the first row that matches the given criteria. 
    
      Input is a list of *(column, value)* pairs.

    :returns: qraat.csv.Row.
    """
    for row in self.table:
      match = True
      for (col, val) in cols.iteritems(): 
        if getattr(row, col) != val:
          match = False; break 
      if match: return row
    return None
  

  def filter(self, **cols):
    """ Filter a table. 
       
      Accept (col, val) pairs and returns a qraat.csv type.
      This is equivelant to "SELECT table WHERE col1 = val1 AND ...
      colN = valN;" in SQL terms. 

    :returns: qraat.csv
    """
    filtered = copy.deepcopy(self)
    filtered.table = []
    for row in self.table:
      match = True
      for (col, val) in cols.iteritems(): 
        if getattr(row, col) != val:
          match = False; break
      if match: filtered.table.append(row)
    return filtered

    

  def __str__(self):
    res = self._row_template % tuple(self.headers) + '\n'
    res += '\n'.join(
      (self._row_template % tuple(
        pretty_printer(getattr(row, col)) for col in self.headers)) for row in self.table) 
    return res
 
  def __len__(self):
    return len(self.table)

  def __iter__(self):
    for row in self.table:
      yield row

  def __getitem__(self, i): 
    return self.table[i]

  def __getslice__(self, i, j):
    return self.table[i:j]

  def __build_header(self, h):
    """ 
      Read column names from file descriptor and create the Row 
      type. Return a dictionary mapping the names of columns to 
      the their length. This will be used to compute the row 
      template string. 
    """
    
    #: Column names, referenced by rows. 
    self.headers = h

    # Store the maximum row length per column. This value will 
    # be used to compute a string template for displaying the 
    # table. 
    lengths = [ len(h) for h in self.headers ]

    #: Type for table rows. This allows us to use the column 
    #: names as class attributes. 
    self.Row = type('Row', (object,), {h : None for h in self.headers})
    self.Row.headers = self.headers
    
    def f(self):
      for h in self.headers:
        yield getattr(self, h) 
    self.Row.__iter__ = f

    return lengths
   

  def __build_row_template(self, lengths):
    """ Build row template string from maximum column lengths ``lengths``. """

    #: Template string for displaying table rows. 
    self._row_template = ' '.join(
       ['%-{0}s'.format(i) for i in lengths])



if __name__ == '__main__': # Testing, testing ... 

  import MySQLdb as mdb
  try:
    db_con = mdb.connect('localhost', 'root', 'woodland', 'qraat')
    txlist = csv(db_con=db_con, db_table='txlist')
    txlist.write('fella')

  except mdb.Error, e:
    print sys.stderr, "error (%d): %s" % (e.args[0], e.args[1])
    sys.exit(1) 
