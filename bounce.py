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

FRACTIONS = [('1/2', 0.5), ('2/8', 0.25), ('1/3', 1 / 3.), ('2/3', 2 / 3.),
             ('2/5', 0.4), ('1/4', 0.25), ('3/4', 0.75), ('4/5', 0.8)]
BAR_HEIGHT = 20

import gtk
from random import uniform
import os
import gobject

from gettext import gettext as _

import logging
_logger = logging.getLogger("fractionbounce-activity")

try:
    from sugar.graphics import style
    GRID_CELL_SIZE = style.GRID_CELL_SIZE
except ImportError:
    GRID_CELL_SIZE = 0

from sprites import Sprites, Sprite


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


def _svg_header(w, h, scale, hscale=1.0):
    """ Returns SVG header; some beads are elongated (hscale) """
    svg_string = "<?xml version=\"1.0\" encoding=\"UTF-8\""
    svg_string += " standalone=\"no\"?>\n"
    svg_string += "<!-- Created with Python -->\n"
    svg_string += "<svg\n"
    svg_string += "   xmlns:svg=\"http://www.w3.org/2000/svg\"\n"
    svg_string += "   xmlns=\"http://www.w3.org/2000/svg\"\n"
    svg_string += "   version=\"1.0\"\n"
    svg_string += "%s%f%s" % ("   width=\"", w * scale, "\"\n")
    svg_string += "%s%f%s" % ("   height=\"", h * scale * hscale, "\">\n")
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

    def __init__(self, canvas, path, parent=None):
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
        self.height = gtk.gdk.screen_height() - GRID_CELL_SIZE
        self.sprites = Sprites(self.canvas)
        self.scale = gtk.gdk.screen_height() / 900.0
        self.press = None

        self._choose_a_fraction()
        self.reached_the_top = False

        # Create the sprites we'll need
        self.smiley_graphic = _svg_str_to_pixbuf(svg_from_file(
                os.path.join(path, "smiley.svg")))

        self.ball = Sprite(self.sprites, 0, 0,
                           _svg_str_to_pixbuf(svg_from_file(
                    os.path.join(path, "basketball.svg"))))
        self.ball.set_layer(1)
        self.ball.set_label(_('click'))

        mark = _svg_header(20, 15, self.scale) + \
               _svg_indicator() + \
               _svg_footer()
        self.mark = Sprite(self.sprites, 0,
                           self.height,  # hide off bottom of screen
                           _svg_str_to_pixbuf(mark))
        self.mark.set_layer(2)

        bar = _svg_header(self.width - self.ball.rect[2], BAR_HEIGHT, 1.0)
        dx = int((self.width - self.ball.rect[2]) / 12)
        for i in range(6):  # divide into twelve segments
            bar += _svg_rect(dx, BAR_HEIGHT * self.scale, 0, 0, i * 2 * dx, 0,
                             '#FFFFFF', '#FFFFFF')
            bar += _svg_rect(dx, BAR_HEIGHT * self.scale, 0, 0,
                             (i * 2 + 1) * dx, 0, '#AAAAAA', '#AAAAAA')
        bar += _svg_footer()
        self.bar =  Sprite(self.sprites, 0, 0, _svg_str_to_pixbuf(bar))
        hoffset = int((self.ball.rect[3] + self.bar.rect[3]) / 2)
        self.bar.move((int(self.ball.rect[2] / 2), self.height - hoffset))
        self.bar.set_layer(0)
        num = _svg_header(BAR_HEIGHT * self.scale, BAR_HEIGHT * self.scale,
                           1.0) + \
              _svg_rect(BAR_HEIGHT * self.scale,
                        BAR_HEIGHT * self.scale, 0, 0, 0, 0,
                        'none', 'none') + \
              _svg_footer()
        self.left = Sprite(self.sprites, int(self.ball.rect[2] / 4),
                           self.height - hoffset, _svg_str_to_pixbuf(num))
        self.left.set_label('0')
        self.right = Sprite(self.sprites,
                            self.width -  int(self.ball.rect[2] / 2),
                            self.height - hoffset, _svg_str_to_pixbuf(num))
        self.right.set_label('1')

        self.ball.move((int((self.width - self.ball.rect[2]) / 2),
                        self.bar.rect[1] - self.ball.rect[3]))

        self.dx = 0  # ball horizontal trajectory
        self.count = 0

    def _button_press_cb(self, win, event):
        """ Callback to handle the button presses """
        win.grab_focus()
        x, y = map(int, event.get_coords())
        self.press = self.sprites.find_sprite((x, y))
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
                self.ball.set_label('')
                self._move_ball()
        return True

    def _move_ball(self):
        """ Move the ball and test boundary conditions """
        self.mark.move((0, self.height))  # hide the mark
        if self.reached_the_top:
            if self.ball.get_xy()[0] + self.dx > 0 and \
               self.ball.get_xy()[0] + self.dx < self.width - self.ball.rect[2]:
                self.ball.move_relative((self.dx, 5))
            else:
                self.ball.move_relative((0, 5))
        else:
            if self.ball.get_xy()[0] + self.dx > 0 and \
               self.ball.get_xy()[0] + self.dx < self.width - self.ball.rect[2]:
                self.ball.move_relative((self.dx, -5))
            else:
                self.ball.move_relative((0, 5))
        if self.ball.get_xy()[1] < 1:
            # hit the top
            self.reached_the_top = True
            gobject.timeout_add(50, self._move_ball)
        elif self.ball.get_xy()[1] > self.bar.rect[1] - self.ball.rect[3]:
            # hit the bottom
            self._test()
            self.reached_the_top = False
            self._choose_a_fraction()
            gobject.timeout_add(3000, self._move_ball)
        else:
            gobject.timeout_add(50, self._move_ball)

    def _choose_a_fraction(self):
        """ Select a new fraction challenge from the table """
        n = int(uniform(0, len(FRACTIONS)))
        _logger.debug(n)
        self.fraction = FRACTIONS[n][1]
        self.activity.reset_label(FRACTIONS[n][1])

    def _test(self):
        """ Test to see if we estimated correctly """
        delta = self.ball.rect[2] / 4
        x = self.ball.get_xy()[0] + self.ball.rect[2] / 2
        f = self.ball.rect[2] / 2 + self.fraction * self.bar.rect[2]
        if x > f - delta and x < f + delta:
            smiley = Sprite(self.sprites, 0, 0, self.smiley_graphic)
            x = int(self.count * 25 % self.width)
            y = int(self.count / int(self.width / 25)) * 25
            smiley.move((x, y))
            smiley.set_layer(-1)

        self.count += 1
        self.mark.move((int(f), self.bar.rect[1] - self.mark.rect[3]))

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
