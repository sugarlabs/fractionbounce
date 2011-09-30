# -*- coding: utf-8 -*-
#Copyright (c) 2011, Walter Bender, Paulina Clares, Chris Rowe
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

BWIDTH = 40
BHEIGHT = 30
BOFFSET = 10
FSTROKE = 45
MAX_FADE_LEVEL = 3
CURSOR = '█'

FRACTIONS = [('1/2', 0.5), ('2/8', 0.25), ('1/3', 1/3.), ('2/3', 2/3.),
             ('2/5', 0.4)]

import pygtk
pygtk.require('2.0')
import gtk
from math import pow, floor, ceil
from random import uniform
import os
from time import sleep
import gobject

import locale
from gettext import gettext as _

import traceback
import logging
_logger = logging.getLogger("fractionbounce-activity")

try:
    from sugar.graphics import style
    GRID_CELL_SIZE = style.GRID_CELL_SIZE
except:
    GRID_CELL_SIZE = 0

from sprites import Sprites, Sprite

def dec2frac(d):
    """ Convert float  to its approximate fractional representation. """

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

#
# Utilities for generating artwork as SVG
#

def _svg_str_to_pixbuf(svg_string):
    """ Load pixbuf from SVG string """
    pl = gtk.gdk.PixbufLoader('svg')
    pl.write(svg_string)
    pl.close()
    pixbuf = pl.get_pixbuf()
    return pixbuf

def _svg_rect(w, h, rx, ry, x, y, fill, stroke):
    """ Returns an SVG rectangle """
    svg_string = "       <rect\n"
    svg_string += "          width=\"%f\"\n" % (w)
    svg_string += "          height=\"%f\"\n" % (h)
    svg_string += "          rx=\"%f\"\n" % (rx)
    svg_string += "          ry=\"%f\"\n" % (ry)
    svg_string += "          x=\"%f\"\n" % (x)
    svg_string += "          y=\"%f\"\n" % (y)
    svg_string += _svg_style("fill:%s;stroke:%s;" % (fill, stroke))
    return svg_string

def _svg_indicator():
    """ Returns a wedge-shaped indicator as SVG """
    svg_string = "%s %s" % ("<path d=\"m1.5 1.5 L 18.5 1.5 L 10 13.5 L 1.5",
                            "1.5 z\"\n")
    svg_string += _svg_style("fill:#ff0000;stroke:#ff0000;stroke-width:3.0;")
    return svg_string

def _svg_bead(fill, stroke, scale=1.0):
    """ Returns a bead-shaped SVG object; scale is used to elongate """
    _h = 15+30*(scale-1.0)
    _h2 = 30*scale-1.5
    svg_string = "<path d=\"m 1.5 15 A 15 13.5 90 0 1 15 1.5 L 25 1.5 A 15 13.5 90 0 1 38.5 15 L 38.5 %f A 15 13.5 90 0 1 25 %f L 15 %f A 15 13.5 90 0 1 1.5 %f L 1.5 15 z\"\n" %\
        (_h, _h2, _h2, _h)
    svg_string += _svg_style("fill:%s;stroke:%s;stroke-width:1.5" %\
                             (fill, stroke))
    return svg_string

def _svg_header(w, h, scale, hscale=1.0):
    """ Returns SVG header; some beads are elongated (hscale) """
    svg_string = "<?xml version=\"1.0\" encoding=\"UTF-8\""
    svg_string += " standalone=\"no\"?>\n"
    svg_string += "<!-- Created with Python -->\n"
    svg_string += "<svg\n"
    svg_string += "   xmlns:svg=\"http://www.w3.org/2000/svg\"\n"
    svg_string += "   xmlns=\"http://www.w3.org/2000/svg\"\n"
    svg_string += "   version=\"1.0\"\n"
    svg_string += "%s%f%s" % ("   width=\"", w*scale, "\"\n")
    svg_string += "%s%f%s" % ("   height=\"", h*scale*hscale, "\">\n")
    svg_string += "%s%f%s%f%s" % ("<g\n       transform=\"matrix(", 
                                  scale, ",0,0,", scale,
                                  ",0,0)\">\n")
    return svg_string

def _svg_footer():
    """ Returns SVG footer """
    svg_string = "</g>\n"
    svg_string += "</svg>\n"
    return svg_string

def _svg_style(extras=""):
    """ Returns SVG style for shape rendering """
    return "%s%s%s" % ("style=\"", extras, "\"/>\n")


