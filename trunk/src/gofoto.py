#!/usr/bin/python

#
# GOFoto 0.0.1 - a photo manager application
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


import logging
logging.basicConfig()
log = logging.getLogger("gofoto")
log.setLevel(logging.DEBUG)
log = logging.getLogger("gofoto")


def appdir(path):
    return os.path.join(os.path.dirname(sys.argv[0]), path)

class Properties:
    def save(self, doc, xml_base):
        xml = doc.createElement("props")
        xml_base.appendChild(xml)
        for key in self.__dict__.keys():
            #print "%s = %s" % (str(key), str(self.__dict__[key]))
            type = self.__dict__[key].__class__.__name__
            if type == "int":
                node_key = doc.createElement(key)
                xml.appendChild(node_key)
                node_key.setAttribute("type", "int")
                node_key.setAttribute("value", str(self.__dict__[key]))
            elif type == "str":
                node_key = doc.createElement(key)
                xml.appendChild(node_key)
                node_key.setAttribute("type", "str")
                node_key.setAttribute("value", self.__dict__[key])
            elif type == "unicode":
                node_key = doc.createElement(key)
                xml.appendChild(node_key)
                node_key.setAttribute("type", "unicode")
                node_key.setAttribute("value", self.__dict__[key])
            elif type == "bool":
                node_key = doc.createElement(key)
                xml.appendChild(node_key)
                node_key.setAttribute("type", "bool")
                node_key.setAttribute("value", str(self.__dict__[key]))
            elif type == "list":
                list = self.__dict__[key]
                subtype = list[0].__class__.__name__
                if subtype == "int":
                    for el in list:
                        node_key = doc.createElement(key)
                        xml.appendChild(node_key)
                        node_key.setAttribute("type", "int")
                        node_key.setAttribute("value", str(el))
                        pass
                    pass
                elif subtype == "str":
                    for el in list:
                        node_key = doc.createElement(key)
                        xml.appendChild(node_key)
                        node_key.setAttribute("type", "str")
                        node_key.setAttribute("value", el)
                        pass
                    pass
                elif subtype == "unicode":
                    for el in list:
                        node_key = doc.createElement(key)
                        xml.appendChild(node_key)
                        node_key.setAttribute("type", "unicode")
                        node_key.setAttribute("value", el)
                        pass
                    pass
                elif subtype == "bool":
                    for el in list:
                        node_key = doc.createElement(key)
                        xml.appendChild(node_key)
                        node_key.setAttribute("type", "bool")
                        node_key.setAttribute("value", str(el))
                        pass
                    pass
                else:
                    log.error("unhandled type %s in list for field %s" % (subtype, key))
                    pass
                pass
            else:
                log.error("ERROR: unhandled type %s for field %s" % (type, key))
                pass
            pass
        pass

    def load(self, xml):
        props = xml.getElementsByTagName("props")[0]
        node = props.firstChild
        while node != None and node.nodeType != xml.ELEMENT_NODE:
            node = node.nextSibling
            pass
        while node != None:
            type = node.getAttribute("type")
            if type == "int":
                value = int(node.getAttribute("value"))
            elif type == "str":
                value = str(node.getAttribute("value"))
            elif type == "unicode":
                value = unicode(node.getAttribute("value"))
            elif type == "bool":
                val = node.getAttribute("value")
                if val == "False":
                    value = False
                else:
                    value = True
                    pass
                pass

            #print "%s = %s" % (str(node.nodeName), str(value))

            if self.__dict__.has_key(node.nodeName):
                if self.__dict__[node.nodeName].__class__.__name__ == "list":
                    self.__dict__[node.nodeName].append(value)
                else:
                    tmp = self.__dict__[node.nodeName]
                    self.__dict__[node.nodeName] = []
                    self.__dict__[node.nodeName].append(tmp)
                    self.__dict__[node.nodeName].append(value)
                    pass
                pass
            else:
                self.__dict__[node.nodeName] = value
                pass

            node = node.nextSibling
            while node != None and node.nodeType != xml.ELEMENT_NODE:
                node = node.nextSibling
                pass
            pass
        pass
    pass

class Pict:
    def __init__(self, album, arg):
        self.album = album
        self.props = Properties()

        if arg.__class__.__name__ == "str":
            self.props.vertical = False
            self.props.marked = False
            self.props.filename = arg
            self.props.name = os.path.basename(self.props.filename)
        elif arg.__class__.__name__ == "Element":
            pict_xml = arg
            self.props.load(pict_xml)
            pass
        self.big = None
        #self.reload()
        pass

    def reload(self):
        self.small = gtk.gdk.pixbuf_new_from_file_at_size(self.props.filename, 50, 50)
        self.big = None
        pass

    def save(self, doc, xml):
        pict_xml = doc.createElement("pict")
        xml.appendChild(pict_xml)
        self.props.save(doc, pict_xml)
        pass

