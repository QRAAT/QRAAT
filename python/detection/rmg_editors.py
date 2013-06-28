# rmg_editors.py
# Defines textbox editors for the setup table. (Part of tx_setup.)
# This file is part of QRAAT, an automated animal tracking system 
# based on GNU Radio. 
#
# Copyright (C) 2012 Todd Borrowman
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

import wx
import wx.grid as grd
import rmg_validators as rmg_val


class name_editor(grd.PyGridCellEditor):

    def __init__(self):
        grd.PyGridCellEditor.__init__(self)

    def Create(self, parent, ID, evtHandler):

        self._tc = wx.TextCtrl(parent, ID, "")
        self._tc.SetInsertionPoint(0)
        self.SetControl(self._tc)

        if evtHandler:
            self._tc.PushEventHandler(evtHandler)

    def BeginEdit(self, row, col, grid):

        self.startValue = grid.GetTable().GetValue(row, col)
        self._tc.SetValue(self.startValue)
        #self._tc.SetInsetionPointEnd()
        self._tc.SetFocus()
        self._tc.SetSelection(0,self._tc.GetLastPosition())

    def EndEdit(self, row, col, grid):

        changed = False
        val = self._tc.GetValue()
        if val != self.startValue:
            if rmg_val.name_val(val):
                changed = True
                grid.GetTable().SetValue(row, col, val)
            #else:
                #Failed Verification Dialog HERE
                #wx.MessageDialog(grid.parent, "Names can not contain the characters \\ : * ? | < > /",
                                # "Invalid Name",wx.OK|wx.ICON_EXCLAMATION).ShowModal()
                #changed = False
        self.startValue = ""
        self._tc.SetValue("")
        return changed

    def StartingKey(self,event):
        key = event.GetUnicodeKey()
        self._tc.SetValue(chr(key))
        self._tc.SetInsertionPointEnd()

    def Reset(self):

        self._tc.SetValue(self.startValue)
        self._tc.SetInsertionPointEnd()

    def Clone(self):
        return name_editor(self)

class freq_editor(grd.PyGridCellEditor):

    def __init__(self, pa_min, pa_max):
        grd.PyGridCellEditor.__init__(self)
        self.pa_min = pa_min
        self.pa_max = pa_max

    def Create(self, parent, ID, evtHandler):

        self._tc = wx.TextCtrl(parent, ID, "")
        self._tc.SetInsertionPoint(0)
        self.SetControl(self._tc)

        if evtHandler:
            self._tc.PushEventHandler(evtHandler)

    def BeginEdit(self, row, col, grid):

        self.startValue = str(grid.GetTable().GetValue(row, col))
        self._tc.SetValue(self.startValue)
        #self._tc.SetInsetionPointEnd()
        self._tc.SetFocus()
        self._tc.SetSelection(0,self._tc.GetLastPosition())

    def EndEdit(self, row, col, grid):

        changed = False
        val = self._tc.GetValue()
        if val != self.startValue:
            if rmg_val.freq_val(val,self.pa_min,self.pa_max):
                changed = True
                grid.GetTable().SetValue(row, col, float(val))

        self.startValue = ""
        self._tc.SetValue("")
        return changed

    def StartingKey(self,event):
        key = event.GetUnicodeKey()
        self._tc.SetValue(chr(key))
        self._tc.SetInsertionPointEnd()

    def Reset(self):

        self._tc.SetValue(self.startValue)
        self._tc.SetInsertionPointEnd()

    def Clone(self):
        return name_editor(self)


class pw_editor(grd.PyGridCellEditor):

    def __init__(self):
        grd.PyGridCellEditor.__init__(self)

    def Create(self, parent, ID, evtHandler):

        self._tc = wx.TextCtrl(parent, ID, "")
        self._tc.SetInsertionPoint(0)
        self.SetControl(self._tc)

        if evtHandler:
            self._tc.PushEventHandler(evtHandler)

    def BeginEdit(self, row, col, grid):

        self.startValue = str(grid.GetTable().GetValue(row, col))
        self._tc.SetValue(self.startValue)
        
        self._tc.SetFocus()
        self._tc.SetSelection(0,self._tc.GetLastPosition())

    def EndEdit(self, row, col, grid):

        changed = False
        val = str(self._tc.GetValue())
        if val != self.startValue:
            if rmg_val.pw_val(val):
                changed = True
                grid.GetTable().SetValue(row, col, float(val))
        self.startValue = ""
        self._tc.SetValue("")
        return changed

    def StartingKey(self,event):
        key = event.GetUnicodeKey()
        self._tc.SetValue(chr(key))
        self._tc.SetInsertionPointEnd()

    def Reset(self):

        self._tc.SetValue(self.startValue)
        self._tc.SetInsertionPointEnd()

    def Clone(self):
        return pw_editor(self)

