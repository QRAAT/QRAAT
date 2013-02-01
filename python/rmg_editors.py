#rmg_editors.py

#defines textbox editors for the setup table

#Todd Borrowman ECE-UIUC 02/2010

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


     
