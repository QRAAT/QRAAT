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

  def __init__(self, fn=None): 
    #: The CSV table. 
    self.table = []
    if fn: 
      self.read(fn)

  def read(self, fn): 
    """ Read a CSV file. 
    
      :param fn: Input file name. 
      :type fn: str
    """

    fd = open(fn, 'r')

    # Store the maximum row length per column. This value will 
    # be used to compute a string template for displaying the 
    # table. 
    headers = { header : len(header) 
                      for header in fd.readline().strip().split(',') }

    # Create an object for rows. TODO Row.__str__() should print 
    # the row in a pretty way. Perhaps some sort of fancy meta 
    # template string thing? In any case, I don't need to worry 
    # about this right now. ~cjp 9/5/2013
    self.Row = type('Row', (object,), {header : None for header in headers})
    def f(self):
      return "TODO"
    self.Row.__str__ = f
    
    # Populate the table.
    for line in map(lambda l: l.strip().split(','), fd.readlines()): 
      self.table.append(self.Row())
      for (cell, value) in zip(headers.keys(), line):
        if headers[cell] < len(value):
          headers[cell] = len(value)  
        setattr(self.table[-1], cell, value)
    fd.close()

    #: Template string for displaying table rows. 
    self._row_template = ' '.join(
          [ '%-{0}s'.format(i) for i in headers.itervalues()])

    #: Header names.
    self.headers = headers.keys()

  def __str__(self):
    res = self._row_template % tuple(self.headers) + '\n'
    res += '\n'.join(
      (self._row_template % tuple(
        getattr(row, col) for col in self.headers)) for row in self.table) 
    return res

  def write(self, fn): 
    """ Write data table to CSV file. 

      TODO

      :param fn: Output file name. 
      :type fn: str
    """
    pass
  
  def __getitem__(self, i): 
    return self.table[i]

  def __getslice__(self, i, j):
    return self.table[i:j]


if __name__ == '__main__': 
  tx = csv('../build/tx.csv')
  print tx
  print tx[0].name
  print tx[:]
