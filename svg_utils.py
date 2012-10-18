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
from gi.repository import GdkPixbuf

from math import sin, cos, pi


def generate_xo_svg(scale=1.0, colors=["#C0C0C0", "#282828"]):
    ''' Returns an SVG string representing an XO image '''
    return svg_header(55, 55, scale) + \
           _svg_xo(colors[0], colors[1]) + \
           svg_footer()


def svg_str_to_pixbuf(svg_string):
    ''' Load pixbuf from SVG string '''
    pl = GdkPixbuf.PixbufLoader.new_with_type('svg') 
    pl.write(svg_string)
    pl.close()
    pixbuf = pl.get_pixbuf()
    return pixbuf


def svg_sector(x, y, r, a, fill, stroke):
    ''' Returns an SVG sector '''
    if a < pi:
        big_arc = 0
    else:
        big_arc = 1
    svg_string = '       <path d="M%f,%f v%f a%f,%f 0 %d,0 %f,%f z"\n' % (
        x, y, -r, r, r, big_arc, -sin(a) * r, r - cos(a) * r)
    svg_string += _svg_style('fill:%s;stroke:%s;' % (fill, stroke))
    print svg_string
    return svg_string


def svg_rect(w, h, rx, ry, x, y, fill, stroke):
    ''' Returns an SVG rectangle '''
    svg_string = '       <rect\n'
    svg_string += '          width="%f"\n' % (w)
    svg_string += '          height="%f"\n' % (h)
    svg_string += '          rx="%f"\n' % (rx)
    svg_string += '          ry="%f"\n' % (ry)
    svg_string += '          x="%f"\n' % (x)
    svg_string += '          y="%f"\n' % (y)
    svg_string += _svg_style('fill:%s;stroke:%s;' % (fill, stroke))
    return svg_string


def _svg_xo(fill, stroke, width=3.5):
    ''' Returns XO icon graphic '''
    svg_string = '<path d="M33.233,35.1l10.102,10.1c0.752,\
0.75,1.217,1.783,1.217,2.932\
   c0,2.287-1.855,4.143-4.146,4.143c-1.145,0-2.178-0.463-2.932-1.211L27.372,\
40.961l-10.1,10.1c-0.75,0.75-1.787,1.211-2.934,1.211\
   c-2.284,0-4.143-1.854-4.143-4.141c0-1.146,0.465-2.184,\
1.212-2.934l10.104-10.102L11.409,24.995\
   c-0.747-0.748-1.212-1.785-1.212-2.93c0-2.289,1.854-4.146,4.146-4.146c1.143,\
0,2.18,0.465,2.93,1.214l10.099,10.102l10.102-10.103\
   c0.754-0.749,1.787-1.214,2.934-1.214c2.289,0,4.146,1.856,4.146,4.145c0,\
1.146-0.467,2.18-1.217,2.932L33.233,35.1z" '
    svg_string += _svg_style('fill:%s;stroke:%s;stroke_width:%f' % (fill,
                                                                    stroke,
                                                                    width))
    svg_string += '\n<circle cx="27.371" cy="10.849" r="8.122" '
    svg_string += _svg_style('fill:%s;stroke:%s;stroke_width:%f' % (fill,
                                                                    stroke,
                                                                    width))
    return svg_string


def svg_header(w, h, scale, hscale=1.0):
    ''' Returns SVG header; some beads are elongated (hscale) '''
    svg_string = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
    svg_string += '<!-- Created with Python -->\n'
    svg_string += '<svg\n'
    svg_string += '   xmlns:svg="http://www.w3.org/2000/svg"\n'
    svg_string += '   xmlns="http://www.w3.org/2000/svg"\n'
    svg_string += '   version="1.0"\n'
    svg_string += '   width="%f"\n' % (w * scale)
    svg_string += '   height="%f">\n' % (h * scale * hscale)
    svg_string += '<g\n       transform="matrix(%f,0,0,%f,0,0)">\n' % (
                                  scale, scale)
    return svg_string


def svg_footer():
    ''' Returns SVG footer '''
    svg_string = '</g>\n'
    svg_string += '</svg>\n'
    return svg_string


def _svg_style(extras=''):
    ''' Returns SVG style for shape rendering '''
    return 'style="%s"/>\n' % (extras)


def svg_from_file(pathname):
    ''' Read SVG string from a file '''
    f = file(pathname, 'r')
    svg = f.read()
    f.close()
    return(svg)


def extract_svg_payload(fd):
    """Returns everything between <svg ...> and </svg>"""
    payload = ''
    looking_for_start_svg_token = True
    looking_for_close_token = True
    looking_for_end_svg_token = True
    for line in fd:
        if looking_for_start_svg_token:
            if line.find('<svg') < 0:
                continue
            looking_for_start_svg_token = False
            line = line.split('<svg', 1)[1]
        if looking_for_close_token:
            if line.find('>') < 0:
                continue
            looking_for_close_token = False
            line = line.split('>', 1)[1]
        if looking_for_end_svg_token:
            if line.find('</svg>') < 0:
                payload += line
                continue
            payload += line.split('</svg>')[0]
            break
    return payload
