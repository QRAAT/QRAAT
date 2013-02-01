#rmg_validators.py

#events and functions for validating information in the setup form

#Todd Borrowman ECE-UIUC 02/2010

import wx
import re

#events regarding the name column
class name_evt:

    def __init__(self, txtbox):
        self.tb = txtbox
        self.txt = self.tb.GetValue()

    def onFocus(self, event):
        #print "on"
        self.txt = self.tb.GetValue()

    def offFocus(self, event):
        #print "off"
        newtxt = self.tb.GetValue()
        if newtxt != self.txt:
            if not name_val(newtxt):
                self.tb.SetValue(self.txt)
                self.tb.SetFocus()
            else:
                self.txt = newtxt

#name validator
def name_val(txt):

        passed = True
        p = re.compile('[\\\\:*?|<>/]')
        matched = p.search(txt)
        if matched:
            passed = False
            #print matched.group()
            wx.MessageDialog(None, "Names can not contain the characters \\ : * ? | < > /",
                                 "Invalid Name",wx.OK|wx.ICON_EXCLAMATION).ShowModal()
        return passed

#events regarding the frequency column
class freq_evt:

    def __init__(self, txtbox, cf, bw):
        self.tb = txtbox
        self.txt = self.tb.GetValue()
        self.cf = cf
        self.bw = bw

    def onFocus(self, event):
        self.txt = self.tb.GetValue()

    def offFocus(self, event):

        newtxt = self.tb.GetValue()
        if newtxt != self.txt:
            if not freq_val(newtxt, self.cf, self.bw):
                self.tb.SetValue(self.txt)
                self.tb.SetFocus()
            else:
                self.txt = newtxt
#frequency validation
def freq_val(txt, pa_min, pa_max):

    passed = True
    p = re.compile('(\\d*[.]?\\d*$)')
    matched = p.match(txt)
#is number?
    if not matched:
        passed = False
        wx.MessageDialog(None, "Frequency must be a number in MHz",
                         "Invalid Frequency",wx.OK|wx.ICON_EXCLAMATION).ShowModal()
#valid number?
    if passed and ((float(txt)*1000000 < pa_min) or (float(txt)*1000000 > (pa_max))):
        passed = False
        wx.MessageDialog(None, "Frequency must be within the pre-amp bandwidth (%f - %f MHz)" %(pa_min,pa_max),
                         "Invalid Frequency",wx.OK|wx.ICON_EXCLAMATION).ShowModal()
        
    return passed

#events regarding the pulse width column
class pw_evt:

    def __init__(self, txtbox):
        self.tb = txtbox
        self.txt = self.tb.GetValue()

    def onFocus(self, event):
        
        self.txt = self.tb.GetValue()

    def offFocus(self, event):
        
        newtxt = self.tb.GetValue()
        if newtxt != self.txt:
            if not pw_val(newtxt):
                self.tb.SetValue(round(float(self.txt),1))
                self.tb.SetFocus()
            else:
                self.txt = newtxt

#pulse width validation
def pw_val(txt):

        passed = True
        p = re.compile('\\d*[.]?\\d*$')
        matched = p.match(txt)
        if not matched:
            passed = False
            #print matched.group()
            wx.MessageDialog(None, "Pulse Width must be a positive number in ms",
                                 "Invalid Pulse Width",wx.OK|wx.ICON_EXCLAMATION).ShowModal()
        return passed

#filter rise validation
def fr_val(txt,ff_value):

    passed = True
    p = re.compile('(\\d*[.]?\\d*$)')
    matched = p.match(txt)
#is number?
    if not matched:
        passed = False
        wx.MessageDialog(None, "Rise Trigger must be a number greater than Fall Trigger",
                         "Invalid Frequency",wx.OK|wx.ICON_EXCLAMATION).ShowModal()
#valid number?
    if passed and (float(txt) < ff_value):
        passed = False
        wx.MessageDialog(None, "Rise Trigger must be greater than Fall Trigger",
                         "Invalid Frequency",wx.OK|wx.ICON_EXCLAMATION).ShowModal()
        
    return passed

#filter fall validation
def ff_val(txt,fr_value):

    passed = True
    p = re.compile('(\\d*[.]?\\d*$)')
    matched = p.match(txt)
#is number?
    if not matched:
        passed = False
        wx.MessageDialog(None, "Fall Trigger must be a number between 1 and Rise Trigger",
                         "Invalid Frequency",wx.OK|wx.ICON_EXCLAMATION).ShowModal()
#valid number?
    if passed and ((float(txt) < 1) or (float(txt) > fr_value)):
        passed = False
        wx.MessageDialog(None, "Frequency must be within 1 and Rise Trigger",
                         "Invalid Frequency",wx.OK|wx.ICON_EXCLAMATION).ShowModal()
        
    return passed

#filter alpha validation
def fa_val(txt):

    passed = True
    p = re.compile('(\\d*[.]?\\d*$)')
    matched = p.match(txt)
#is number?
    if not matched:
        passed = False
        wx.MessageDialog(None, "Filter Alpha must be a number between 0 and 1",
                         "Invalid Frequency",wx.OK|wx.ICON_EXCLAMATION).ShowModal()
#valid number?
    if passed and ((float(txt) < 0) or (float(txt) > 1)):
        passed = False
        wx.MessageDialog(None, "Filter Alpha must be within 0 and 1",
                         "Invalid Frequency",wx.OK|wx.ICON_EXCLAMATION).ShowModal()
        
    return passed
