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

import os.path
import md5
import gtk.gdk

print "thumbcache init"

CACHE_DIR = os.path.expanduser("~/.thumbnail")
CACHE_DIR_NORMAL = os.path.join(CACHE_DIR, "normal")
CACHE_DIR_LARGE = os.path.join(CACHE_DIR, "large")
CACHE_DIR_FAIL = os.path.join(CACHE_DIR, "fail")

if not os.access(CACHE_DIR, os.F_OK):
    os.mkdir(CACHE_DIR)
    pass
if not os.access(CACHE_DIR_NORMAL, os.F_OK):
    os.mkdir(CACHE_DIR_NORMAL)
    pass
if not os.access(CACHE_DIR_LARGE, os.F_OK):
    os.mkdir(CACHE_DIR_LARGE)
    pass
if not os.access(CACHE_DIR_FAIL, os.F_OK):
    os.mkdir(CACHE_DIR_FAIL)
    pass
pass



def get_thumb(filepath, width):
    thumbpath = os.path.join(CACHE_DIR_NORMAL, md5.md5("file://"+filepath).hexdigest() + ".png")
    if os.access(thumbpath, os.F_OK):
        return gtk.gdk.pixbuf_new_from_file_at_size(thumbpath, width, width)
    else:
        print "create thumb for %s" % filepath
        thumb = __create_thumb(filepath, thumbpath)
        height = thumb.get_height() * width / thumb.get_width()
        return thumb.scale_simple(width, height, gtk.gdk.INTERP_NEAREST)
    pass

def __create_thumb(filepath, thumbpath):
    thumb = gtk.gdk.pixbuf_new_from_file_at_size(filepath, 128, 128)
    thumb.save(thumbpath, "png",
               {"tEXt::Thumb::URI" : "file://"+filepath,
                "tEXt::Thumb::MTime" : str(os.stat(filepath)[8]),
                "tEXt::Thumb::Size" : str(os.stat(filepath)[6]),
                "tEXt::Software" : "GOFoto"})
    return thumb
