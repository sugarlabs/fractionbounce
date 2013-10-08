# -*- coding: utf-8 -*-
#Copyright (c) 2011, Walter Bender, Paulina Clares, Chris Rowe
# Ported to GTK3 - 2012:
# Ignacio Rodríguez <ignaciorodriguez@sugarlabs.org>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with this library; if not, write to the Free Software
# Foundation, 51 Franklin Street, Suite 500 Boston, MA 02110-1335 USA

# The challenges are arrays:
# [a fraction to display on the ball,
#  the number of segments in the bar,
#  the number of times this challenge has been played]

CHALLENGES = [[['1/2', 2, 0], ['1/3', 3, 0], ['1/4', 4, 0],
               ['2/4', 4, 0], ['2/3', 3, 0], ['3/4', 4, 0]],
              [['1/8', 8, 0], ['2/8', 8, 0],  ['3/8', 8, 0],
               ['4/8', 8, 0], ['5/8', 8, 0],  ['6/8', 8, 0],
               ['7/8', 8, 0]],
              [['1/6', 6, 0], ['2/6', 6, 0], ['3/6', 6, 0],
               ['4/6', 6, 0], ['5/6', 6, 0]],
              [['1/5', 10, 0], ['2/5', 10, 0], ['3/5', 10, 0],
               ['4/5', 10, 0]],
              [['1/10', 10, 0], ['2/10', 10, 0], ['3/10', 10, 0],
               ['4/10', 10, 0], ['5/10', 10, 0], ['6/10', 10, 0],
               ['7/10', 10, 0], ['8/10', 10, 0], ['9/10', 10, 0]],
              [['1/12', 12, 0], ['2/12', 12, 0], ['3/12', 12, 0],
               ['4/12', 12, 0], ['3/12', 12, 0], ['6/12', 12, 0],
               ['7/12', 12, 0], ['8/12', 12, 0], ['9/12', 12, 0],
               ['10/12', 12, 0], ['11/12', 12, 0]],
              [['1/16', 4, 0], ['2/16', 4, 0], ['3/16', 4, 0],
               ['4/16', 4, 0], ['5/16', 4, 0], ['6/16', 4, 0],
               ['7/16', 4, 0], ['8/16', 4, 0], ['9/16', 4, 0],
               ['10/16', 4, 0], ['11/16', 4, 0], ['12/16', 4, 0],
               ['13/16', 4, 0], ['14/16', 4, 0], ['15/16', 4, 0]]]
REWARD_HEIGHT = 25
STEPS = 100.  # number of time steps per bounce rise and fall
STEP_PAUSE = 50  # milliseconds between steps
BOUNCE_PAUSE = 3000  # milliseconds between bounces
DX = 10  # starting step size for horizontal movement
DDX = 1.25  # acceleration during keypress
ACCELEROMETER_DEVICE = '/sys/devices/platform/lis3lv02d/position'
CRASH = 'crash.ogg'  # wrong answer sound
LAUGH = 'bottle.ogg'  # correct answer sound
BUBBLES = 'bubbles.ogg'  # Easter Egg sound
from gi.repository import Gtk, Gdk, GdkPixbuf, GObject

from random import uniform
import os


from svg_utils import svg_header, svg_footer, svg_rect, svg_str_to_pixbuf, \
    svg_from_file
from play_audio import play_audio_from_file

from ball import Ball
from bar import Bar

from gettext import gettext as _

import logging
_logger = logging.getLogger('fractionbounce-activity')

try:
    from sugar3.graphics import style
    GRID_CELL_SIZE = style.GRID_CELL_SIZE
except ImportError:
    GRID_CELL_SIZE = 0

from sprites import Sprites, Sprite


