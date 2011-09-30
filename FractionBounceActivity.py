# -*- coding: utf-8 -*-
#Copyright (c) 2011, Walter Bender, Paulina Clares, Chris Rowe

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import pygtk
pygtk.require('2.0')
import gtk
import gobject

import sugar
from sugar.activity import activity
from sugar.bundle.activitybundle import ActivityBundle
from sugar.activity.widgets import ActivityToolbarButton
from sugar.activity.widgets import StopButton
from sugar.graphics.toolbarbox import ToolbarBox
from sugar.graphics.toolbarbox import ToolbarButton
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.menuitem import MenuItem
from sugar.graphics.icon import Icon
from sugar.datastore import datastore

from gettext import gettext as _
import locale

import logging
_logger = logging.getLogger("fractionbounce-activity")

from bounce import Bounce


def _label_factory(toolbar, label):
    """ Factory for adding a label to a toolbar """
    my_label = gtk.Label(label)
    my_label.set_line_wrap(True)
    my_label.show()
    _toolitem = gtk.ToolItem()
    _toolitem.add(my_label)
    toolbar.insert(_toolitem, -1)
    _toolitem.show()
    return my_label


def _separator_factory(toolbar, expand=False, visible=True):
    """ add a separator to a toolbar """
    _separator = gtk.SeparatorToolItem()
    _separator.props.draw = visible
    _separator.set_expand(expand)
    toolbar.insert(_separator, -1)
    _separator.show()


def dec2frac(d):
    """ Convert float to its approximate fractional representation. """

    """
    This code was translated to Python from the answers at
    http://stackoverflow.com/questions/95727/how-to-convert-floats-to-human-readable-fractions/681534#681534
    
    For example:
    >>> 3./5
    0.59999999999999998

    >>> dec2frac(3./5)
    "3/5"

    """

    if d > 1:
        return "%s" % d
    df = 1.0
    top = 1
    bot = 1

    while abs(df - d) > 0.00000001:
        if df < d:
            top += 1
        else:
            bot += 1
            top = int(d * bot)
        df = float(top) / bot

    if bot == 1:
        return "%s" % top
    elif top == 0:
        return ""
    return "%s/%s" % (top, bot)


class FractionBounceActivity(activity.Activity):

    def __init__(self, handle):
        """ Initiate activity. """
        super(FractionBounceActivity, self).__init__(handle)

        # no sharing
        self.max_participants = 1

        toolbox = ToolbarBox()

        activity_button = ActivityToolbarButton(self)
        toolbox.toolbar.insert(activity_button, 0)
        activity_button.show()

        self.challenge = _label_factory(toolbox.toolbar, '')
        self.reset_label(0.5)

        _separator_factory(toolbox.toolbar, visible=False)

        self.counter = _label_factory(toolbox.toolbar, '')
        self.increment_label(0)

        _separator_factory(toolbox.toolbar, expand=True, visible=False)

        stop_button = StopButton(self)
        stop_button.props.accelerator = _('<Ctrl>Q')
        toolbox.toolbar.insert(stop_button, -1)

        stop_button.show()

        self.set_toolbox(toolbox)
        toolbox.show()

        # Create a canvas
        canvas = gtk.DrawingArea()
        canvas.set_size_request(gtk.gdk.screen_width(),
                                gtk.gdk.screen_height())
        self.set_canvas(canvas)
        canvas.show()
        self.show_all()

        # Initialize the canvas
        Bounce(canvas, self)

    def reset_label(self, fraction):
        """ update the challenge label """
        self.challenge.set_label(_("Bounce the ball to %s") \
                                     % (dec2frac(fraction)))

    def increment_label(self, n):
        """ update the number of tries label """
        self.counter.set_label(_("Number of tries: %d") % n)
