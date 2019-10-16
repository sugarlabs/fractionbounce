# -*- coding: utf-8 -*-
# Copyright (c) 2011, Walter Bender
# Ported to gtk 3: Ignacio Rodríguez
# <ignaciorodriguez@sugarlabs.org>

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
try:
    from sugar3.graphics.objectchooser import FILTER_TYPE_GENERIC_MIME
except:
    FILTER_TYPE_GENERIC_MIME = 'generic_mime'


def chooser(parent_window, filter, action):
    """ Choose an object from the datastore and take some action """
    chooser = None
    try:
        chooser = ObjectChooser(parent=parent_window, what_filter=filter,
                                filter_type=FILTER_TYPE_GENERIC_MIME,
                                show_preview=True)
    except:
        chooser = ObjectChooser(parent=parent_window, what_filter=filter)
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
