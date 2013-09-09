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

import sys

class csv: 
  
  """ 
    Encapsulate a CSV file. The rows are accessed via the [] operator. 
    Each row is a Row object, whose attributes correspond to the CSV 
    columns. 

    :param fn: Input file name. 
    :type fn: str
  """

  #: The CSV table.
  table = []
  
  def __init__(self, fn=None): 
    if fn: 
      self.read(fn)

  def read(self, fn): 
    """ Read a CSV file. 
    
      :param fn: Input file name. 
      :type fn: str
    """

    if type(fn) == str: 
      fd = open(fn, 'r')
    elif type(fn) == file: 
      fd = fn
    else: raise TypeError

    lengths = self.__build_header(fd)

    # Populate the table.
    for line in map(lambda l: l.strip().split(','), fd.readlines()): 
      self.table.append(self.Row())
      for i in range(len(self.headers)): 
        if lengths[i] < len(line[i]):
          lengths[i] = len(line[i])
        setattr(self.table[-1], self.headers[i], line[i])
    fd.close()
    
    self.__build_row_template(lengths)


  def write(self, fn): 
    """ Write data table to CSV file. 

      TODO

      :param fn: Output file name. 
      :type fn: str
    """
    pass
  
  
  def __str__(self):
    res = self._row_template % tuple(self.headers) + '\n'
    res += '\n'.join(
      (self._row_template % tuple(
        getattr(row, col) for col in self.headers)) for row in self.table) 
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

  def __build_header(self, fd):
    """ 
      Read column names from file descriptor and create the Row 
      type. Return a dictionary mapping the names of columns to 
      the their length. This will be used to compute the row 
      template string. 
    """
    
    #: Column names, referenced by rows. 
    self.headers = [ h for h in fd.readline().strip().split(',') ]

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
    """ Build row template string from maximum column lengths ``ls``. """

    #: Template string for displaying table rows. 
    self._row_template = ' '.join(
       ['%-{0}s'.format(i) for i in lengths])


if __name__ == '__main__': 
  tx = csv('../build/tx.csv')
  print list(tx[0])
  for line in tx: 
    print line
