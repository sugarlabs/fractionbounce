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
import base64
from math import sin, cos, pi


def generate_ball_svg(path):
    ''' Returns an SVG string of a ball + label with image from path '''
    with open(path, 'rb') as w:
        x = w.read()
    base64_embed = base64.b64encode(x).decode()
    type_embed = path.split('.')[-1]
    a =  """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
xmlns:dc="http://purl.org/dc/elements/1.1/"
xmlns:cc="http://creativecommons.org/ns#"
xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
xmlns:svg="http://www.w3.org/2000/svg"
xmlns="http://www.w3.org/2000/svg"
xmlns:xlink="http://www.w3.org/1999/xlink"
version="1.1"
width="85"
height="120">
<image
xlink:href="data:image/{};base64,{}
"
x="0"
y="35"
width="85"
height="85" />
<rect
width="85"
height="35"
ry="7.75"
x="0"
y="0"
style="fill:#ffffff;fill-opacity:1;stroke:none" />
</svg>
""".format(type_embed, base64_embed)
    return a


def generate_xo_svg(scale=1.0, colors=["#C0C0C0", "#282828"]):
    ''' Returns an SVG string representing an XO image '''
    return svg_header(55, 55, scale) + \
        _svg_xo(colors[0], colors[1]) + \
        svg_footer()


def svg_str_to_pixbuf(v):
    ''' Load pixbuf from SVG string '''
    pl = GdkPixbuf.PixbufLoader.new_with_type('svg')
    pl.write(v.encode())
    pl.close()
    pixbuf = pl.get_pixbuf()
    return pixbuf


def svg_sector(x, y, r, a, fill, stroke):
    ''' Returns an SVG sector '''
    if a < pi:
        big_arc = 0
    else:
        big_arc = 1
    v = '       <path d="M%f,%f v%f a%f,%f 0 %d,0 %f,%f z"\n' % (
        x, y, -r, r, r, big_arc, -sin(a) * r, r - cos(a) * r)
    v += _svg_style('fill:%s;stroke:%s;' % (fill, stroke))
    return v


def svg_wedge(w, h, dx, dyl, dyr, fill, stroke, stroke_width=3.5):
    ''' Returns an SVG wedge: assumes  '''
    s2 = stroke_width / 2.0
    v = '<path\n'
    v += 'd="m %f,%f ' % (dx + s2, h - s2)
    v += '%f,%f ' % (w - s2, 0)
    v += '%f,-%f ' % (0, dyr - s2)
    v += '-%f,%f z"\n' % (w - s2, (dyr - dyl))
    v += _svg_style(
        'fill:%s;stroke:%s;stroke_width:%f' % (fill, stroke, stroke_width))
    return v


def svg_rect(w, h, rx, ry, x, y, fill, stroke):
    ''' Returns an SVG rectangle '''
    v = '       <rect\n'
    v += '          width="%f"\n' % (w)
    v += '          height="%f"\n' % (h)
    v += '          rx="%f"\n' % (rx)
    v += '          ry="%f"\n' % (ry)
    v += '          x="%f"\n' % (x)
    v += '          y="%f"\n' % (y)
    v += _svg_style('fill:%s;stroke:%s;' % (fill, stroke))
    return v


def genblank(w, h, colors, stroke_width=1.0):
    return svg_header(w, h, 1.0) + \
        svg_rect(w, h, 0, 0, 0, 0, colors[0], colors[1]) + \
        svg_footer()


def _svg_xo(fill, stroke, width=3.5):
    ''' Returns XO icon graphic '''
    v = '<path d="M33.233,35.1l10.102,10.1c0.752,\
0.75,1.217,1.783,1.217,2.932\
   c0,2.287-1.855,4.143-4.146,4.143c-1.145,0-2.178-0.463-2.932-1.211L27.372,\
40.961l-10.1,10.1c-0.75,0.75-1.787,1.211-2.934,1.211\
   c-2.284,0-4.143-1.854-4.143-4.141c0-1.146,0.465-2.184,\
1.212-2.934l10.104-10.102L11.409,24.995\
   c-0.747-0.748-1.212-1.785-1.212-2.93c0-2.289,1.854-4.146,4.146-4.146c1.143,\
0,2.18,0.465,2.93,1.214l10.099,10.102l10.102-10.103\
   c0.754-0.749,1.787-1.214,2.934-1.214c2.289,0,4.146,1.856,4.146,4.145c0,\
1.146-0.467,2.18-1.217,2.932L33.233,35.1z" '
    v += _svg_style(
        'fill:%s;stroke:%s;stroke_width:%f' % (fill, stroke, width))
    v += '\n<circle cx="27.371" cy="10.849" r="8.122" '
    v += _svg_style(
        'fill:%s;stroke:%s;stroke_width:%f' % (fill, stroke, width))
    return v


def svg_header(w, h, scale):
    ''' Returns SVG header; some beads are elongated (hscale) '''
    v = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
    v += '<!-- Created with Python -->\n'
    v += '<svg\n'
    v += '   xmlns:svg="http://www.w3.org/2000/svg"\n'
    v += '   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n'
    v += '   xmlns:cc="http://creativecommons.org/ns#"\n'
    v += '   xmlns:dc="http://purl.org/dc/elements/1.1/"\n'
    v += '   xmlns="http://www.w3.org/2000/svg"\n'
    v += '   version="1.0"\n'
    v += '   width="%f"\n' % (w * scale)
    v += '   height="%f">\n' % (h * scale)
    v += '<g\n       transform="matrix(%f,0,0,%f,0,0)">\n' % (scale, scale)
    return v


def svg_footer():
    ''' Returns SVG footer '''
    v = '</g>\n'
    v += '</svg>\n'
    return v


def _svg_style(extras=''):
    ''' Returns SVG style for shape rendering '''
    return 'style="%s"/>\n' % (extras)


def svg_from_file(pathname):
    ''' Read SVG string from a file '''
    f = open(pathname, 'r')
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
