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


class VideoCD(plugins.Plugin):
    VCD_CLMN_NAME = 0
    VCD_CLMN_CHTR = 1
    def __init__(self, gofoto, dir):
        self.gofoto = gofoto
        self.dir = dir

        self.plugin_name = "VideoCD"

        self.xml = gtk.glade.XML(os.path.join(dir, "gui.glade"), "vbox")
        self.gui_root = self.xml.get_widget("vbox")

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
            mpeg_dir = os.path.join(chapter.album.dir, "mpeg")
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

main_class = VideoCD
