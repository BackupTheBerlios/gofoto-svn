#!/usr/bin/python

#
# GOFoto 0.0.2 - a photo manager application
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


class WebGallery(plugins.Plugin):
    GAL_CLMN_PICT = 0
    GAL_CLMN_MARK = 1
    GAL_CLMN_NAME = 2
    def __init__(self, gofoto, dir):
        self.gofoto = gofoto
        self.dir = dir

        self.plugin_name = "Web Gallery"

        self.xml = gtk.glade.XML(os.path.join(dir, "gui.glade"), "vbox")
        self.gui_root = self.xml.get_widget("vbox")

        self.album = None

        self.tv_gal_picts = self.xml.get_widget("tv_gal_picts")
        self.ent_gal_title = self.xml.get_widget("ent_gal_title")

        self.xml.signal_autoconnect({
            "on_btn_create_gal_clicked": self.on_btn_create_gal_clicked,
            "on_ent_gal_title_focus_out_event": self.on_ent_gal_title_focus_out_event})

        renderer = gtk.CellRendererToggle() # Mark
        renderer.connect("toggled", self.on_tv_gal_pict_toggled)
        clmn = gtk.TreeViewColumn("Mark", renderer, active=self.GAL_CLMN_MARK)
        self.tv_gal_picts.append_column(clmn)

        renderer = gtk.CellRendererText()   # Pict
        clmn = gtk.TreeViewColumn("Pict", renderer, text=self.GAL_CLMN_NAME)
        self.tv_gal_picts.append_column(clmn)

        self.tv_gal_clmn_types = (gobject.TYPE_PYOBJECT,
                                  gobject.TYPE_BOOLEAN,
                                  gobject.TYPE_STRING)

        model = gtk.ListStore(*self.tv_gal_clmn_types)
        self.tv_gal_picts.set_model(model)

        self.tv_gal_picts.enable_model_drag_dest([('MY_TREE_MODEL_ROW', 0, 0),
                                                  ('text/plain', 0, 1),
                                                  ('TEXT', 0, 2),
                                                  ('STRING', 0, 3)],
                                                 gtk.gdk.ACTION_DEFAULT)
        pass

    def ev_activate_plugin(self):
        album = self.gofoto.albumsBrowser.get_current_album()
        if album:
            self.__load_album(album)
            curr_pict = self.gofoto.albumsBrowser.get_selected_picts()[0]
            if curr_pict:
                self.__select_pict(curr_pict)
                pass
            pass
        pass

    def ev_album_changed(self, album):
        self.__load_album(album)
        pass

    def ev_pict_changed(self, pict):
        self.__select_pict(pict)
        pass

    def __select_pict(self, pict):
        model = self.tv_gal_picts.get_model()
        for row in model:
            if pict == row[self.GAL_CLMN_PICT]:
                self.tv_gal_picts.set_cursor(row.path)
                break
            pass
        pass

    def __load_album(self, album):
        self.album = album
        
        if album.props.__dict__.has_key("web_gal_name"):
            web_gal_name = album.props.web_gal_name
        else:
            web_gal_name = album.props.name
            album.props.web_gal_name = album.props.name
            pass
        self.ent_gal_title.set_text(web_gal_name)
        
        model = gtk.ListStore(*self.tv_gal_clmn_types)
        for pict in album.picts:
            if pict.props.__dict__.has_key("web_gal_included"):
                web_gal_included = pict.props.web_gal_included
            else:
                pict.props.web_gal_included = True
                web_gal_included = True
                pass
            model.append((pict, web_gal_included, pict.props.name))
            pass
        self.tv_gal_picts.set_model(model)
        pass

    def __load_template(self):
        f = open(os.path.join(self.dir, "templates/simple/layout.html"), "r")
        self.templ_layout = f.read()
        f.close()
        f = open(os.path.join(self.dir, "templates/simple/photo.html"), "r")
        self.templ_photo = f.read()
        f.close()
        pass

    def __create_photo_html(self, pict_normal, pict, prev_pict=None, next_pict=None):
        # prev photo
        if prev_pict:
            fname = prev_pict.props.name[:-4] + ".html"
            photo = self.templ_photo.replace("%PREV%", '<a href="%s">Prev</a>' % fname)
        else:
            photo = self.templ_photo.replace("%PREV%", "prev")
            pass

        # main
        photo = photo.replace("%MAIN%", '<a href="index.html">Main</a>')

        # next photo
        if next_pict:
            fname = next_pict.props.name[:-4] + ".html"
            photo = photo.replace("%NEXT%", '<a href="%s">Next</a>' % fname)
        else:
            photo = photo.replace("%NEXT%", "next")
            pass

        photo = photo.replace("%NAME%", pict.props.name[:-4])
        photo = photo.replace("%PHOTO%", "%s" % pict_normal)
        f = open(pict.props.www_pict_html, "w")
        f.write(photo.encode("iso-8859-2"))
        f.close()
        pass

    def __create_htmls(self):
        main = self.templ_layout.replace("%TITLE%", self.ent_gal_title.get_text())
        picts = ""

        album_dir = self.album.dir
        www_dir = os.path.join(album_dir, "www")
        if not os.path.exists(www_dir):
            os.mkdir(www_dir)
            pass

        model = self.tv_gal_picts.get_model()
        prev_pict = None
        for row in model:
            pict = row[self.GAL_CLMN_PICT]

            if not pict.props.web_gal_included:
                continue

            next_pict = None
            idx = pict.album.picts.index(pict) + 1
            if idx < len(pict.album.picts):
                for p in pict.album.picts[idx:]:
                    if p.props.web_gal_included:
                        next_pict = p
                        break
                    pass
                pass

            pict_name = pict.props.name[:-4]
            pict_normal = pict_name + "-pict.jpg"
            pict_thumb = pict_name + "-thumb.jpg"
            pict_html = pict_name + ".html"

            pict.props.www_pict_normal = os.path.join(www_dir,
                                                      pict_normal).encode("iso-8859-2")
            pict.props.www_pict_thumb = os.path.join(www_dir,
                                                     pict_thumb).encode("iso-8859-2")
            pict.props.www_pict_html = os.path.join(www_dir,
                                                    pict_html).encode("iso-8859-2")

            if not os.access(pict.props.www_pict_html, os.F_OK):
                self.__create_photo_html(pict_normal, pict, prev_pict, next_pict)
                pass

            if not os.access(pict.props.www_pict_normal, os.F_OK):
                os.system("convert -resize 400x300 '%s' '%s'" %
                          (pict.pathfilename,
                           pict.props.www_pict_normal))
                pass
            if not os.access(pict.props.www_pict_thumb, os.F_OK):
                os.system("convert -resize 80x60 '%s' '%s'" %
                          (pict.props.www_pict_normal,
                           pict.props.www_pict_thumb))
                pass

            picts = picts + '<a href="%s"><img src="%s"/></a>\n' % (pict_html, pict_thumb)

            prev_pict = pict
            pass
        
        main = main.replace("%CONTENT%", picts)
        f = open(os.path.join(www_dir, "index.html"), "w")
        f.write(main.encode("iso-8859-2"))
        f.close()
        pass

    def on_tv_gal_pict_toggled(self, widget, path):
        model = self.tv_gal_picts.get_model()
        iter = model.get_iter(path)
        pict = model.get_value(iter, self.GAL_CLMN_PICT)
        pict.props.web_gal_included = not pict.props.web_gal_included
        model.set_value(iter, self.GAL_CLMN_MARK, pict.props.web_gal_included)
        print "Toggle pict %d" % pict.props.web_gal_included
        pass
    
    def on_btn_create_gal_clicked(self, widget):
        self.__load_template()
        self.__create_htmls()
        pass

    def on_ent_gal_title_focus_out_event(self, widget, event):
        print "done"
        self.album.props.web_gal_name = self.ent_gal_title.get_text()
        pass

    def on_tv_gal_picts_drag_data_received(self, widget, context, x, y, selection_data, info, timestamp):
        print sys._getframe().f_code.co_name
        dest = self.tv_gal_picts.get_dest_row_at_pos(x, y)
        print "dest "+str(dest)
        context.finish(gtk.TRUE, gtk.FALSE, timestamp)
        chapter = self.gofoto.albumCollection.get_chapter(selection_data.data)
        if chapter != None:
            self.tv_gal_picts.get_model().append(None, [chapter.props.name, chapter])
            if self.ent_gal_title.get_text() == "":
                self.ent_gal_title.set_text(chapter.album.props.name)
                pass
            pass
        return 0

main_class = WebGallery
