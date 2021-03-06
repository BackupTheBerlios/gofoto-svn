#
# GOFoto 0.1.0 - a photo manager application, Video CD plugin
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
import properties

class VideoCD(plugins.Plugin):
    VCD_CLMN_PICT = 0
    VCD_CLMN_MARK = 1
    VCD_CLMN_NAME = 2
    def __init__(self, gofoto, dir):
        self.gofoto = gofoto
        self.dir = dir

        self.plugin_name = "VideoCD"

        self.xml = gtk.glade.XML(os.path.join(dir, "gui.glade"), "vbox")
        self.gui_root = self.xml.get_widget("vbox")

        self.ent_music = self.xml.get_widget("ent_music")
        self.tv_vcd_chapters = self.xml.get_widget("tv_vcd_chapters")

        self.xml.signal_autoconnect({
            "on_btn_create_mpegs_clicked": self.on_btn_create_mpegs_clicked,
            "on_btn_build_cd_clicked": self.on_btn_build_cd_clicked,
            "on_btn_choose_music_clicked": self.on_btn_choose_music_clicked,
            "on_btn_chapters_play_clicked": self.on_btn_chapters_play_clicked,
            "on_btn_sound_play_clicked": self.on_btn_sound_play_clicked,
            "on_btn_play_vcd_clicked": self.on_btn_play_vcd_clicked,
            "on_tv_vcd_chapters_cursor_changed": self.on_tv_vcd_chapters_cursor_changed,
            "on_tv_vcd_chapters_drag_data_get": self.on_tv_vcd_chapters_drag_data_get,
            "on_tv_vcd_chapters_drag_data_received": self.on_tv_vcd_chapters_drag_data_received,
            "on_tv_vcd_chapters_button_press_event": self.on_tv_vcd_chapters_button_press_event})

        self.menu_xml = gtk.glade.XML(os.path.join(dir, "gui.glade"), "ctx_menu")
        self.ctx_menu = self.menu_xml.get_widget("ctx_menu")
        self.menu_xml.signal_autoconnect({
            "on_add_chapter_activate": self.on_add_chapter_activate,
            "on_remove_chapter_activate": self.on_remove_chapter_activate,
            "on_rename_chapter_activate": self.on_rename_chapter_activate})

        self.xml2 = gtk.glade.XML(os.path.join(dir, "gui.glade"), "file_chooser_dialog")
        self.file_chooser_dialog = self.xml2.get_widget("file_chooser_dialog")

        renderer = gtk.CellRendererToggle() # Mark
        renderer.connect("toggled", self.on_tv_vcd_pict_toggled)
        clmn = gtk.TreeViewColumn("Mark", renderer, active=self.VCD_CLMN_MARK)
        self.tv_vcd_chapters.append_column(clmn)

        renderer = gtk.CellRendererText()   # Chapter
        renderer.connect('edited', self.cell_edited_callback)
        renderer.set_property('editable', True)
        clmn = gtk.TreeViewColumn("Chapter / Pict", renderer, text=self.VCD_CLMN_NAME)
        self.tv_vcd_chapters.append_column(clmn)
        self.tv_vcd_chapters.set_expander_column(clmn)

        self.tv_vcd_clmn_types = (gobject.TYPE_PYOBJECT,
                                  gobject.TYPE_BOOLEAN,
                                  gobject.TYPE_STRING)

        model = gtk.TreeStore(*self.tv_vcd_clmn_types)
        self.tv_vcd_chapters.set_model(model)

        self.tv_vcd_chapters.enable_model_drag_source(gtk.gdk.BUTTON1_MASK,
                                                      [('path', 0, 0)],
                                                      gtk.gdk.ACTION_DEFAULT |
                                                      gtk.gdk.ACTION_MOVE)
        self.tv_vcd_chapters.enable_model_drag_dest([('path', 0, 0)],
                                                    gtk.gdk.ACTION_DEFAULT |
                                                    gtk.gdk.ACTION_MOVE)

        self.album = None

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
        #model = self.tv_gal_picts.get_model()
        #for row in model:
        #    if pict == row[self.VCD_CLMN_PICT]:
        #        self.tv_gal_picts.set_cursor(row.path)
        #        break
        #    pass
        pass

    def __load_album(self, album):
        self.album = album
        
        model = gtk.TreeStore(*self.tv_vcd_clmn_types)

        # if there is no chapters, then add one chapter
        if not album.props.__dict__.has_key("vcd_chapters"):
            p = properties.Properties()
            p.name = "first"
            p.mp3_name = ""
            p.remake = True
            album.props.vcd_chapters = [p]
            for pict in album.picts:
                pict.props.vcd_chapter = "first"
                pass
            pass

        # load chapters to tv_vcd_chapters
        parent_chpts = {}
        for chpt in album.props.vcd_chapters:
            if not chpt.__dict__.has_key("mp3_name"):
                chpt.mp3_name = ""
                pass
            parent_chpts[chpt.name] = model.append(None, [None, True, chpt.name])
            pass            

        # load picts to chapters in tv_vcd_chapters
        for pict in album.picts:
            if pict.props.__dict__.has_key("vcd_included"):
                vcd_included = pict.props.vcd_included
            else:
                pict.props.vcd_included = True
                vcd_included = True
                pass
            model.append(parent_chpts[pict.props.vcd_chapter], [pict, vcd_included, pict.props.name])
            pass
        self.tv_vcd_chapters.set_model(model)
        pass

    def __find_chapter(self, name):
        for chpt in self.album.props.vcd_chapters:
            if chpt.name == name:
                return chpt
            pass
        return None
    

    def on_tv_vcd_pict_toggled(self, widget, path):
        model = self.tv_vcd_chapters.get_model()
        iter = model.get_iter(path)
        pict = model.get_value(iter, self.VCD_CLMN_PICT)
        if not pict:
            return
        pict.props.vcd_included = not pict.props.vcd_included
        model.set_value(iter, self.VCD_CLMN_MARK, pict.props.vcd_included)

        chpt = self.__find_chapter(model.get_value(model.iter_parent(iter), self.VCD_CLMN_NAME))
        chpt.remake = True
        
        print "Toggle pict %d" % pict.props.vcd_included
        pass

    def on_btn_create_mpegs_clicked(self, widget):
        print "create mpegs"

        mpeg_dir = os.path.join(self.album.dir, "mpeg")
        if not os.path.exists(mpeg_dir):
            os.mkdir(mpeg_dir)
            pass
        
        for row in self.tv_vcd_chapters.get_model():
            name = row[self.VCD_CLMN_NAME]
            chapter = self.__find_chapter(name)
            chapter.mpeg_dir = mpeg_dir
            chapter.esc_name = name.replace(" ", "_")
            chapter.mpg_name = os.path.join(mpeg_dir, ("mpg-"+chapter.esc_name+".mpg"))
            chapter.sound_name = os.path.join(mpeg_dir, ("snd-"+chapter.esc_name+".mp2"))
            chapter.video_name = os.path.join(mpeg_dir, ("vid-"+chapter.esc_name+".m2v"))

            self.__create_mpeg(chapter)
            pass
        print "mpegs are created"
        pass

    def __count_picts_in_chapter(self, chapter):
        num = 0
        for p in self.album.picts:
            if p.props.vcd_chapter == chapter.name and p.props.vcd_included:
                num = num + 1
                pass
            pass
        return num

    def __check_sound(self, chapter):
        chapter.wav_name_in = os.path.join(chapter.mpeg_dir,
                                           chapter.esc_name+"-in.wav")
        chapter.wav_name = os.path.join(chapter.mpeg_dir,
                                        chapter.esc_name+".wav")
        wav_cmd = "madplay '%s' --output=wave:'%s'"
        join_wav = "qwavjoin -o '%s' '%s'"
        cut_wav = "qwavcut -d -B %ds '%s'"
        mp2_cmd = "toolame -b 224 -s 44.1 -m s '%s' '%s'"
        mplex_cmd = "mplex -f 4 -o '%s' '%s'"

        print " creating sound %s" % chapter.sound_name

        if chapter.mp3_name == "":
            raise "chapter %s: MP3 file was not provided" % chapter.name
        if not os.access(chapter.mp3_name, os.F_OK):
            raise "chapter %s: MP3 file was not provided" % chapter.name
        
        if os.access(chapter.sound_name, os.F_OK):
            print " sound %s already exists" % chapter.sound_name
            return

        # convert mp3 to wave
        os.system(wav_cmd % (chapter.mp3_name, chapter.wav_name_in))

        # cut the wave
        w = wave.open(chapter.wav_name_in, "rb")
        wav_len = w.getnframes()/w.getframerate() # wave length in seconds
        video_len = self.__count_picts_in_chapter(chapter)*5  # chapter length in seconds
        if wav_len > video_len: # cut the wave
            chapter.wav_name = chapter.wav_name_in
            os.system(cut_wav % (video_len, chapter.wav_name))
            pass
        elif wav_len < video_len:   # extend the wave
            multi = video_len / wav_len
            files_in = ""
            for i in range(0, multi + 1):
                files_in = files_in + chapter.wav_name_in + " "
                pass
            os.system(join_wav % (chapter.wav_name, files_in))
            os.system(cut_wav % (video_len, chapter.wav_name))
            pass

        # convert wave to mp2
        os.system(mp2_cmd % (chapter.wav_name, chapter.sound_name))

        # delete temp files
        if os.access(chapter.wav_name, os.F_OK):
            os.unlink(chapter.wav_name)
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
        for pict in self.album.picts:
            if pict.props.vcd_chapter != chapter.name or not pict.props.vcd_included:
                continue
            
            tmp_pict = os.path.join(chapter.mpeg_dir,
                                    "pict-%s-%03d-%s" % (chapter.esc_name,
                                                         i,
                                                         pict.props.name))
            if not os.access(tmp_pict, os.F_OK):
                print "  convert pict %s" % tmp_pict
                if not pict.props.vertical:
                    os.system(convert_cmd1 % (os.path.join(self.album.dir, pict.props.name), tmp_pict))
                else:
                    os.system(convert_cmd2 % (os.path.join(self.album.dir, pict.props.name), tmp_pict))
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
        for pict in self.album.picts:
            if pict.props.vcd_chapter != chapter.name or not pict.props.vcd_included:
                continue

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
        print " creating video %s" % chapter.video_name
        yuv_cmd = "jpeg2yuv -v 0 -f 25 -I p -j '%s' "
        mpeg_cmd = "mpeg2enc -v 0 -a 2 -n p -f 4 -o '%s'"
        if not chapter.remake and os.access(chapter.video_name, os.F_OK):
            print " video %s already exists" % chapter.video_name
            return

        self.__check_picts(chapter)

        print "  combining frames"
        pict = os.path.join(chapter.mpeg_dir, "pict-%s-%%04d.jpg" % chapter.esc_name)
        os.system(yuv_cmd % pict + "|" +
                  mpeg_cmd % chapter.video_name)

        self.__rm_picts_links(chapter)
        pass

    def __check_mpg(self, chapter):
        mplex_cmd = "mplex -v 0 -f 4 -o '%s' '%s' '%s'"
        if not chapter.remake and os.access(chapter.mpg_name, os.F_OK):
            print "mpeg %s already exists" % chapter.mpg_name
            return

        self.__check_sound(chapter)
        self.__check_video(chapter)

        os.system(mplex_cmd % (chapter.mpg_name,
                               chapter.video_name,
                               chapter.sound_name))
        pass

    def __create_mpeg(self, chapter):
        print "creating mpeg for chapter " + chapter.name + "..."

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
        for chpt in self.album.props.vcd_chapters:
            xml.write('    <sequence-item src="%s" id="sequence-%02d"/>\n' % (chpt.mpg_name, i))
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
            if model.iter_depth(iter) == 1:
                iter = model.iter_parent(iter)
                pass
            name = model.get_value(iter, self.VCD_CLMN_NAME)
            chapter = self.__find_chapter(name)
            chapter.mp3_name = self.file_chooser_dialog.get_filename()
            self.ent_music.set_text(chapter.mp3_name)
            pass
        pass

    def on_btn_chapters_play_clicked(self, widget):
        model, iter = self.tv_vcd_chapters.get_selection().get_selected()
        if iter == None:
            return
        pict = model.get_value(iter, self.VCD_CLMN_PICT)
        if pict:
            chapter = self.__find_chapter(pict.props.vcd_chapter)
        else:
            chapter = self.__find_chapter(model.get_value(iter, self.VCD_CLMN_NAME))
            pass
        
        if os.access(chapter.mpg_name, os.F_OK):
            os.system("vlc '%s'" % chapter.mpg_name)
            pass
        pass

    def on_btn_sound_play_clicked(self, widget):
        model, iter = self.tv_vcd_chapters.get_selection().get_selected()
        if iter == None:
            return
        chapter = model.get_value(iter, self.VCD_CLMN_CHTR)
        if os.access(chapter.sound_name, os.F_OK):
            os.system("vlc '%s'" % chapter.sound_name)
        elif os.access(chapter.mp3_name, os.F_OK):
            os.system("vlc '%s'" % chapter.mp3_name)
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
        pict = model.get_value(iter, self.VCD_CLMN_PICT)
        if pict:
            mp3_name = self.__find_chapter(pict.props.vcd_chapter).mp3_name
        else:
            mp3_name = self.__find_chapter(model.get_value(iter, self.VCD_CLMN_NAME)).mp3_name
            pass
        self.ent_music.set_text(mp3_name)
        pass

    def on_tv_vcd_chapters_drag_data_get(self, treeview, context, selection, info, timestamp):
        print "on_tv_vcd_chapters_drag_data_get"
        treeselection = treeview.get_selection()
        model, paths = treeselection.get_selected_rows()
        str_paths = ""
        for p in paths:
            s = ""
            for i in p:
                s = s + str(i)+":"
                pass
            s = s[:-1]
            str_paths = str_paths + " " + s
            pass
        selection.set('text/plain', 8, str_paths)
        return

    def on_tv_vcd_chapters_drag_data_received(self, widget, context, x, y, selection_data, info, timestamp):
        print "on_tv_vcd_chapters_drag_data_received"
        dest = self.tv_vcd_chapters.get_dest_row_at_pos(x, y)
        if not dest:
            return
        print "dest "+str(dest)
        dest_path, dest_pos = dest
        context.finish(gtk.TRUE, gtk.FALSE, timestamp)
        print "received:" + str(selection_data.data)
        model = self.tv_vcd_chapters.get_model()
        src_row = model[selection_data.data]
        dest_row = model[dest_path]
        if dest_row[self.VCD_CLMN_PICT] != None or src_row[self.VCD_CLMN_PICT] == None:
            return 0
        pict = src_row[self.VCD_CLMN_PICT]
        model.append(dest_row.iter, [pict,
                                     src_row[self.VCD_CLMN_MARK],
                                     src_row[self.VCD_CLMN_NAME]])
        model.remove(src_row.iter)
        pict.props.vcd_chapter = dest_row[self.VCD_CLMN_NAME]
        return 0

    def on_tv_vcd_chapters_button_press_event(self, widget, event):
        if event.button == 3:
            self.ctx_menu.popup(None, None, None, event.button, event.time)
            return gtk.TRUE
        return gtk.FALSE

    def on_add_chapter_activate(self, widget):
        if not self.album:
            return

        name = "new"
        p = properties.Properties()
        p.name = name
        p.mp3_name = ""
        p.remake = True
        self.album.props.vcd_chapters.append(p)
        
        model = self.tv_vcd_chapters.get_model()
        iter = model.append(None, [None, True, name])
        path = model.get_path(iter)
        clmn = self.tv_vcd_chapters.get_column(self.VCD_CLMN_NAME)
        self.tv_vcd_chapters.set_cursor(path, clmn, True)

        pass
    
    def on_remove_chapter_activate(self, widget):
        model, iter = self.tv_vcd_chapters.get_selection().get_selected()
        if not iter:
            return

        print "got selected"

        name = model.get_value(iter, self.VCD_CLMN_NAME)

        chpt = self.__find_chapter(name)
        if not chpt:
            print "there is no chapter of name "+name
            return
        
        iter_child = model.iter_children(iter)
        if not iter_child:
            model.remove(iter)
            print "Removed chapter '%s' had no children" % name
            self.album.props.vcd_chapters.remove(chpt)
            return
        print "removing chapter %s" % name
        
        root = model.get_iter_root()
        print "root chapter %s" % model.get_value(root, self.VCD_CLMN_NAME)
        root_name = model.get_value(root, self.VCD_CLMN_NAME)
        iter_name = model.get_value(iter, self.VCD_CLMN_NAME)
        if root_name == iter_name:
            root = model.iter_next(root)
            print "root2 chapter %s" % model.get_value(root, self.VCD_CLMN_NAME)
            if not root:
                print "Removing last chapter is not allowed"
                return
            pass
        dest_name = model.get_value(root, self.VCD_CLMN_NAME)
        print "pict are moved to chapter %s" % dest_name

        # move all picts to destination chapter
        print "move all picts to dest chapter"
        iter_child = model.iter_children(iter)
        while iter_child:
            p, m, n = model.get(iter_child, self.VCD_CLMN_PICT, self.VCD_CLMN_MARK, self.VCD_CLMN_NAME)
            p.props.vcd_chapter = dest_name
            model.append(root, [p, m, n])
            model.remove(iter_child)
            iter_child = model.iter_children(iter)
            pass
        
        model.remove(iter)

        # remove from prop
        self.album.props.vcd_chapters.remove(chpt)

        pass
    
    def on_rename_chapter_activate(self, widget):
        print "c"
        pass

    def cell_edited_callback(self, cell, path, new_name):
        print "cell_edited_callback"
        model = self.tv_vcd_chapters.get_model()
        iter = model.get_iter(path)
        if model.get_value(iter, self.VCD_CLMN_PICT) != None:
            return # it is not chapter
        
        old_name = model.get_value(iter, self.VCD_CLMN_NAME)
        model.set_value(iter, self.VCD_CLMN_NAME, new_name)
        child = model.iter_children(iter)
        while child:
            pict = model.get_value(child, self.VCD_CLMN_PICT)
            pict.props.vcd_chapter = new_name
            child = model.iter_next(child)
            pass

        chpt = self.__find_chapter(old_name)
        chpt.name = new_name
        pass

main_class = VideoCD
