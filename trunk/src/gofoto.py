#!/usr/bin/python

#
# GOFoto 0.1.0 - a photo manager application
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
import imp
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


#private modules
import const
import properties
import thumbcache

def appdir(path):
    return os.path.join(os.path.dirname(sys.argv[0]), path)


class Pict:
    def __init__(self, album, arg):
        self.album = album
        self.props = properties.Properties()

        if arg.__class__.__name__ == "str":
            self.pathfilename = arg
            self.props.vertical = False
            self.props.marked = False
            self.props.filename = os.path.basename(arg)
            self.props.name = self.props.filename
        elif arg.__class__.__name__ == "Element":
            pict_xml = arg
            self.props.load(pict_xml)
            self.pathfilename = os.path.join(album.dir, self.props.filename)
            pass
        self.small = None
        self.big = None
        pass

    def load(self):
        if not self.small:
            self.small = thumbcache.get_thumb(self.pathfilename, 50)
            pass
        pass

    def reload(self):
        self.small = thumbcache.get_thumb(self.pathfilename, 50)
        self.big = None
        pass

    def save(self, doc, xml):
        #pict_xml = doc.createElement("pict")
        #xml.appendChild(pict_xml)
        self.props.save(doc, xml, "pict")
        pass

class Chapter:
    def __init__(self, album, chpt_xml=None, dir=None):
        self.album = album
        self.props = properties.Properties()
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
    def __init__(self, dir, alb_xml=None):
        self.dir = os.path.abspath(dir)
        self.props = properties.Properties()
        self.picts = []

        if alb_xml:
            # read data from xml
            self.props.load(alb_xml)
            if not self.props.__dict__.has_key("hits"):
                self.props.hits = 0
                pass
            pass
        else:
            # read data from directory
            self.props.name = os.path.basename(self.dir)
            list = filter(lambda f: f.count(".jpg") > 0, os.listdir(dir))
            list.sort()
            for f in list:
                self.picts.append(Pict(self, os.path.join(dir, f)))
                pass
            pass
            self.props.marked = False
            self.props.hits = 0
        pass

    def save(self):
        doc = xml.dom.minidom.Document()

        alb_xml = doc.createElement("gofoto")
        doc.appendChild(alb_xml)

        # save props
        #props_xml = doc.createElement("props")
        #alb_xml.appendChild(props_xml)
        self.props.save(doc, alb_xml, "album")

        # save picts
        for pict in self.picts:
            pict.save(doc, alb_xml)
            pass

        f = open(os.path.join(self.dir, ".gofoto"), "w")
        xmlstring = doc.toprettyxml()
        f.write(xmlstring)
        f.close()
        #print xmlstring
        log.info("Album %s saved" % self.props.name)
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
        self.images_loader_break = threading.Event()
        self.images_loader_break.clear()
        self.thread = threading.Thread(target=self.__images_loader)
        self.thread.start()
        pass

    def close(self):
        self.images_loader_stop.set()
        self.images_loader_break.set()
        self.album_cond.acquire()
        self.album_cond.notify()
        self.album_cond.release()
        self.thread.join()
        pass

    def new_album(self, dir):
        album = self.get_album_by_dir(dir)
        if album:
            return album
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
        if album == None or album.__class__ != Album:
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

    def get_album_by_dir(self, dir):
        print "find album %s" % dir
        for a in self.albums:
            if a.dir == dir:
                return a
            pass
        return None

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
            
            log.debug("load images '%s' start %f" % (album.props.name, time.time()))
            for pict in album.picts:
                if self.images_loader_break.isSet():
                    log.info("Image loader break")
                    self.images_loader_break.clear()
                    self.albums_to_load.append(album)
                    break
                pict.load()
                pass
            log.debug("load images '%s' end %f" % (album.props.name, time.time()))
            pass
        log.info("Image loader closed")
        pass

    def __load_album_images(self, album):
        self.album_cond.acquire()
        alb_num = len(self.albums_to_load)
        if alb_num > 0:
            for i in range(0, len(self.albums_to_load)):
                if self.albums_to_load[i].props.hits < album.props.hits:
                    self.albums_to_load.insert(i, album)
                    break
                pass
            if not album in self.albums_to_load:
                self.albums_to_load.append(album)
                pass
            pass
        else:
            self.albums_to_load.append(album)
            pass
        #print [ a.props.name for a in self.albums_to_load ]
        self.album_cond.notify()
        self.album_cond.release()
        pass

    def speed_up_loading(self, album):
        self.album_cond.acquire()
        if album in self.albums_to_load and self.albums_to_load.index(album) > 0:
            self.albums_to_load.remove(album)
            self.albums_to_load.insert(0, album)
            log.debug("speed up loading of '%s'" % album.props.name)
            pass
        #print [ a.props.name for a in self.albums_to_load ]
        self.album_cond.notify()
        self.album_cond.release()
        self.images_loader_break.set()
        pass

    def append_album(self, dir, doc):
        if self.get_album_by_dir(dir):
            return
        
        # album
        alb_xml = doc.getElementsByTagName("gofoto")[0]
        props_xml = alb_xml.getElementsByTagName("album")[0]
        album = Album(dir, props_xml)
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
            if obj.__class__ in [Album, Chapter]:
                cell.set_property("active", obj.props.marked)
                cell.set_property("activatable", True)
            else:
                cell.set_property("active", False)
                cell.set_property("activatable", False)
                pass
            pass
        elif clmn_number == CLMN_NAME:
            if obj.__class__ == Album:
                if cell.__class__ == gtk.CellRendererText:
                    cell.set_property("text", obj.props.name)
                    cell.set_property('editable', True)
                elif cell.__class__ == gtk.CellRendererPixbuf:
                    cell.set_property("pixbuf", None)
                    cell.set_property("visible", False)
                    pass
            elif obj.__class__ == Pict:
                if cell.__class__ == gtk.CellRendererText:
                    cell.set_property("text", obj.props.name)
                    cell.set_property('editable', False)
                elif cell.__class__ == gtk.CellRendererPixbuf:
                    cell.set_property("height", 50)
                    cell.set_property("visible", True)
                    if obj.__dict__.has_key("small"):
                        cell.set_property("pixbuf", obj.small)
                    else:
                        cell.set_property("pixbuf", None)
                        pass
                    pass
                pass
            pass
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
                return True
            #if self.albumCollection.get_album_by_path(paths[0]) != None:
            #    self.ctxmnu_images.popup(None, None, None, event.button, event.time)
            #    pass
            return True
        return False

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
        context.finish(True, False, timestamp)
        paths = selection_data.data.split()
        print str(paths)
        self.albumCollection.move_picts(paths, path)
        return 0

    def on_tv_images_row_expanded(self, widget, iter, path):
        album = self.albumCollection.get_album_by_path(path)
        if not album:
            return 

        album.props.hits = album.props.hits + 1
        self.albumCollection.speed_up_loading(album)
        pass


    def get_current_album(self):
        return self.curr_album
        # old
        #model, paths = self.tv_images.get_selection().get_selected_rows()
        #alb_path = str(paths[0][0])
        #return self.albumCollection.get_album_by_path(alb_path)

    def select_pict_relative(self, offset):
        model, paths = self.tv_images.get_selection().get_selected_rows()
        if not paths:
            return
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

        plugins_paths = [os.path.join(const.GOFOTO_DIR, "plugins")]
        plugins = {}
        for d in plugins_paths:
            plugins[d] = os.listdir(d)
            pass
            
        for dir in plugins:
            for name in plugins[dir]:
                plugin_dir = os.path.join(dir, name)
                module = imp.find_module(name, [plugin_dir])
                mod = imp.load_module(name, *module)
                module[0].close
                self.plugins[mod.main_class.__name__] = mod
                self.__init_plugin(mod.main_class, plugin_dir)
                pass
            pass
        
        self.active_plugin = "PhotoRefining"
        pass

    def __init_plugin(self, klass, plugin_dir):
        plugin = klass(self.gofoto, plugin_dir)
        self.plugins[klass.__name__] = plugin
        plugin.page_idx = self.gofoto.notebook.insert_page(plugin.gui_root,
                                                           gtk.Label(plugin.plugin_name))
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