class Chapter:
    def __init__(self, album, chpt_xml=None, dir=None):
        self.album = album
        self.props = Properties()
        self.picts = []

        if chpt_xml == None:
            self.props.mp3_name = ""
            self.props.marked = False

            self.props.color = "#%02x%02x%02x" % (random.randint(0, 255),
                                                  random.randint(0, 255),
                                                  random.randint(0, 255))
            self.props.name = "Chapter %d" % (len(self.album.chapters) + 1)

            if dir != None:
                list = filter(lambda f: f.count(".jpg") > 0, os.listdir(dir))
                list.sort()
                for f in list:
                    self.picts.append(Pict(self, os.path.join(dir, f)))
                    pass
                pass
            pass
        else:
            self.props.load(chpt_xml)
            pass

        pass

    def change_name(self, name):
        self.props.name = name
        pass

    def save(self, doc, xml):
        chpt_xml = doc.createElement("chapter")
        xml.appendChild(chpt_xml)
        self.props.save(doc, chpt_xml)

        # save picts
        for pict in self.picts:
            pict.save(doc, chpt_xml)
            pass
        pass

class Album:
    def __init__(self, arg):
        if not arg:
            raise Exception("Bad argument to Album constructor")

        self.props = Properties()
        self.picts = []

        if arg.__class__.__name__ == "Element":
            alb_xml = arg
            # read data from xml
            self.props.load(alb_xml)
        elif arg.__class__.__name__ == "str":
            dir = arg
            # read data from directory
            self.props.marked = False
            self.props.dir = os.path.abspath(dir)
            self.props.name = os.path.basename(self.props.dir)
            list = filter(lambda f: f.count(".jpg") > 0, os.listdir(dir))
            list.sort()
            for f in list:
                self.picts.append(Pict(self, os.path.join(dir, f)))
                pass
            pass
        pass

    def save(self):
        doc = xml.dom.minidom.Document()

        alb_xml = doc.createElement("gofoto")
        doc.appendChild(alb_xml)
        self.props.save(doc, alb_xml)

        # save chapters
        for pict in self.picts:
            pict.save(doc, alb_xml)
            pass

        f = open(os.path.join(self.props.dir, ".gofoto"), "w")
        xmlstring = doc.toprettyxml()
        f.write(xmlstring)
        f.close()
        #print xmlstring
        log.info("Album saved")
        pass


CLMN_MARK = 0
CLMN_NAME = 1
#CLMN_PICT = 2

class AlbumCollection:
    def __init__(self):
        self.albums = []
        self.model = gtk.TreeStore(gobject.TYPE_PYOBJECT)

        self.album_cond = threading.Condition()
        self.albums_to_load = []
        self.images_loader_stop = threading.Event()
        self.images_loader_stop.clear()
        self.thread = threading.Thread(target=self.__images_loader)
        self.thread.start()
        pass

    def close(self):
        self.images_loader_stop.set()
        self.album_cond.acquire()
        self.album_cond.notify()
        self.album_cond.release()
        self.thread.join()
        pass

    def new_album(self, dir):
        album = Album(dir)
        self.albums.append(album)
        self.__load_album_images(album)      
        self.__fill_model(album)
        return album

    def __fill_model(self, album):
        parent_album = self.model.append(None, [album])
        for p in album.picts:
            self.model.append(parent_album, [p])
            pass
        pass

    def path2str(self, path):
        s = ""
        for i in path:
            s = s + str(i)+":"
            pass
        return s[:-1]

    def get_pict(self, path):
        if path.__class__.__name__ == "str":
            iter = self.model.get_iter_from_string(path)
        elif path.__class__.__name__ in ["list", "tuple"]:
            iter = self.model.get_iter(path)
        else:
            return None
        pict = self.model.get_value(iter, 0)
        if pict == None or pict.__class__.__name__ != "Pict":
            return None
        else:
            return pict
        pass

    def get_chapter(self, path):
        if path.__class__.__name__ == "str":
            iter = self.model.get_iter_from_string(path)
        elif path.__class__.__name__ in ["list", "tuple"]:
            iter = self.model.get_iter(path)
        else:
            return None
        chapter = self.model.get_value(iter, 0)
        if chapter == None or chapter.__class__.__name__ != "Chapter":
            return None
        else:
            return chapter
        pass

    def move_picts(self, pict_paths, chpt_path):
        ch_iter = self.model.get_iter(chpt_path)
        if ch_iter == None:
            return
        chapter = self.model.get_value(ch_iter, 0)
        if chapter == None or chapter.__class__.__name__ != "Chapter":
            return None
        iters = []
        for p in pict_paths:
            # take pict
            p_iter = self.model.get_iter_from_string(p)
            if p_iter == None:
                continue
            pict = self.model.get_value(p_iter, 0)
            if pict == None or pict.__class__.__name__ != "Pict":
                continue
            # remove from old chapter
            pict.chapter.picts.remove(pict)
            iters.append(p_iter)
            # add to new chapter
            pict.chapter = chapter
            chapter.picts.append(pict)
            self.model.append(ch_iter, [pict])
            pass
        # remove from model (remove here to not broke provided path)
        for p in iters:
            self.model.remove(p)
            pass
        pass

    def get_album_by_path(self, path):
        if path.__class__.__name__ == "str":
            iter = self.model.get_iter_from_string(path)
        elif path.__class__.__name__ in ["list", "tuple"]:
            iter = self.model.get_iter(path)
        else:
            return None
        album = self.model.get_value(iter, 0)
        if album == None or album.__class__.__name__ != "Album":
            return None
        else:
            return album
        pass

    def get_album_by_name(self, name):
        print "find album %s" % name
        for a in self.albums:
            if a.props.name == name:
                return a
            pass
        return None

    debug = False
    def dbgf(self, txt):
        if AlbumCollection.debug:
            print txt
            pass
        pass

    def __images_loader(self):
        while not self.images_loader_stop.isSet():
            self.album_cond.acquire()
            while len(self.albums_to_load) == 0 and not self.images_loader_stop.isSet():
                self.album_cond.wait()
                pass

            if self.images_loader_stop.isSet():
                self.album_cond.release()
                log.info("Image loader closed")
                return

            album = self.albums_to_load.pop(0)
            
            self.album_cond.release()
            
            log.debug("load_images start %f" % time.time())
            for pict in album.picts:
                if self.images_loader_stop.isSet():
                    log.info("Image loader closed")
                    return
                pict.reload()
                pass
            log.debug("load_images end %f" % time.time())
            pass
        log.info("Image loader closed")
        pass

    def __load_album_images(self, album):
        self.album_cond.acquire()
        self.albums_to_load.append(album)
        self.album_cond.notify()
        self.album_cond.release()
        pass

    def append_album(self, doc):
        # album
        alb_xml = doc.getElementsByTagName("gofoto")[0]
        album = Album(alb_xml)
        self.albums.append(album)
        
        # picts
        for pict_xml in alb_xml.getElementsByTagName("pict"):
            album.picts.append(Pict(album, pict_xml))
            pass

        self.__load_album_images(album)      
        self.__fill_model(album)
        pass

