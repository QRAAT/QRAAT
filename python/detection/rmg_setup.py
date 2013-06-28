# rmg_setup.py
# GUI front end for entering transmitters. (Part of tx_setup.)
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
import rmg_editors
import rmg_param
import os, csv
import math

transmitter_types = rmg_param.transmitter_types

default_transmitter = [True, "N",164.5,"Pulse", 20.0,3.0,2.0,0.01]

class tx_table(grd.PyGridTableBase):

    def __init__(self,parent,data):

        self.parent = parent
        self.data = data
        grd.PyGridTableBase.__init__(self)
        self.colLabels = ["Select", "Name", "Frequency in MHz", "Type", "Pulse Width in ms", "Rise Trigger", "Fall Trigger", "Filter Alpha"]
        self.dataTypes = [grd.GRID_VALUE_BOOL, grd.GRID_VALUE_STRING, grd.GRID_VALUE_FLOAT,
                          grd.GRID_VALUE_CHOICE + ":" + ",".join(transmitter_types.keys()),
                          grd.GRID_VALUE_FLOAT, grd.GRID_VALUE_FLOAT, grd.GRID_VALUE_FLOAT, grd.GRID_VALUE_FLOAT]
        self.colSizes = [50, 200, 150, 120, 150, 150, 150, 150]


    def GetNumberRows(self):
        return len(self.data)

    def GetNumberCols(self):
        return len(self.data[0])

    def IsEmptyCell(self, row, col):

        try:
            return self.data[row][col]
        except IndexError:
            return True

    def GetValue(self, row, col):
        try:
            return self.data[row][col]
        except IndexError:
            return ""

    def SetValue(self, row, col, value):

        try:
            self.data[row][col] = value
        except IndexError:
            return False

    def GetColLabelValue(self, col):
        return self.colLabels[col]

    def GetTypeName(self,row, col):
        return self.dataTypes[col]

    def CanGetValueAs(self, row, col, typeName):

        colType = self.dataTypes[col].split(':')[0]
        if typeName == colType:
            return True
        else:
            return False

    def CanSetValueAs(self, row, col, typeName):
        return self.CanGetValueAs(row, col, typeName)

    def GetColSize(self, col):
        return self.colSizes[col]

    def AppendRow(self, data):
        self.data.append(data)

    def DeleteRow(self, row):
        del self.data[row]

     

class tx_grid(grd.Grid):

    def __init__(self, parent, ID, data, pa_min, pa_max):

        self.parent = parent
        grd.Grid.__init__(self, parent, ID)
        self.table = tx_table(parent,data)
        self.SetTable(self.table, True)
        self.SetRowLabelSize(0)
        for j in range(self.table.GetNumberCols()):
            self.SetColSize(j, self.table.GetColSize(j))
        name_attr = grd.GridCellAttr()
        name_attr.SetEditor(rmg_editors.name_editor())
        self.SetColAttr(1,name_attr)
        freq_attr = grd.GridCellAttr()
        freq_attr.SetEditor(rmg_editors.freq_editor(pa_min,pa_max))
        self.SetColAttr(2,freq_attr)
        pw_attr = grd.GridCellAttr()
        pw_attr.SetEditor(rmg_editors.pw_editor())
        self.SetColAttr(4,pw_attr)
        self.SetColFormatFloat(4,-1,1)
        fr_attr = grd.GridCellAttr()
        fr_attr.SetEditor(rmg_editors.fr_editor())
        self.SetColAttr(5,fr_attr)
        self.SetColFormatFloat(5,-1,2)
        ff_attr = grd.GridCellAttr()
        ff_attr.SetEditor(rmg_editors.ff_editor())
        self.SetColAttr(6,ff_attr)
        self.SetColFormatFloat(6,-1,2)
        fa_attr = grd.GridCellAttr()
        fa_attr.SetEditor(rmg_editors.fa_editor())
        self.SetColAttr(7,fa_attr)
        self.SetColFormatFloat(7,-1,3)

    def AppendRow(self, data):

        self.table.AppendRow(data)
        self.ProcessTableMessage(grd.GridTableMessage(self.table, grd.GRIDTABLE_NOTIFY_ROWS_APPENDED,1))
        self.AdjustScrollbars()

    def delete_checked(self):

        count = 0;
        numrows = self.table.GetNumberRows()
        for j in range(numrows-1,-1,-1):
            if self.table.GetValue(j,0):
                self.table.DeleteRow(j)
                count+=1
        self.ProcessTableMessage(grd.GridTableMessage(self.table, grd.GRIDTABLE_NOTIFY_ROWS_DELETED,numrows-count,count))
        self.AdjustScrollbars()

    def check_all(self):

        for j in range(self.table.GetNumberRows()):
            self.table.SetValue(j,0,True)
        self.ProcessTableMessage(grd.GridTableMessage(self.table, grd.GRIDTABLE_REQUEST_VIEW_GET_VALUES))

    def uncheck_all(self):

        for j in range(self.table.GetNumberRows()):
            self.table.SetValue(j,0,False)
        self.ProcessTableMessage(grd.GridTableMessage(self.table, grd.GRIDTABLE_REQUEST_VIEW_GET_VALUES))

    def invert_check(self):
        for j in range(self.table.GetNumberRows()):
            self.table.SetValue(j,0,not self.table.GetValue(j,0))
        self.ProcessTableMessage(grd.GridTableMessage(self.table, grd.GRIDTABLE_REQUEST_VIEW_GET_VALUES))

    def replace_data(self, data):

        old_rows = self.table.GetNumberRows()
        new_rows = len(data)
        self.table.data = data
        if old_rows > new_rows:
            self.ProcessTableMessage(grd.GridTableMessage(self.table, grd.GRIDTABLE_NOTIFY_ROWS_DELETED,new_rows,
                                     old_rows-new_rows))
        elif new_rows > old_rows:
            self.ProcessTableMessage(grd.GridTableMessage(self.table, grd.GRIDTABLE_NOTIFY_ROWS_APPENDED,new_rows-old_rows))
        self.ProcessTableMessage(grd.GridTableMessage(self.table, grd.GRIDTABLE_REQUEST_VIEW_GET_VALUES))
        self.AdjustScrollbars()