class PhotoCollector:
    CLMN_VISIBLE_MARK = 0
    CLMN_MARK = 1
    CLMN_NAME = 2
    def __init__(self, gofoto):
        self.xml = gofoto.xml
        self.gofoto = gofoto
        
        self.photo_collector_dialog = self.xml.get_widget("photo_collector_dialog")
        self.ent_top_dir = self.xml.get_widget("ent_top_dir")
        self.tv_photo_collector = self.xml.get_widget("tv_photo_collector")
        self.btn_collect = self.xml.get_widget("btn_collect")
        self.btn_add_collected = self.xml.get_widget("btn_add_collected")

        self.xml.signal_autoconnect({
            "on_btn_collect_toggled": self.on_btn_collect_toggled,
            "on_btn_add_collected_clicked": self.on_btn_add_collected_clicked})


        renderer = gtk.CellRendererToggle()
        renderer.connect("toggled", self.__toggled_dir)
        clmn = gtk.TreeViewColumn("", renderer, active=self.CLMN_MARK, visible=self.CLMN_VISIBLE_MARK)
        self.tv_photo_collector.append_column(clmn)

        renderer = gtk.CellRendererText()
        clmn = gtk.TreeViewColumn("Directory / photo", renderer, text=self.CLMN_NAME)
        self.tv_photo_collector.append_column(clmn)

        pass

    def __toggled_dir(self, cell, path):
        model = self.tv_photo_collector.get_model()
        iter = model.get_iter(path)
        model.set_value(iter, self.CLMN_MARK, not cell.get_active())
        pass

    def run(self):
        self.timer = -1
        response = self.photo_collector_dialog.run()
        self.photo_collector_dialog.hide()
        self.btn_collect.set_active(False)
        if self.timer != -1:
            gobject.source_remove(self.timer)
            pass
        pass

    def __collect_photos(self, top_dir, tree_store):
        for root, dirs, files in os.walk(top_dir):
            # skip traversing dirs with albums
            if ".gofoto" in files:
                # check if it is not missing from album list
                if not self.gofoto.albumCollection.get_album_by_dir(root):
                    self.gofoto.load_album(root)
                    pass
                # do not travers deeper
                dirs2 = dirs[:]
                for d in dirs2:
                    dirs.remove(d)
                    pass
                continue
            images = [ f for f in files if len(f) >= 4 and f[-4:] == ".jpg" ]
            if images:
                print root
                parent_iter = tree_store.append(None, [True, False, root])
                for i in images:
                    tree_store.append(parent_iter, [False, False, i])
                    pass
                pass
            yield True 
            pass
        self.btn_collect.set_active(False)
        yield False

    def on_btn_collect_toggled(self, widget):
        #deactivated search
        if not self.btn_collect.get_active():
            print "stop search"
            if self.timer != -1:
                gobject.source_remove(self.timer)
                pass
            return
            
        #activated search
        top_dir = self.ent_top_dir.get_text()
        print "search %s" % top_dir

        tree_store = gtk.TreeStore(gobject.TYPE_BOOLEAN, gobject.TYPE_BOOLEAN, gobject.TYPE_STRING)
        self.tv_photo_collector.set_model(tree_store)
        self.timer = gobject.timeout_add(50, self.__collect_photos(top_dir, tree_store).next)
        pass

    def on_btn_add_collected_clicked(self, widget):
        model = self.tv_photo_collector.get_model()
        
        for row in model:
            if not row[self.CLMN_MARK]:
                continue
            dir_name = row[self.CLMN_NAME]
            album = self.gofoto.albumCollection.new_album(dir_name)
            album.save()
            print dir_name
            pass

        model.clear()
        pass
    
    
