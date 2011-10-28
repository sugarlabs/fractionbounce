# -*- coding: utf-8 -*-
# Copyright (c) 2011, Walter Bender

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with this library; if not, write to the Free Software
# Foundation, 51 Franklin Street, Suite 500 Boston, MA 02110-1335 USA


import gtk

from sugar.graphics.objectchooser import ObjectChooser

from StringIO import StringIO
try:
    USING_JSON_READWRITE = False
    import json
    json.dumps
    from json import load as jload
    from json import dump as jdump
except (ImportError, AttributeError):
    try:
        import simplejson as json
        from simplejson import load as jload
        from simplejson import dump as jdump
    except (ImportError, AttributeError):
        USING_JSON_READWRITE = True


def json_load(text):
    """ Load JSON data using what ever resources are available. """
    if USING_JSON_READWRITE is True:
        listdata = json.read(text)
    else:
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
    if USING_JSON_READWRITE is True:
        return json.write(data)
    else:
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
            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT)
    if chooser is not None:
        try:
            result = chooser.run()
            if result == gtk.RESPONSE_ACCEPT:
                dsobject = chooser.get_selected_object()
                action(dsobject)
                dsobject.destroy()
        finally:
            chooser.destroy()
            del chooser