class rmg_window(wx.Frame):

    def __init__(self, parent, id, title):

        self.pa_min = 162000000
        self.pa_max = 167000000

        wx.Frame.__init__(self,parent,id, title, size=(700,600))
        self.CreateStatusBar()

        self.panel = wx.Panel(self, wx.ID_ANY)

#Menu
        menu_bar = wx.MenuBar()
        file_menu = wx.Menu()
        file_menu.Append(101, "&Load\tCtrl+O")
        file_menu.Append(102, "&Save\tCtrl+S")
        file_menu.AppendSeparator()
        file_menu.Append(103, "&Close\tAlt+F4")
        menu_bar.Append(file_menu, "&File")
        help_menu = wx.Menu()
        help_menu.Append(201, "&About")
        menu_bar.Append(help_menu, "&Help")
        self.SetMenuBar(menu_bar)
#Menu Events
        self.Bind(wx.EVT_MENU, self.load_data_dlg, id=101)
        self.Bind(wx.EVT_MENU, self.save_data, id=102)
        self.Bind(wx.EVT_MENU, self.close_window, id=103)
        self.Bind(wx.EVT_MENU, self.about_message, id=201)

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

#RF front-end params
        self.SetStatusText('Not Saved')
        
        self.ID_param_txt = wx.NewId()
        self.param_txt = wx.StaticText(self.panel, self.ID_param_txt,label = "", size = (500,30))
        self.main_sizer.Add(self.param_txt,0,wx.EXPAND)
        self.update_param_txt()

#tx entries
        self.ID_tx_txt = wx.NewId()
        self.tx_txt = wx.StaticText(self.panel,self.ID_tx_txt,label = "Transmitters", size = (100,30))
        self.main_sizer.Add(self.tx_txt,0,wx.CENTER)

        self.ID_grid = wx.NewId()
        self.gr = tx_grid(self.panel, self.ID_grid, [default_transmitter], self.pa_min, self.pa_max)


        self.main_sizer.Add(self.gr,1,wx.EXPAND)

        