class Gofoto:
    def __init__(self):
        #xml.signal_autoconnect(locals())

        gtk.threads_init()

        self.albumCollection = AlbumCollection()

        self.xml = gtk.glade.XML(appdir("gofoto.glade"))

        self.about_dialog = self.xml.get_widget("about_dialog")
        self.file_chooser_dialog = self.xml.get_widget("file_chooser_dialog")
        self.file_chooser_dialog.set_action(gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
        self.file_chooser_dialog.set_title("Choose directory with photos")
        #self.file_chooser_dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        #self.file_chooser_dialog.add_button(gtk.STOCK_OPEN, gtk.RESPONSE_OK)
        
        self.notebook = self.xml.get_widget("notebook")

        self.xml.signal_autoconnect({
            "on_gofoto_destroy": self.close_application,
            "on_save_activate": self.on_save_activate,
            "on_exit_activate": self.close_application,
            "on_new_album_activate": self.on_new_album_activate,
            "on_notebook_switch_page": self.on_notebook_switch_page,
            "on_collect_photos_activate": self.on_collect_photos_activate,
            "on_about_activate": self.on_about_activate})

        self.albumsBrowser = AlbumsBrowser(self)
        self.pluginManager = PluginManager(self)
        self.photoCollector = PhotoCollector(self)

        self.load_collection()

        #gtk.timeout_add(400, self.load_dir_files().next)
        gtk.main()
        pass

    def close_application(self, widget):
        self.save_collection()
        log.info("Closing gofoto")
        self.albumCollection.close()
        gtk.main_quit()
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
            f.write(album.dir+"\n")
            pass
        f.close()
        pass

    def load_album(self, dir_name):
        doc = xml.dom.minidom.parse(os.path.join(dir_name, ".gofoto"))
        self.albumCollection.append_album(dir_name, doc)
        pass

    def load_collection(self):
        rc = os.path.expanduser("~/.gofotorc")
        if not os.access(rc, os.F_OK):
            return
        f = open(rc, "r")
        dir_name = f.readline().strip()
        log.debug("load_collection start %f" % time.time())
        while dir_name:
            self.load_album(dir_name)
            dir_name = f.readline().strip()
            pass # end while dir
        log.debug("load_collection end %f" % time.time())
        f.close()
        pass

    def on_collect_photos_activate(self, widget):
        self.photoCollector.run()
        pass

    def on_about_activate(self, widget):
        self.about_dialog.run()
        self.about_dialog.hide()
        pass


if __name__ == "__main__":
    gofoto = Gofoto()
    pass
