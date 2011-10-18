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

from sprites import Sprite
from svg_utils import svg_header, svg_footer, svg_rect, svg_str_to_pixbuf

from gettext import gettext as _


BAR_HEIGHT = 25


class Bar():
    ''' The Bar class is used to define the bars at the bottom of the
    screen '''

    def __init__(self, sprites, width, height, scale, size):
        ''' Initialize the 2-segment bar, labels, and mark '''
        self.sprites = sprites
        self.bars = {}
        self.screen_width = width
        self.screen_height = height
        self.scale = scale
        self.ball_size = size

        self.make_bar(2)
        self.make_mark()
        self.make_labels()

    def make_mark(self):
        ''' Make a mark to show the fraction position on the bar. '''
        mark = svg_header(self.ball_size / 2.,
                          BAR_HEIGHT * self.scale + 4, 1.0) + \
               svg_rect(self.ball_size / 2.,
                        BAR_HEIGHT * self.scale + 4, 0, 0, 0, 0,
                        '#FF0000', '#FF0000') + \
               svg_rect(1, BAR_HEIGHT * self.scale + 4, 0, 0,
                        self.ball_size / 4., 0, '#000000', '#000000') + \
               svg_footer()
        self.mark = Sprite(self.sprites, 0,
                           self.screen_height,  # hide off bottom of screen
                           svg_str_to_pixbuf(mark))
        self.mark.set_layer(2)

    def mark_width(self):
        return self.mark.rect[2]

    def bar_x(self):
        return self.bars[2].get_xy()[0]

    def bar_y(self):
        return self.bars[2].get_xy()[1]

    def width(self):
        return self.bars[2].rect[2]

    def height(self):
        return self.bars[2].rect[3]

    def hide_bars(self):
        ''' Hide all of the bars '''
        for bar in self.bars:
            self.bars[bar].set_layer(-1)

    def make_labels(self):
        ''' Label the bar '''
        num = svg_header(BAR_HEIGHT * self.scale, BAR_HEIGHT * self.scale,
                         1.0) + \
              svg_rect(BAR_HEIGHT * self.scale, BAR_HEIGHT * self.scale,
                       0, 0, 0, 0, 'none', 'none') + \
              svg_footer()
        self.left = Sprite(self.sprites, int(self.ball_size / 4),
                           self.bar_y(), svg_str_to_pixbuf(num))
        self.left.set_label(_('0'))
        self.right = Sprite(self.sprites,
                            self.screen_width - int(self.ball_size / 2),
                            self.bar_y(), svg_str_to_pixbuf(num))
        self.right.set_label(_('1'))

    def get_bar(self, nsegments):
        ''' Return a bar with n segments '''
        if nsegments not in self.bars:
            self.make_bar(nsegments)
        return self.bars[nsegments]

    def make_bar(self, nsegments):
        ''' Create a bar with n segments '''
        svg = svg_header(self.screen_width - self.ball_size, BAR_HEIGHT, 1.0)
        dx = (self.screen_width - self.ball_size) / float(nsegments)
        for i in range(int(nsegments) / 2):
            svg += svg_rect(dx, BAR_HEIGHT * self.scale, 0, 0,
                            i * 2 * dx, 0, '#FFFFFF', '#FFFFFF')
            svg += svg_rect(dx, BAR_HEIGHT * self.scale, 0, 0,
                            (i * 2 + 1) * dx, 0, '#AAAAAA', '#AAAAAA')
        if int(nsegments) % 2 == 1:  # odd
            svg += svg_rect(dx, BAR_HEIGHT * self.scale, 0, 0,
                            (i * 2 + 2) * dx, 0, '#FFFFFF', '#FFFFFF')
        svg += svg_footer()

        self.bars[nsegments] = Sprite(self.sprites, 0, 0,
                                      svg_str_to_pixbuf(svg))
        self.bars[nsegments].move(
            (int(self.ball_size / 2), self.screen_height - \
                 int((self.ball_size + self.height()) / 2)))