#buttons
        self.button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.ID_check_all = wx.NewId()
        self.check_all = wx.Button(self.panel, self.ID_check_all, label = "Check All", size = (120,30))
        wx.EVT_BUTTON(self.panel,self.ID_check_all, self.check_all_tx)
        self.button_sizer.Add(self.check_all,3)
        self.ID_uncheck_all = wx.NewId()
        self.uncheck_all = wx.Button(self.panel, self.ID_uncheck_all, label = "Uncheck All", size = (120,30))
        wx.EVT_BUTTON(self.panel,self.ID_uncheck_all, self.uncheck_all_tx)
        self.button_sizer.Add(self.uncheck_all,3)
        self.ID_invert_all = wx.NewId()
        self.invert_all = wx.Button(self.panel, self.ID_invert_all, label = "Invert Selection", size = (120,30))
        wx.EVT_BUTTON(self.panel,self.ID_invert_all, self.invert_all_tx)
        self.button_sizer.Add(self.invert_all,3)

        self.ID_del_tx = wx.NewId()
        self.del_tx = wx.Button(self.panel, self.ID_del_tx, label = "Delete Selected", size = (120,30))
        wx.EVT_BUTTON(self.panel,self.ID_del_tx, self.del_sel_tx)
        self.button_sizer.Add(self.del_tx,3)
        self.ID_new_tx = wx.NewId()
        self.new_tx = wx.Button(self.panel, self.ID_new_tx, label = "Add New Transmitter", size = (200,30))
        wx.EVT_BUTTON(self.panel, self.ID_new_tx, self.add_new_tx)
        self.button_sizer.Add(self.new_tx,5)
        
        self.main_sizer.Add(self.button_sizer,0,wx.CENTER)

        self.panel.SetSizer(self.main_sizer)
        self.main_sizer.Fit(self)

        #open default dfc file if it exists
        default_dfc = './tx.csv'
        if os.path.isfile(default_dfc):
            self.load_data(default_dfc)

        self.Show(True)

    def add_new_tx(self, event):

        self.gr.AppendRow(list(default_transmitter))
        w, h = self.GetClientSize()
        num_rows = self.gr.table.GetNumberRows()
        if (((h - 127) / 25.0 < num_rows) and ((h - 127) / 25.0 > num_rows - 2)):
            h += 50
            screen_size = wx.GetDisplaySize()
            if (h < screen_size.height - 25):
                self.SetSize((w,h))

    def check_all_tx(self, event):

        self.gr.check_all()

    def uncheck_all_tx(self, event):

        self.gr.uncheck_all()

    def invert_all_tx(self, event):

        self.gr.invert_check()

    def del_sel_tx(self, event):
        
        self.gr.delete_checked()


    def load_data_dlg(self, event):
        dlg = wx.FileDialog(self, "Load .csv file", os.getcwd(), "tx.csv", "*.csv", wx.OPEN | wx.CHANGE_DIR)
        if (dlg.ShowModal() == wx.ID_OK):
            self.load_data(dlg.GetPath())
        dlg.Destroy()

    def load_data(self, path):
    #
    # Load a list of transmitters from a .csv file. This is for modifying 
    # the list of transmitters. Tuning calculation is done when the flow
    # graph is built (rmg_run)  Chris ~18 Sep 2012
    #
        inf = open(path, 'rb')
        transmitters = csv.reader(inf, delimiter = ",", quotechar='"') 
        cols  = transmitters.next() # first row is header
        index = dict( [(cols[i], i) for i in range(len(cols))] ) 
        print 'transmitters'
        new_data = []
        for tx in transmitters:
            print '\t'.join(tx)
            if tx[index['use']] in ['Y', 'y', 'yes', 'Yes', 'YES']: 
                tx[index['use']] = True
            else:
                tx[index['use']] = False
          
            tx[index['freq']] = float(tx[index['freq']])
            tx[index['pulse_width']] = float(tx[index['pulse_width']])
            tx[index['rise_trigger']] = float(tx[index['rise_trigger']])
            tx[index['fall_trigger']] = float(tx[index['fall_trigger']])
            tx[index['filter_alpha']] = float(tx[index['filter_alpha']])
            new_data.append(tx)

        #adjust size of window
        num_rows = self.gr.table.GetNumberRows()
        w, h = self.GetClientSize()
        num_rows = self.gr.table.GetNumberRows()
        new_rows = len(new_data) - num_rows
        print new_rows
        if (new_rows > 0 and ((h - 128) / 25.0 < num_rows) and ((h - 128) / 25.0 > num_rows - 2)):
            h += 25*new_rows+25
            screen_size = wx.GetDisplaySize()
            if (h < screen_size.height - 25):
                self.SetSize((w,h))
            else:
		self.SetSize((w,screen_size.height))

        #replace current txs with ones in file
        self.gr.replace_data(new_data)


            
        self.update_param_txt()
        self.SetStatusText(path)


    def update_param_txt(self):
            param_str = "Frequency Range: {0} - {1} MHz".format(self.pa_min/1000000.0, self.pa_max/1000000.0)
            self.param_txt.SetLabel(param_str)        

    def save_data(self, event):
    #
    # Output a .csv file with transmitter information. (Calculate tuning 
    # when the flow graph is built (rmg_run)  Chris ~18 Sep 2012
    #

        dlg = wx.FileDialog(self, "Save file as ...", os.getcwd(), "tx.csv", "*.csv", wx.SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            outf = open( dlg.GetPath(), 'w' )
            outf.write('use,name,freq,type,pulse_width,rise_trigger,fall_trigger,filter_alpha\n')
            for row in self.gr.table.data: 
                if row[0] == True:
                  row[0] = 'yes'
                else: 
                  row[0] = 'no'
                outf.write(','.join([ str(i) for i in row ]) + "\n")
            outf.close()

            self.SetStatusText(dlg.GetFilename())
        dlg.Destroy()

    def close_window(self, event):
        self.Close()

    def about_message(self, event):
        wx.MessageDialog(self, "This program determines the necessary set-up parameters to run the RMG Receiver.\n\nDept. of Electrical and Computer Engineering\nUniversity of Illinois, Urbana-Champaign\nWritten by Todd Borrowman\nMarch 2010",
                                 "About",wx.OK).ShowModal()



if __name__ == "__main__":
    app = wx.PySimpleApp()
    frame = rmg_window(None, wx.ID_ANY, "Direction Finder Configure")

    app.MainLoop()
