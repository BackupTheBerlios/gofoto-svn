#!/usr/bin/python

#
# GOFoto 0.1.0 - a photo manager application, Photo Refining plugin
#
# Copyright (c) 2004-2005 Michal Nowikowski
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#

from __future__ import generators
import sys
import os
import logging
import random
import PIL.Image
import wave
import threading

import xml.dom.minidom

import pygtk
pygtk.require('2.0')

import gtk
import gtk.glade
import gobject

import time


import plugins


class PhotoRefining(plugins.Plugin):
    def __init__(self, gofoto, dir):
        self.gofoto = gofoto
        self.dir = dir

        self.plugin_name = "Photo Refining"

        self.xml = gtk.glade.XML(os.path.join(dir, "gui.glade"), "vbox")
        self.gui_root = self.xml.get_widget("vbox")
        
        self.chkbtn_pict_vertical = self.xml.get_widget("chkbtn_pict_vertical")
        self.image = self.xml.get_widget("image")

        self.xml.signal_autoconnect({
            "on_btn_cnv_rot_right_clicked": self.on_btn_cnv_rot_right_clicked,
            "on_btn_cnv_rot_left_clicked": self.on_btn_cnv_rot_left_clicked,
            "on_btn_cnv_despeckle_clicked": self.on_btn_cnv_despeckle_clicked,
            "on_btn_cnv_get_orig_clicked": self.on_btn_cnv_get_orig_clicked,
            "on_btn_pict_prev_clicked": self.on_btn_pict_prev_clicked,
            "on_btn_pict_next_clicked": self.on_btn_pict_next_clicked,
            "on_chkbtn_pict_vertical_toggled": self.on_chkbtn_pict_vertical_toggled})

        pass

    def __get_big(self, pict):
        if pict.big == None:
            pict.big = gtk.gdk.pixbuf_new_from_file_at_size(pict.pathfilename, 600, 500)
            pass
        return pict.big


    def __convert_picts(self, operation):
        picts = self.gofoto.albumsBrowser.get_selected_picts()
        first = True
        for pict in picts:
            self.__convert(pict, operation)
            if first:
                first = False
                self.image.set_from_pixbuf(self.__get_big(pict))
                pass
            pass
        pass

    def __convert(self, pict, operation):
        print operation
        dir = pict.album.dir

        # make backup
        orig_dir = os.path.join(dir, "orig")
        orig_file = os.path.join(dir, "orig", pict.props.name)
        if not os.path.exists(orig_dir):
            os.mkdir(orig_dir)
            pass
        if not os.access(orig_file, os.F_OK):
            os.system("cp '%s' '%s'" % (pict.pathfilename, orig_file))
            pict.props.orig = orig_file
            pass

        dest = os.path.join(dir, "tmp-"+pict.props.name)
        # perform operation
        if operation == "rotate left":
            #os.system("convert -rotate -90 "+pict.name+" "+pict.name)
            os.system("jpegtran -rotate 270 -trim '%s' > '%s' && mv '%s' '%s'" %
                      (pict.pathfilename, dest, dest, pict.pathfilename))
            pass
        elif operation == "rotate right":
            #os.system("convert -rotate 90 "+pict.name+" "+pict.name)
            os.system("jpegtran -rotate 90 -trim '%s' > '%s' && mv '%s' '%s'" %
                      (pict.pathfilename, dest, dest, pict.pathfilename))
            pass
        elif operation == "despeckle":
            os.system("convert -despeckle '%s' '%s'" % (pict.pathfilename,
                                                        pict.pathfilename))
            pass
        elif operation == "get orig":
            os.system("mv '%s' '%s'" % (pict.props.orig, pict.pathfilename))
            pass
        else:
            print "unknown operation " + operation
            return

        pict.reload()
        pass

    def on_btn_cnv_rot_right_clicked(self, widget):
        self.__convert_picts("rotate right")
        pass

    def on_btn_cnv_rot_left_clicked(self, widget):
        self.__convert_picts("rotate left")
        pass

    def on_btn_cnv_despeckle_clicked(self, widget):
        self.__convert_picts("despeckle")
        pass

    def on_btn_cnv_get_orig_clicked(self, widget):
        self.__convert_picts("get orig")
        pass

    def on_btn_pict_prev_clicked(self, widget):
        print "prev"
        self.gofoto.albumsBrowser.select_pict_relative(-1)
        pass

    def on_btn_pict_next_clicked(self, widget):
        print "next"
        self.gofoto.albumsBrowser.select_pict_relative(1)
        pass

    def on_chkbtn_pict_vertical_toggled(self, widget):
        active = self.chkbtn_pict_vertical.get_active()
        list = self.gofoto.albumsBrowser.get_selected_picts()
        for p in list:
            p.props.vertical = active
            pass
        pass

    def __load_pict(self, pict):
        self.image.set_from_pixbuf(self.__get_big(pict))
        self.chkbtn_pict_vertical.set_active(pict.props.vertical)
        pass

    def ev_activate_plugin(self):
        picts = self.gofoto.albumsBrowser.get_selected_picts()
        if picts and picts[0]:
            self.__load_pict(picts[0])
            pass
        pass

    def ev_pict_changed(self, pict):
        if pict:
            self.__load_pict(pict)
        pass

main_class = PhotoRefining