class AlbumsBrowser:
    def __init__(self, gofoto):
        self.xml = gofoto.xml
        self.gofoto = gofoto
        self.albumCollection = gofoto.albumCollection

        self.curr_album = None
        self.curr_pict = None

        self.tv_images = self.xml.get_widget("tv_images")
        #self.ctxmnu_images = self.xml.get_widget("ctxmnu_images")

        self.xml.signal_autoconnect({
            "on_tv_images_cursor_changed": self.on_tv_images_cursor_changed,
            "on_tv_images_button_press_event": self.on_tv_images_button_press_event,
            "on_tv_images_drag_data_get": self.on_tv_images_drag_data_get,
            "on_tv_images_drag_data_received": self.on_tv_images_drag_data_received,
            "on_tv_images_row_expanded": self.on_tv_images_row_expanded})
#            "on_tv_images_test_expand_row": self.on_tv_images_test_expand_row,

        renderer = gtk.CellRendererToggle() # Mark
        renderer.connect("toggled", self.on_tv_images_toggled)
        clmn = gtk.TreeViewColumn("Mark", renderer)
        clmn.set_cell_data_func(renderer, self.cell_func, CLMN_MARK)
        #self.tv_images.append_column(clmn)

        clmn = gtk.TreeViewColumn("Album / Pict")
        
        renderer = gtk.CellRendererPixbuf() # Icon
        clmn.pack_start(renderer)
        clmn.set_cell_data_func(renderer, self.cell_func, CLMN_NAME)
        
        renderer = gtk.CellRendererText()   # Album
        renderer.connect("edited", self.cell_edited)
        clmn.pack_start(renderer)
        clmn.set_cell_data_func(renderer, self.cell_func, CLMN_NAME)
        
        self.tv_images.append_column(clmn)
        self.tv_images.set_expander_column(clmn)
        #clmn = gtk.TreeViewColumn("Icon", renderer)
        #clmn.set_cell_data_func(renderer, self.cell_func, CLMN_PICT)
        #self.tv_images.append_column(clmn)

        self.tv_images.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.tv_images.enable_model_drag_source(gtk.gdk.BUTTON1_MASK,
                                                [('text/plain', 0, 0)],
                                                gtk.gdk.ACTION_DEFAULT |
                                                gtk.gdk.ACTION_MOVE)
        self.tv_images.enable_model_drag_dest([('MY_TREE_MODEL_ROW', 0, 0),
                                               ('text/plain', 0, 1),
                                               ('TEXT', 0, 2),
                                               ('STRING', 0, 3)],
                                              gtk.gdk.ACTION_DEFAULT)

        self.tv_images.set_model(self.albumCollection.model)
        pass

    def cell_edited(self, widget, path, new_text):
        log.debug("cell_edited "+str(path)+" "+str(new_text))
        iter = self.albumCollection.model.get_iter(path)
        obj = self.albumCollection.model.get_value(iter, 0)
        if obj.__class__.__name__ == "Album":
            obj.name = new_text
        elif obj.__class__.__name__ == "Chapter":
            obj.change_name(new_text)
            pass
        pass

    def cell_func(self, column, cell, model, iter, clmn_number):
        obj = model.get_value(iter, 0)
        #print "cell func clmn:%d obj:%s" % (clmn_number, obj.__class__.__name__)
        if clmn_number == CLMN_MARK:
            if obj.__class__.__name__ in ["Album", "Chapter"]:
                cell.set_property("active", obj.props.marked)
                cell.set_property("activatable", True)
            else:
                cell.set_property("active", False)
                cell.set_property("activatable", False)
                pass
            pass
        elif clmn_number == CLMN_NAME:
            if obj.__class__.__name__ == "Album":
                if cell.__class__ == gtk.CellRendererText:
                    cell.set_property("text", obj.props.name)
                    cell.set_property('editable', True)
                elif cell.__class__ == gtk.CellRendererPixbuf:
                    cell.set_property("pixbuf", None)
                    pass
            elif obj.__class__.__name__ == "Pict":
                if cell.__class__ == gtk.CellRendererText:
                    cell.set_property("text", obj.props.name)
                    cell.set_property('editable', False)
                elif cell.__class__ == gtk.CellRendererPixbuf:
                    if obj.__dict__.has_key("small"):
                        cell.set_property("pixbuf", obj.small)
                    else:
                        cell.set_property("pixbuf", None)
                        pass
                    pass
                pass
            pass