class Bounce():
    ''' The Bounce class is used to define the ball and the user
    interaction. '''

    def __init__(self, canvas, path, parent=None):
        ''' Initialize the canvas and set up the callbacks. '''
        self.activity = parent

        if parent is None:        # Starting from command line
            self.sugar = False
            self.canvas = canvas
        else:                     # Starting from Sugar
            self.sugar = True
            self.canvas = canvas
            parent.show_all()

        self.canvas.grab_focus()

        if os.path.exists(ACCELEROMETER_DEVICE):
            self.accelerometer = True
        else:
            self.accelerometer = False

        self.canvas.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.canvas.add_events(Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.canvas.add_events(Gdk.EventMask.POINTER_MOTION_MASK) 
        self.canvas.add_events(Gdk.EventMask.KEY_PRESS_MASK)
        self.canvas.add_events(Gdk.EventMask.KEY_RELEASE_MASK)
        self.canvas.connect('draw', self.__draw_cb)
        self.canvas.connect('button-press-event', self._button_press_cb)
        self.canvas.connect('button-release-event', self._button_release_cb)
        self.canvas.connect('key-press-event', self._keypress_cb)
        self.canvas.connect('key-release-event', self._keyrelease_cb)
        self.canvas.set_can_focus(True)
        self.canvas.grab_focus()
        self.width = Gdk.Screen.width()
        self.height = Gdk.Screen.height() - GRID_CELL_SIZE
        self.sprites = Sprites(self.canvas)
        self.scale = Gdk.Screen.height() / 900.0
        self.timeout = None

        self.buddies = []  # used for sharing
        self.my_turn = False
        self.select_a_fraction = False

        self.easter_egg = int(uniform(1, 100))

	# Find paths to sound files
        self.path_to_success = os.path.join(path, LAUGH)
        self.path_to_failure = os.path.join(path, CRASH)
        self.path_to_bubbles = os.path.join(path, BUBBLES)

        self._create_sprites(path)

        self.challenge = 0
        self.expert = False
        self.challenges = []
        for challenge in CHALLENGES[self.challenge]:
            self.challenges.append(challenge)
        self.fraction = 0.5  # the target of the current challenge
        self.label = '1/2'  # the label
        self.count = 0  # number of bounces played
        self.correct = 0  # number of correct answers
        self.press = None  # sprite under mouse click
        self.mode = 'fractions'
        self.new_bounce = False
        self.n = 0

        self.dx = 0.  # ball horizontal trajectory
	# acceleration (with dampening)
        self.ddy = (6.67 * self.height) / (STEPS * STEPS)
        self.dy = self.ddy * (1 - STEPS) / 2.  # initial step size

    def _create_sprites(self, path):
        ''' Create all of the sprites we'll need '''
        self.smiley_graphic = svg_str_to_pixbuf(svg_from_file(
                os.path.join(path, 'smiley.svg')))

        self.frown_graphic = svg_str_to_pixbuf(svg_from_file(
                os.path.join(path, 'frown.svg')))

        self.egg_graphic = svg_str_to_pixbuf(svg_from_file(
                os.path.join(path, 'Easter_egg.svg')))

        self.blank_graphic = svg_str_to_pixbuf(
            svg_header(REWARD_HEIGHT, REWARD_HEIGHT, 1.0) + \
            svg_rect(REWARD_HEIGHT, REWARD_HEIGHT, 5, 5, 0, 0,
                     '#C0C0C0', '#282828') + \
            svg_footer())

        self.ball = Ball(self.sprites, os.path.join(path, 'soccer.svg'))
        self.current_frame = 0

        self.bar = Bar(self.sprites, self.width, self.height, self.scale,
                       self.ball.width())
        self.current_bar = self.bar.get_bar(2)

        self.ball_y_max = self.bar.bar_y() - self.ball.height()
        self.ball.move_ball((int((self.width - self.ball.width()) / 2),
                        self.ball_y_max))

    def pause(self):
        ''' Pause play when visibility changes '''
        if self.timeout is not None:
            GObject.source_remove(self.timeout)
            self.timeout = None

    def we_are_sharing(self):
        ''' If there is more than one buddy, we are sharing. '''
        if len(self.buddies) > 1:
            return True

    def its_my_turn(self):
        ''' When sharing, it is your turn... '''
        GObject.timeout_add(1000, self._take_a_turn)

    def _take_a_turn(self):
        ''' On your turn, choose a fraction. '''
        self.my_turn = True
        self.select_a_fraction = True
        self.activity.set_player_on_toolbar(self.activity.nick)
        self.activity.challenge.set_label(
            _("Click on the bar to choose a fraction."))

    def its_their_turn(self, nick):
        ''' When sharing, it is nick's turn... '''
        GObject.timeout_add(1000, self._wait_your_turn, nick)

    def _wait_your_turn(self, nick):
        ''' Wait for nick to choose a fraction. '''
        self.my_turn = False
        self.activity.set_player_on_toolbar(nick)
        self.activity.challenge.set_label(
            _('Waiting for %(buddy)s') % {'buddy': nick})

    def play_a_fraction(self, fraction):
        ''' Play this fraction '''
        fraction_is_new = True
        for i, c in enumerate(self.challenges):
            if c[0] == fraction:
                fraction_is_new = False
                self.n = i
                break
        if fraction_is_new:
            self.add_fraction(fraction)
            self.n = len(self.challenges)
        self._choose_a_fraction()
        self._move_ball()

    def _button_press_cb(self, win, event):
        ''' Callback to handle the button presses '''
        win.grab_focus()
        x, y = map(int, event.get_coords())
        self.press = self.sprites.find_sprite((x, y))
        return True

    def _button_release_cb(self, win, event):
        ''' Callback to handle the button releases '''
        win.grab_focus()
        x, y = map(int, event.get_coords())
        if self.press is not None:
            if self.we_are_sharing():
                if self.select_a_fraction and self.press == self.current_bar:
                    # Find the fraction closest to the click
                    fraction = self._search_challenges(
                        (x - self.bar.bar_x()) / float(self.bar.width()))
                    self.select_a_fraction = False
                    self.activity.send_a_fraction(fraction)
                    self.play_a_fraction(fraction)
            else:
                if self.timeout is None and self.press == self.ball.ball:
                    self._choose_a_fraction()
                    self._move_ball()
        return True

    def _search_challenges(self, f):
        ''' Find the fraction which is closest to f in the list. '''
        dist = 1.
        closest = '1/2'
        for c in self.challenges:
            numden = c[0].split('/')
            delta = abs((float(numden[0]) / float(numden[1])) - f)
            if delta <= dist:
                dist = delta
                closest = c[0]
        return closest

    def _move_ball(self):
        ''' Move the ball and test boundary conditions '''
        if self.new_bounce:
            self.bar.mark.move((0, self.height))  # hide the mark
            if not self.we_are_sharing():
                self._choose_a_fraction()
            self.new_bounce = False
            self.dy = self.ddy * (1 - STEPS) / 2  # initial step size

        if self.accelerometer:
            fh = open(ACCELEROMETER_DEVICE)
            string = fh.read()
            xyz = string[1:-2].split(',')
            self.dx = float(xyz[0]) / 18.
            fh.close()

        if self.ball.ball_x() + self.dx > 0 and \
           self.ball.ball_x() + self.dx < self.width - self.ball.width():
            self.ball.move_ball_relative((int(self.dx), int(self.dy)))
        else:
            self.ball.move_ball_relative((0, int(self.dy)))

        # speed up ball in x while key is pressed
        self.dx *= DDX

        # accelerate in y
        self.dy += self.ddy

        if self.ball.ball_y() >= self.ball_y_max:
            # hit the bottom
            self.ball.move_ball((self.ball.ball_x(), self.ball_y_max))
            self._test()
            self.new_bounce = True

            if self.we_are_sharing():
                if self.my_turn:
                    # Let the next player know it is their turn.
                    i = (self.buddies.index(self.activity.nick) + 1) % \
                        len(self.buddies)
                    self.its_their_turn(self.buddies[i])
                    self.activity.send_event('t|%s' % (self.buddies[i]))
            else:
                if self._easter_egg_test():
                    self._animate()
                else:
                    self.timeout = GObject.timeout_add(
                        max(STEP_PAUSE,
                            BOUNCE_PAUSE - self.count * STEP_PAUSE),
                        self._move_ball)
        else:
            self.timeout = GObject.timeout_add(STEP_PAUSE, self._move_ball)

    def _animate(self):
        ''' A little Easter Egg just for fun. '''
        if self.new_bounce:
            self.dy = self.ddy * (1 - STEPS) / 2  # initial step size
            self.new_bounce = False
            self.current_frame = 0
            self.frame_counter = 0
            self.ball.move_frame(self.current_frame,
                                (self.ball.ball_x(), self.ball.ball_y()))
            self.ball.move_ball((self.ball.ball_x(), self.height))
            GObject.idle_add(play_audio_from_file, self, self.path_to_bubbles)

        if self.accelerometer:
            fh = open(ACCELEROMETER_DEVICE)
            string = fh.read()
            xyz = string[1:-2].split(',')
            self.dx = float(xyz[0]) / 18.
            fh.close()
        else:
            self.dx = uniform(-int(DX * self.scale), int(DX * self.scale))
        self.ball.move_frame_relative(self.current_frame, (int(self.dx),
                                                           int(self.dy)))
        self.dy += self.ddy

        self.frame_counter += 1
        self.current_frame = self.ball.next_frame(self.frame_counter)

        if self.ball.frame_y(self.current_frame) >= self.ball_y_max:
            # hit the bottom
            self.ball.move_ball((self.ball.ball_x(), self.ball_y_max))
            self.ball.hide_frames()
            self._test(easter_egg=True)
            self.new_bounce = True
            self.timeout = GObject.timeout_add(BOUNCE_PAUSE, self._move_ball)
        else:
            GObject.timeout_add(STEP_PAUSE, self._animate)

    def add_fraction(self, string):
        ''' Add a new challenge; set bar to 2x demominator '''
        numden = string.split('/', 2)
        self.challenges.append([string, int(numden[1]), 0])

    def _choose_a_fraction(self):
        ''' Select a new fraction challenge from the table '''
        if not self.we_are_sharing():
            self.n = int(uniform(0, len(self.challenges)))
        fstr = self.challenges[self.n][0]
        if '/' in fstr:  # fraction
            numden = fstr.split('/', 2)
            self.fraction = float(numden[0].strip()) / float(numden[1].strip())
        elif '%' in fstr:  # percentage
            self.fraction = float(fstr.strip().strip('%').strip()) / 100.
        else:  # To do: add support for decimals (using locale)
            _logger.debug('Could not parse challenge (%s)', fstr)
            fstr = '1/2'
            self.fraction = 0.5

        if self.mode == 'percents':
            self.label = str(int(self.fraction * 100 + 0.5)) + '%'
        else:  # percentage
            self.label = fstr
        if self.mode == 'sectors':
            self.ball.new_ball_from_fraction(self.fraction)

        self.activity.reset_label(self.label)
        self.ball.ball.set_label(self.label)

        self.bar.hide_bars()
        if self.expert:  # Show two-segment bar in expert mode
            self.current_bar = self.bar.get_bar(2)
        else:
            if self.mode == 'percents':
                nseg = 10
            else:
                nseg = self.challenges[self.n][1]
            # generate new bar on demand
            self.current_bar = self.bar.get_bar(nseg)
            self.current_bar.move((self.bar.bar_x(), self.bar.bar_y()))
        self.current_bar.set_layer(0)

    def _easter_egg_test(self):
        ''' Test to see if we show the Easter Egg '''
        delta = self.ball.width() / 8
        x = self.ball.ball_x() + self.ball.width() / 2
        f = self.bar.width() * self.easter_egg / 100.
        if x > f - delta and x < f + delta:
            return True
        else:
            return False

    def _test(self, easter_egg=False):
        ''' Test to see if we estimated correctly '''
        self.timeout = None
        delta = self.ball.width() / 4
        x = self.ball.ball_x() + self.ball.width() / 2
        f = self.ball.width() / 2 + int(self.fraction * self.bar.width())
        self.bar.mark.move((int(f - self.bar.mark_width() / 2),
                        self.bar.bar_y() - 2))
        if self.challenges[self.n][2] == 0:  # label the column
            spr = Sprite(self.sprites, 0, 0, self.blank_graphic)
            spr.set_label(self.label)
            spr.move((int(self.n * 25), 0))
            spr.set_layer(-1)
        self.challenges[self.n][2] += 1
        if x > f - delta and x < f + delta:
            if not easter_egg:
                spr = Sprite(self.sprites, 0, 0, self.smiley_graphic)
            self.correct += 1
            GObject.idle_add(play_audio_from_file, self, self.path_to_success)
        else:
            if not easter_egg:
                spr = Sprite(self.sprites, 0, 0, self.frown_graphic)
            GObject.idle_add(play_audio_from_file, self, self.path_to_failure)

        if easter_egg:
            spr = Sprite(self.sprites, 0, 0, self.egg_graphic)

        spr.move((int(self.n * 25), int(self.challenges[self.n][2] * 25)))
        spr.set_layer(-1)

        # after enough correct answers, up the difficulty
        if self.correct == len(self.challenges) * 2:
            self.challenge += 1
            if self.challenge < len(CHALLENGES):
                for challenge in CHALLENGES[self.challenge]:
                    self.challenges.append(challenge)
            else:
                self.expert = True

        self.count += 1
        self.dx = 0.  # stop horizontal movement between bounces

    def _keypress_cb(self, area, event):
        ''' Keypress: moving the slides with the arrow keys '''
        k = Gdk.keyval_name(event.keyval)
        _logger.error(k)
        if k in ['h', 'Left', 'KP_Left']:
            self.dx = -DX * self.scale
        elif k in ['l', 'Right', 'KP_Right']:
            self.dx = DX * self.scale
        elif k in ['KP_Page_Up', 'Return']:
            self._choose_a_fraction()
            self._move_ball()
        else:
            self.dx = 0.
        return True

    def _keyrelease_cb(self, area, event):
        ''' Keyrelease: stop horizontal movement '''
        self.dx = 0.
        return True

    def __draw_cb(self, canvas, cr):
        self.sprites.redraw_sprites(cr=cr)

    def do_expose_event(self, event):
        ''' Handle the expose-event by drawing '''
        # Restrict Cairo to the exposed area
        cr = self.canvas.window.cairo_create()
        cr.rectangle(event.area.x, event.area.y,
                event.area.width, event.area.height)
        cr.clip()
        self.sprites.redraw_sprites(cr=cr)

    def _destroy_cb(self, win, event):
        ''' Callback to handle quit '''
        Gtk.main_quit()
