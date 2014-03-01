# error.py - Exception classes for QRAAT. 
#
# Copyright (C) 2014 Christopher Patton
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

class QraatError (Exception):

  def __init__(self, msg, no=0):

    self.msg = msg
    self.no = no

  def __str__(self):
    
    if self.no > 0:
      return '[%d] %s' % (self.no, self.msg)

    else:
      return self.msg

class ResolveIdError (QraatError):

  def __init__(self, txid, siteid):
    QraatError.__init__(self, None, 1)
    self.txid = txid
    self.siteid = siteid

  def __str__(self):
    return "could not resolve foreign key(s) for table row (txid='%s', siteid='%s')" % (
      self.txid, self.siteid)