class Bounce():
    """ The Bounce class is used to define the ball and the user
    interaction. """

    def __init__(self, canvas, parent=None):
        """ Initialize the canvas and set up the callbacks. """
        self.activity = parent

        if parent is None:        # Starting from command line
            self.sugar = False
            self.canvas = canvas
        else:                     # Starting from Sugar
            self.sugar = True
            self.canvas = canvas
            parent.show_all()

        self.canvas.set_flags(gtk.CAN_FOCUS)
        self.canvas.add_events(gtk.gdk.BUTTON_PRESS_MASK)
        self.canvas.add_events(gtk.gdk.BUTTON_RELEASE_MASK)
        self.canvas.add_events(gtk.gdk.POINTER_MOTION_MASK)
        self.canvas.connect("expose-event", self._expose_cb)
        self.canvas.connect("button-press-event", self._button_press_cb)
        self.canvas.connect("button-release-event", self._button_release_cb)
        self.canvas.connect("motion-notify-event", self._mouse_move_cb)
        self.canvas.connect("key_press_event", self._keypress_cb)
        self.width = gtk.gdk.screen_width()
        self.height = gtk.gdk.screen_height()-GRID_CELL_SIZE
        self.sprites = Sprites(self.canvas)
        self.scale = gtk.gdk.screen_height()/900.0
        self.dragpos = 0
        self.press = None
        self.last = None

        locale.setlocale(locale.LC_NUMERIC, '')
        self.decimal_point = locale.localeconv()['decimal_point']
        if self.decimal_point == '' or self.decimal_point is None:
            self.decimal_point = '.'

        self._choose_a_fraction()
        self.reached_the_top = False

        self.smiley_graphic = _svg_str_to_pixbuf(svg_from_file(
                os.path.join(# self.activity.get_bundle_path(),
                    "/home/walter/Activities/FractionBounce.activity",
                             "smiley.svg")))

        self.ball = Sprite(self.sprites, int(self.width/3), self.height-100, 
                           _svg_str_to_pixbuf(svg_from_file(
                os.path.join(# self.activity.get_bundle_path(),
                    "/home/walter/Activities/FractionBounce.activity",
                             "basketball.svg"))))
        self.dx = 0  # ball horizontal trajectory

        _mark = _svg_header(20, 15, self.scale) +\
                _svg_indicator() +\
                _svg_footer()
        self.mark = Sprite(self.sprites, int(self.width / 2),
                           self.height + 10,  # hide off bottom of screen
                           _svg_str_to_pixbuf(_mark))
        self.count = 0

        
    def _button_press_cb(self, win, event):
        """ Callback to handle the button presses """
        win.grab_focus()
        x, y = map(int, event.get_coords())
        self.press = self.sprites.find_sprite((x,y))
        self.last = self.press
        return True

    def _mouse_move_cb(self, win, event):
        """ Callback to handle the mouse moves """
        return True

    def _button_release_cb(self, win, event):
        """ Callback to handle the button releases """
        win.grab_focus()
        x, y = map(int, event.get_coords())
        if self.press is not None:
            if self.press == self.ball:
                self._move_ball()
        return True

    def _move_ball(self):
        self.mark.move((0, self.height + 10))
        if self.reached_the_top:
            self.ball.move_relative((self.dx, 5))
        else:
            self.ball.move_relative((self.dx, -5))
        if self.ball.get_xy()[1] < 1:  # get_xy() returns (x, y)
            # hit the top
            self.reached_the_top = True
            gobject.timeout_add(50, self._move_ball)
        elif self.ball.get_xy()[1] > self.height - self.ball.rect[3]:
            # hit the bottom
            self._test()
            self.reached_the_top = False
            self._choose_a_fraction()
            gobject.timeout_add(3000, self._move_ball)
        else:
            gobject.timeout_add(50, self._move_ball)

    def _choose_a_fraction(self):
        n = int(uniform(0, len(FRACTIONS)))
        _logger.debug(n)
        self.fraction = FRACTIONS[n][1]
        self.activity.reset_label(FRACTIONS[n][1])

    def _test(self):
        delta = self.ball.rect[2] / 4
        x = self.ball.get_xy()[0] + self.ball.rect[2] / 2
        f = self.fraction * self.width
        if x > f - delta and x < f + delta:
            smiley = Sprite(self.sprites, 0, 0, self.smiley_graphic)
            x = int(self.count * 25 % self.width)
            y = int(self.count / int(self.width / 25)) * 25
            smiley.move((x, y))
            smiley.set_layer(-1)
            _logger.debug("smiley face :)")

        self.count += 1
        self.activity.increment_label(self.count)
        self.mark.move((int(f), self.height - 10))

    def _keypress_cb(self, area, event):
        """ Keypress: moving the slides with the arrow keys """
        k = gtk.gdk.keyval_name(event.keyval)
        if k in ['h', 'Left']:
            self.dx = -5
        elif k in ['l', 'Right']:
            self.dx = 5
        else:
            self.dx = 0
        return True

    def _expose_cb(self, win, event):
        """ Callback to handle window expose events """
        self.sprites.redraw_sprites(event.area)
        return True

    def _destroy_cb(self, win, event):
        """ Callback to handle quit """
        gtk.main_quit()


def svg_from_file(pathname):
    """ Read SVG string from a file """
    f = file(pathname, 'r')
    svg = f.read()
    f.close()
    return(svg)