#        elif clmn_number == CLMN_PICT:
#            if obj.__class__.__name__ == "Pict":
#                if obj.__dict__.has_key("small"):
#                    cell.set_property("pixbuf", obj.small)
#                    pass
#                pass
#            else:
#                cell.set_property("pixbuf", None)
#                pass
#            pass
        pass
    pass

    def on_tv_images_toggled(self, widget, path):
        print "on_tv_images_toggled "+str(path)
        iter = self.albumCollection.model.get_iter(path)
        obj = self.albumCollection.model.get_value(iter, 0)
        print obj.__class__.__name__
        if obj.__class__.__name__ in ["Album", "Chapter"]:
            obj.props.marked = not obj.props.marked
            pass
        pass

    def on_tv_images_test_expand_row(self, widget, iter, path):
        log.debug("expand")
        return gtk.FALSE

    def on_tv_images_cursor_changed(self, widget):
        model, paths = self.tv_images.get_selection().get_selected_rows()
        if paths == []:
            return
        pict = self.albumCollection.get_pict(paths[0])
        album = self.albumCollection.get_album_by_path(paths[0])
        if album == None and pict != None:
            album = pict.album
            pass

        pict_changed = False
        if self.curr_pict != pict:
            self.curr_pict = pict
            pict_changed = True
            pass

        album_changed = False
        if self.curr_album != album:
            self.curr_album = album
            album_changed = True
            pass

        if album_changed:
            self.gofoto.pluginManager.event("ev_album_changed", album)
            pass

        if pict_changed:
            self.gofoto.pluginManager.event("ev_pict_changed", pict)
            pass
        
        pass

    def on_tv_images_button_press_event(self, widget, event):
        if event.button == 3:
            model, paths = self.tv_images.get_selection().get_selected_rows()
            if paths == []:
                return gtk.TRUE
            #if self.albumCollection.get_album_by_path(paths[0]) != None:
            #    self.ctxmnu_images.popup(None, None, None, event.button, event.time)
            #    pass
            return gtk.TRUE
        return gtk.FALSE

    def on_tv_images_drag_data_get(self, treeview, context, selection, info, timestamp):
        print "on_tv_images_drag_data_get"
        treeselection = treeview.get_selection()
        model, paths = treeselection.get_selected_rows()
        path2str = self.albumCollection.path2str
        str_paths = ""
        for p in paths:
            str_paths = str_paths + " " + path2str(p)
            pass
        selection.set('text/plain', 8, str_paths)
        return

    def on_tv_images_drag_data_received(self, widget, context, x, y, selection_data, info, timestamp):
        print "on_tv_images_drag_data_received"
        dest = self.tv_images.get_dest_row_at_pos(x, y)
        print "dest "+str(dest)
        path, position = dest
        context.finish(gtk.TRUE, gtk.FALSE, timestamp)
        paths = selection_data.data.split()
        print str(paths)
        self.albumCollection.move_picts(paths, path)
        return 0

    def on_tv_images_row_expanded(self, widget, iter, path):
        log.debug("expanded")
                
        pass

    def get_current_album(self):
        return self.curr_album
        # old
        #model, paths = self.tv_images.get_selection().get_selected_rows()
        #alb_path = str(paths[0][0])
        #return self.albumCollection.get_album_by_path(alb_path)

    def select_pict_relative(self, offset):
        model, paths = self.tv_images.get_selection().get_selected_rows()
        log.debug("Select: from path "+str(paths[0]))
        path = paths[0]
        if len(path) != 2:
            log.warning("Paths len %d != 3" % len(path))
            return
        path = (path[0], path[1] + offset)
        if path[1] < 0:
            log.warning("idx %d < 0" % path[1])
            return
        log.debug("Select: to path "+str(path))
        try:
            iter = model.get_iter(path)
        except ValueError:
            log.error("Path %s doesn't exist" % str(path))
            return
        pict = model.get_value(iter, 0)
        if pict == None or pict.__class__ != Pict:
            log.warning("obj is None or class:%s != Pict" % pict.__class__.__name__)
            return
        self.tv_images.get_selection().unselect_all()
        self.tv_images.get_selection().select_iter(iter)
        self.gofoto.pluginManager.event("ev_pict_changed", pict)
        pass

    def get_selected_picts(self):
        model, paths = self.tv_images.get_selection().get_selected_rows()
        return [ self.albumCollection.get_pict(p) for p in paths ]


#class Logger:
#    def log(self, txt):
#        print "%s: %s: %s" % (self.__class__.__name__, sys._getframe(1).f_code.co_name, txt)
#        pass