class fr_editor(grd.PyGridCellEditor):

    def __init__(self):
        grd.PyGridCellEditor.__init__(self)

    def Create(self, parent, ID, evtHandler):

        self._tc = wx.TextCtrl(parent, ID, "")
        self._tc.SetInsertionPoint(0)
        self.SetControl(self._tc)

        if evtHandler:
            self._tc.PushEventHandler(evtHandler)

    def BeginEdit(self, row, col, grid):

        self.startValue = str(grid.GetTable().GetValue(row, col))
        self._tc.SetValue(self.startValue)
        
        self._tc.SetFocus()
        self._tc.SetSelection(0,self._tc.GetLastPosition())

    def EndEdit(self, row, col, grid):

        changed = False
        val = str(self._tc.GetValue())
        if val != self.startValue:
            if rmg_val.fr_val(val,float(grid.GetTable().GetValue(row,col+1))):
                changed = True
                grid.GetTable().SetValue(row, col, float(val))
        self.startValue = ""
        self._tc.SetValue("")
        return changed

    def StartingKey(self,event):
        key = event.GetUnicodeKey()
        self._tc.SetValue(chr(key))
        self._tc.SetInsertionPointEnd()

    def Reset(self):

        self._tc.SetValue(self.startValue)
        self._tc.SetInsertionPointEnd()

    def Clone(self):
        return fr_editor(self)

class ff_editor(grd.PyGridCellEditor):

    def __init__(self):
        grd.PyGridCellEditor.__init__(self)

    def Create(self, parent, ID, evtHandler):

        self._tc = wx.TextCtrl(parent, ID, "")
        self._tc.SetInsertionPoint(0)
        self.SetControl(self._tc)

        if evtHandler:
            self._tc.PushEventHandler(evtHandler)

    def BeginEdit(self, row, col, grid):

        self.startValue = str(grid.GetTable().GetValue(row, col))
        self._tc.SetValue(self.startValue)
        
        self._tc.SetFocus()
        self._tc.SetSelection(0,self._tc.GetLastPosition())

    def EndEdit(self, row, col, grid):

        changed = False
        val = str(self._tc.GetValue())
        if val != self.startValue:
            if rmg_val.ff_val(val,float(grid.GetTable().GetValue(row,col-1))):
                changed = True
                grid.GetTable().SetValue(row, col, float(val))
        self.startValue = ""
        self._tc.SetValue("")
        return changed

    def StartingKey(self,event):
        key = event.GetUnicodeKey()
        self._tc.SetValue(chr(key))
        self._tc.SetInsertionPointEnd()

    def Reset(self):

        self._tc.SetValue(self.startValue)
        self._tc.SetInsertionPointEnd()

    def Clone(self):
        return ff_editor(self)

class fa_editor(grd.PyGridCellEditor):

    def __init__(self):
        grd.PyGridCellEditor.__init__(self)

    def Create(self, parent, ID, evtHandler):

        self._tc = wx.TextCtrl(parent, ID, "")
        self._tc.SetInsertionPoint(0)
        self.SetControl(self._tc)

        if evtHandler:
            self._tc.PushEventHandler(evtHandler)

    def BeginEdit(self, row, col, grid):

        self.startValue = str(grid.GetTable().GetValue(row, col))
        self._tc.SetValue(self.startValue)
        
        self._tc.SetFocus()
        self._tc.SetSelection(0,self._tc.GetLastPosition())

    def EndEdit(self, row, col, grid):

        changed = False
        val = str(self._tc.GetValue())
        if val != self.startValue:
            if rmg_val.fa_val(val):
                changed = True
                grid.GetTable().SetValue(row, col, float(val))
        self.startValue = ""
        self._tc.SetValue("")
        return changed

    def StartingKey(self,event):
        key = event.GetUnicodeKey()
        self._tc.SetValue(chr(key))
        self._tc.SetInsertionPointEnd()

    def Reset(self):

        self._tc.SetValue(self.startValue)
        self._tc.SetInsertionPointEnd()

    def Clone(self):
        return fa_editor(self)


     
