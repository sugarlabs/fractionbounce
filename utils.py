# -*- coding: utf-8 -*-
# Copyright (c) 2011, Walter Bender
# Copyright (c) 2012, Ignacio Rodriguez

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with this library; if not, write to the Free Software
# Foundation, 51 Franklin Street, Suite 500 Boston, MA 02110-1335 USA


from gi.repository import Gtk

from sugar3.graphics.objectchooser import ObjectChooser
from sugar3 import profile
from sugar3.graphics.style import Color

from StringIO import StringIO
import json
json.dumps
from json import load as jload
from json import dump as jdump
full = False


def rgb2html(color):
    """Returns a html string from a Gdk color"""
    red = "%x" % int(color.red / 65535.0 * 255)
    if len(red) == 1:
            red = "0%s" % red

    green = "%x" % int(color.green / 65535.0 * 255)

    if len(green) == 1:
            green = "0%s" % green

    blue = "%x" % int(color.blue / 65535.0 * 255)

    if len(blue) == 1:
            blue = "0%s" % blue

    new_color = "#%s%s%s" % (red, green, blue)

    return new_color
def get_user_fill_color(type='str'):
    """Returns the user fill color"""
    color = profile.get_color()

    if type == 'gdk':
        rcolor = Color(color.get_fill_color()).get_gdk_color()

    elif type == 'str':
        rcolor = color.get_fill_color()

    return rcolor


def get_user_stroke_color(type='str'):
    """Returns the user stroke color"""
    color = profile.get_color()

    if type == 'gdk':
        rcolor = Color(color.get_stroke_color()).get_gdk_color()

    elif type == 'str':
        rcolor = color.get_stroke_color()

    return rcolor

def json_load(text):
    """ Load JSON data using what ever resources are available. """
    # strip out leading and trailing whitespace, nulls, and newlines
    io = StringIO(text)
    try:
        listdata = jload(io)
    except ValueError:
        # assume that text is ascii list
        listdata = text.split()
        for i, value in enumerate(listdata):
            listdata[i] = int(value)
    return listdata


def json_dump(data):
    """ Save data using available JSON tools. """
    _io = StringIO()
    jdump(data, _io)
    return _io.getvalue()


def chooser(parent_window, filter, action):
    """ Choose an object from the datastore and take some action """
    chooser = None
    try:
        chooser = ObjectChooser(parent=parent_window, what_filter=filter)
    except TypeError:
        chooser = ObjectChooser(None, parent_window,
            Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT)
    if chooser is not None:
        try:
            result = chooser.run()
            if result == Gtk.ResponseType.ACCEPT:
                dsobject = chooser.get_selected_object()
                action(dsobject)
                dsobject.destroy()
        finally:
            chooser.destroy()
            del chooser