class PluginManager:
    def __init__(self, gofoto):
        self.gofoto = gofoto
        self.plugins = {}
        self.__load_plugin(PhotoRefining)
        self.__load_plugin(WebGallery)
        self.__load_plugin(VideoCD)
        self.active_plugin = PhotoRefining.__name__
        pass

    def __load_plugin(self, klass):
        page_idx = len(self.plugins)
        self.plugins[klass.__name__] = klass(self.gofoto,
                                             self.gofoto.xml,
                                             page_idx,
                                             self.gofoto.notebook.get_nth_page(page_idx))
        pass

    def event(self, event_name, *args):
        self.plugins[self.active_plugin].event(event_name, *args)
        pass

    def switch_active_plugin(self, page_idx):
        for key in self.plugins.keys():
            if self.plugins[key].page_idx == page_idx:
                self.active_plugin = key
                self.event("ev_activate_plugin")
                log.info("activated plugin %s" % key)
                return
            pass
        log.error("ERROR: could not find plugin for activation")
        pass

class Plugin:
    def event(self, event_name, *args):
        if self.__class__.__dict__.has_key(event_name):
            self.__class__.__dict__[event_name](self, *args)
            pass
        pass

    
    
class Gofoto:
    def __init__(self):
        #xml.signal_autoconnect(locals())

        gtk.threads_init()

        self.albumCollection = AlbumCollection()

        self.xml = gtk.glade.XML(appdir("gofoto.glade"))

        self.file_chooser_dialog = self.xml.get_widget("file_chooser_dialog")
        self.notebook = self.xml.get_widget("notebook")

        self.xml.signal_autoconnect({
            "on_gofoto_destroy": self.close_application,
            "on_save_activate": self.on_save_activate,
            "on_new_album_activate": self.on_new_album_activate,
            "on_notebook_switch_page": self.on_notebook_switch_page})

        self.albumsBrowser = AlbumsBrowser(self)

        self.pluginManager = PluginManager(self)

        self.load_collection()

        #gtk.timeout_add(400, self.load_dir_files().next)
        gtk.main()
        pass

    def close_application(self, widget):
        log.info("Closing gofoto")
        self.albumCollection.close()
        gtk.main_quit()
        pass

    def on_add_chapter_activate(self, widget):
        print "on_add_chapter_activate"
        model, paths = self.tv_images.get_selection().get_selected_rows()
        if paths == []:
            return
        iter = model.get_iter(paths[0])
        album = model.get_value(iter, 0)
        ch = Chapter(album)
        album.chapters.append(ch)
        self.albumCollection.model.append(iter, [ch])
        self.tv_images.set_cursor(paths[0], self.tv_images.get_column(CLMN_NAME),gtk.TRUE)
        pass

    def on_delete_chapter_activate(self, widget):
        pass

    def on_notebook_switch_page(self, widget, page, page_idx):
        log.debug("on_notebook_switch_page "+str(page_idx))
        self.pluginManager.switch_active_plugin(page_idx)
        pass

    def on_save_activate(self, widget):
        album = self.albumsBrowser.get_current_album()
        if album:
            album.save()
            pass
        pass

    def on_new_album_activate(self, widget):
        self.file_chooser_dialog.set_action(gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
        self.file_chooser_dialog.set_title("Choose directory with photos")
        self.file_chooser_dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        self.file_chooser_dialog.add_button(gtk.STOCK_OPEN, gtk.RESPONSE_OK)
        response = self.file_chooser_dialog.run()
        self.file_chooser_dialog.hide()
        if response == gtk.RESPONSE_OK:
            dir_name = self.file_chooser_dialog.get_current_folder()
            album = self.albumCollection.new_album(dir_name)
            album.save()
            self.save_collection()
        pass

    def save_collection(self):
        f = open(os.path.expanduser("~/.gofotorc"), "w")
        for album in self.albumCollection.albums:
            f.write(album.props.dir+"\n")
            pass
        f.close()
        pass

    def load_collection(self):
        rc = os.path.expanduser("~/.gofotorc")
        if not os.access(rc, os.F_OK):
            return
        f = open(rc, "r")
        dir = f.readline().strip()
        log.debug("load_collection start %f" % time.time())
        while dir:
            doc = xml.dom.minidom.parse(os.path.join(dir, ".gofoto"))

            self.albumCollection.append_album(doc)

            dir = f.readline().strip()
            pass # end while dir
        log.debug("load_collection end %f" % time.time())
        f.close()
        pass

class PhotoRefining(Plugin):
    def __init__(self, gofoto, xml, page_idx, page):
        self.gofoto = gofoto
        self.xml = xml
        self.page_idx = page_idx
        self.page = page

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
            pict.big = gtk.gdk.pixbuf_new_from_file_at_size(pict.props.filename, 600, 500)
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
        dir = pict.album.props.dir

        # make backup
        orig_dir = os.path.join(dir, "orig")
        orig_file = os.path.join(dir, "orig", pict.props.name)
        if not os.path.exists(orig_dir):
            os.mkdir(orig_dir)
            pass
        if not os.access(orig_file, os.F_OK):
            os.system("cp '%s' '%s'" % (pict.props.filename, orig_file))
            pict.props.orig = orig_file
            pass

        dest = os.path.join(dir, "tmp-"+pict.props.name)
        # perform operation
        if operation == "rotate left":
            #os.system("convert -rotate -90 "+pict.name+" "+pict.name)
            os.system("jpegtran -rotate 270 -trim '%s' > '%s' && mv '%s' '%s'" %
                      (pict.props.filename, dest, dest, pict.props.filename))
            pass
        elif operation == "rotate right":
            #os.system("convert -rotate 90 "+pict.name+" "+pict.name)
            os.system("jpegtran -rotate 90 -trim '%s' > '%s' && mv '%s' '%s'" %
                      (pict.props.filename, dest, dest, pict.props.filename))
            pass
        elif operation == "despeckle":
            os.system("convert -despeckle '%s' '%s'" % (pict.props.filename,
                                                        pict.props.filename))
            pass
        elif operation == "get orig":
            os.system("mv '%s' '%s'" % (pict.props.orig, pict.props.filename))
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

    def ev_pict_changed(self, pict):
        if not pict:
            return
        self.image.set_from_pixbuf(self.__get_big(pict))
        self.chkbtn_pict_vertical.set_active(pict.props.vertical)
        pass


class WebGallery(Plugin):
    GAL_CLMN_PICT = 0
    GAL_CLMN_MARK = 1
    GAL_CLMN_NAME = 2
    def __init__(self, gofoto, xml, page_idx, page):
        self.gofoto = gofoto
        self.xml = xml
        self.page_idx = page_idx
        self.page = page

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
            pass
        pass

    def ev_album_changed(self, album):
        self.__load_album(album)
        pass

    def ev_pict_changed(self, pict):
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
        f = open("templ/layout.html", "r")
        self.templ_layout = f.read()
        f.close()
        f = open("templ/photo.html", "r")
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

        album_dir = self.album.props.dir
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
                          (pict.props.filename,
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

class VideoCD(Plugin):
    VCD_CLMN_NAME = 0
    VCD_CLMN_CHTR = 1
    def __init__(self, gofoto, xml, page_idx, page):
        self.gofoto = gofoto
        self.xml = xml
        self.page_idx = page_idx
        self.page = page

        self.file_chooser_dialog = self.xml.get_widget("file_chooser_dialog")
        self.ent_music = self.xml.get_widget("ent_music")
        self.tv_vcd_chapters = self.xml.get_widget("tv_vcd_chapters")

        self.xml.signal_autoconnect({
            "on_btn_chapters_remove_clicked": self.on_btn_chapters_remove_clicked,
            "on_btn_create_mpegs_clicked": self.on_btn_create_mpegs_clicked,
            "on_btn_build_cd_clicked": self.on_btn_build_cd_clicked,
            "on_btn_choose_music_clicked": self.on_btn_choose_music_clicked,
            "on_btn_chapters_play_clicked": self.on_btn_chapters_play_clicked,
            "on_btn_sound_play_clicked": self.on_btn_sound_play_clicked,
            "on_btn_play_vcd_clicked": self.on_btn_play_vcd_clicked,
            "on_tv_vcd_chapters_cursor_changed": self.on_tv_vcd_chapters_cursor_changed,
            "on_tv_vcd_chapters_drag_data_received": self.on_tv_vcd_chapters_drag_data_received})

        renderer = gtk.CellRendererText()   # Chapter
        clmn = gtk.TreeViewColumn("Album / Chapter", renderer, text=self.VCD_CLMN_NAME)
        self.tv_vcd_chapters.append_column(clmn)

        model = gtk.TreeStore(gobject.TYPE_STRING,
                              gobject.TYPE_PYOBJECT)
        self.tv_vcd_chapters.set_model(model)

        self.tv_vcd_chapters.enable_model_drag_dest([('MY_TREE_MODEL_ROW', 0, 0),
                                                     ('text/plain', 0, 1),
                                                     ('TEXT', 0, 2),
                                                     ('STRING', 0, 3)],
                                                    gtk.gdk.ACTION_DEFAULT)

        pass

    def on_btn_chapters_remove_clicked(self, widget):
        print "remove"
        model, iter = self.tv_vcd_chapters.get_selection().get_selected()
        model.remove(iter)
        pass

    def on_btn_create_mpegs_clicked(self, widget):
        print "create mpegs"

        for row in self.tv_vcd_chapters.get_model():
            chapter = row[self.VCD_CLMN_CHTR]
            mpeg_dir = os.path.join(chapter.album.props.dir, "mpeg")
            chapter.mpeg_dir = mpeg_dir
            if not os.path.exists(mpeg_dir):
                os.mkdir(mpeg_dir)
                pass
            esc_name = chapter.props.name.replace(" ", "_")
            chapter.esc_name = esc_name
            chapter.props.mpg_name = os.path.join(mpeg_dir, ("mpg-"+esc_name+".mpg"))
            chapter.props.sound_name = os.path.join(mpeg_dir, ("snd-"+esc_name+".mp2"))
            chapter.props.video_name = os.path.join(mpeg_dir, ("vid-"+esc_name+".m2v"))

            self.__create_mpeg(chapter)
            pass
        print "mpegs are created"
        pass

    def __check_sound(self, chapter):
        chapter.wav_name_in = os.path.join(chapter.mpeg_dir,
                                           chapter.esc_name+"-in.wav")
        chapter.props.wav_name = os.path.join(chapter.mpeg_dir,
                                              chapter.esc_name+".wav")
        wav_cmd = "madplay '%s' --output=wave:'%s'"
        join_wav = "qwavjoin -o '%s' '%s'"
        cut_wav = "qwavcut -d -B %ds '%s'"
        mp2_cmd = "toolame -b 224 -s 44.1 -m s '%s' '%s'"
        mplex_cmd = "mplex -f 4 -o '%s' '%s'"

        print " creating sound %s" % chapter.props.sound_name
        if os.access(chapter.props.sound_name, os.F_OK):
            print " sound %s already exists" % chapter.props.sound_name
            return

        # convert mp3 to wave
        os.system(wav_cmd % (chapter.props.mp3_name, chapter.wav_name_in))

        # cut the wave
        w = wave.open(chapter.wav_name_in, "rb")
        wav_len = w.getnframes()/w.getframerate() # wave length in seconds
        video_len = len(chapter.picts)*5             # chapter length in seconds
        if wav_len > video_len: # cut the wave
            chapter.props.wav_name = chapter.wav_name_in
            os.system(cut_wav % (video_len, chapter.props.wav_name))
            pass
        elif wav_len < video_len:   # extend the wave
            multi = video_len / wav_len
            files_in = ""
            for i in range(0, multi + 1):
                files_in = files_in + chapter.wav_name_in + " "
                pass
            os.system(join_wav % (chapter.props.wav_name, files_in))
            os.system(cut_wav % (video_len, chapter.props.wav_name))
            pass

        # convert wave to mp2
        os.system(mp2_cmd % (chapter.props.wav_name, chapter.props.sound_name))

        # delete temp files
        if os.access(chapter.props.wav_name, os.F_OK):
            os.unlink(chapter.props.wav_name)
            pass
        if os.access(chapter.wav_name_in, os.F_OK):
            os.unlink(chapter.wav_name_in)
            pass
        pass

    def __check_picts(self, chapter):
        print "  converting picts.."
        convert_cmd1 = "convert -resize 704x576! '%s' '%s'"
        convert_cmd2 = "convert -resize 704x576  '%s' '%s'"
        convert_cmd3 = "convert -border %dx0 -bordercolor black '%s' '%s'"

        duration = 5*25 # 5 seconds * 25 fps
        i = 0
        for pict in chapter.picts:
            tmp_pict = os.path.join(chapter.mpeg_dir,
                                    "pict-%s-%03d-%s" % (chapter.esc_name,
                                                         i,
                                                         pict.props.name))
            if not os.access(tmp_pict, os.F_OK):
                print "  convert pict %s" % tmp_pict
                if not pict.props.vertical:
                    os.system(convert_cmd1 % (pict.props.name, tmp_pict))
                else:
                    os.system(convert_cmd2 % (pict.props.name, tmp_pict))
                    width = PIL.Image.open(tmp_pict).size[0]
                    os.system((convert_cmd3 % ((704-width)/2), tmp_pict, tmp_pict))
                    pass
                pass
            else:
                print "  pict %s already exists" % tmp_pict
                pass
            for j in range(0, duration):
                slink = os.path.join(chapter.mpeg_dir,
                                     "pict-%s-%04d.jpg" % (chapter.esc_name,
                                                           i*duration+j))
                os.system("ln -s '%s' '%s'" % (tmp_pict, slink))
                pass
            i = i + 1
            pass
        pass

    def __rm_picts_links(self, chapter):
        duration = 5*25 # 5 seconds * 25 fps
        i = 0
        for pict in chapter.picts:
            for j in range(0, duration):
                slink = os.path.join(chapter.mpeg_dir,
                                     "pict-%s-%04d.jpg" % (chapter.esc_name,
                                                           i*duration+j))
                os.unlink(slink)
                pass
            i = i + 1
            pass
        pass

    def __check_video(self, chapter):
        print " creating video %s" % chapter.props.video_name
        yuv_cmd = "jpeg2yuv -v 0 -f 25 -I p -j '%s' "
        mpeg_cmd = "mpeg2enc -v 0 -a 2 -n p -f 4 -o '%s'"
        if os.access(chapter.props.video_name, os.F_OK):
            print " video %s already exists" % chapter.props.video_name
            return

        self.__check_picts(chapter)

        print "  combining frames"
        pict = os.path.join(chapter.mpeg_dir, "pict-%s-%%04d.jpg" % chapter.esc_name)
        os.system(yuv_cmd % pict + "|" +
                  mpeg_cmd % chapter.props.video_name)

        self.__rm_picts_links(chapter)
        pass

    def __check_mpg(self, chapter):
        mplex_cmd = "mplex -v 0 -f 4 -o '%s' '%s' '%s'"
        if os.access(chapter.props.mpg_name, os.F_OK):
            print "mpeg %s already exists" % chapter.props.mpg_name
            return

        self.__check_sound(chapter)
        self.__check_video(chapter)

        os.system(mplex_cmd % (chapter.props.mpg_name,
                               chapter.props.video_name,
                               chapter.props.sound_name))
        pass

    def __create_mpeg(self, chapter):
        print "creating mpeg for chapter " + chapter.props.name + "..."

        self.__check_mpg(chapter)

        print "done"
        pass


    def on_btn_build_cd_clicked(self, widget):
        print "build CD"
        xml = open("/tmp/videocd.xml", "w")

        #
        # header
        #
        xml.write('<?xml version="1.0"?>\n')
        xml.write('<!DOCTYPE videocd PUBLIC "-//GNU//DTD VideoCD//EN" "http://www.gnu.org/software/vcdimager/videocd.dtd">\n')
        xml.write('<videocd xmlns="http://www.gnu.org/software/vcdimager/1.0/" class="svcd" version="1.0">\n')
        xml.write('  <info>\n')
        xml.write('    <album-id>rodos</album-id>\n')
        xml.write('    <volume-count>1</volume-count>\n')
        xml.write('    <volume-number>1</volume-number>\n')
        xml.write('    <restriction>0</restriction>\n')
        xml.write('  </info>\n')
        xml.write('  <pvd>\n')
        xml.write('    <volume-id>VIDEOCD</volume-id>\n')
        xml.write('    <system-id>CD-RTOS CD-BRIDGE</system-id>\n')
        xml.write('    <application-id></application-id>\n')
        xml.write('    <preparer-id/>\n')
        xml.write('    <publisher-id/>\n')
        xml.write('  </pvd>\n')

        #
        # resources
        #

        xml.write('  <sequence-items>\n')
        i = 0
        for row in self.tv_vcd_chapters.get_model():
            xml.write('    <sequence-item src="%s" id="sequence-%02d"/>\n' % (row[1].props.mpg_name, i))
            i = i + 1
            pass
        max_chpts = i
        xml.write('  </sequence-items>\n')
        xml.write('  <pbc>\n')

        #
        # navigation
        #
        for i in range(0, max_chpts):
            xml.write('  <selection id="chpt-%02d">\n' % i)
            xml.write('    <bsn>1</bsn>\n')
            prev = i - 1
            if prev < 0:
                prev = max_chpts - 1
                pass
            next = i + 1
            if next >= max_chpts:
                next = 0
                pass
            xml.write('    <prev ref="chpt-%02d"/>\n' % prev)
            xml.write('    <next ref="chpt-%02d"/>\n' % next)
            xml.write('    <timeout ref="chpt-%02d"/>\n' % next)
            xml.write('    <wait>0</wait>\n')
            xml.write('    <loop jump-timing="immediate">1</loop>\n')
            xml.write('    <play-item ref="sequence-%02d"/>\n' % i)
            xml.write('  </selection>\n')
            pass

        xml.write('  </pbc>\n')
        xml.write('</videocd>\n')
        xml.close()
        os.system("vcdxbuild -p /tmp/videocd.xml -c /tmp/videocd.cue -b /tmp/videocd.bin")
        pass

    def on_btn_choose_music_clicked(self, widget):
        self.file_chooser_dialog.set_action(gtk.FILE_CHOOSER_ACTION_OPEN)
        self.file_chooser_dialog.set_title("Choose background music")
        response = self.file_chooser_dialog.run()
        self.file_chooser_dialog.hide()
        if response == gtk.RESPONSE_OK:
            model, iter = self.tv_vcd_chapters.get_selection().get_selected()
            if iter == None:
                return
            chapter = model.get_value(iter, self.VCD_CLMN_CHTR)
            chapter.props.mp3_name = self.file_chooser_dialog.get_filename()
            self.ent_music.set_text(chapter.props.mp3_name)
            pass
        pass

    def on_btn_chapters_play_clicked(self, widget):
        model, iter = self.tv_vcd_chapters.get_selection().get_selected()
        if iter == None:
            return
        chapter = model.get_value(iter, self.VCD_CLMN_CHTR)
        if os.access(chapter.props.mpg_name, os.F_OK):
            os.system("vlc '%s'" % chapter.props.mpg_name)
            pass
        pass

    def on_btn_sound_play_clicked(self, widget):
        model, iter = self.tv_vcd_chapters.get_selection().get_selected()
        if iter == None:
            return
        chapter = model.get_value(iter, self.VCD_CLMN_CHTR)
        if os.access(chapter.props.sound_name, os.F_OK):
            os.system("vlc '%s'" % chapter.props.sound_name)
        elif os.access(chapter.props.mp3_name, os.F_OK):
            os.system("vlc '%s'" % chapter.props.mp3_name)
            pass
        pass

    def on_btn_play_vcd_clicked(self, widget):
        if os.access("/tmp/videocd.cue", os.F_OK) and os.access("/tmp/videocd.bin", os.F_OK):
            os.system("vlc vcd:/tmp/videocd.cue")
            pass
        pass

    def on_tv_vcd_chapters_cursor_changed(self, widget):
        print "on_tv_vcd_chapters_cursor_changed"
        model, iter = self.tv_vcd_chapters.get_selection().get_selected()
        chapter = model.get_value(iter, self.VCD_CLMN_CHTR)
        self.ent_music.set_text(chapter.props.mp3_name)
        pass

    def on_tv_vcd_chapters_drag_data_received(self, widget, context, x, y, selection_data, info, timestamp):
        print "on_tv_vcd_chapters_drag_data_received"
        dest = self.tv_vcd_chapters.get_dest_row_at_pos(x, y)
        print "dest "+str(dest)
        context.finish(gtk.TRUE, gtk.FALSE, timestamp)
        chapter = self.gofoto.albumCollection.get_chapter(selection_data.data)
        if chapter != None:
            name = chapter.album.props.name + " / " + chapter.props.name
            self.tv_vcd_chapters.get_model().append(None, [name, chapter])
            pass
        return 0




if __name__ == "__main__":
    gofoto = Gofoto()
    pass
