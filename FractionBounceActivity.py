# -*- coding: utf-8 -*-
# Copyright (c) 2011-14, Walter Bender
# Copyright (c) 2011 Paulina Clares, Chris Rowe
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

import os

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gdk

from sugar3 import profile
from sugar3.activity import activity
from sugar3.activity.widgets import ActivityToolbarButton
from sugar3.activity.widgets import StopButton
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.graphics.toolbarbox import ToolbarButton
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.radiotoolbutton import RadioToolButton
from sugar3.graphics.alert import NotifyAlert
from sugar3.graphics import style
from sugar3.graphics.xocolor import XoColor
from sugar3.graphics.icon import Icon

import telepathy
from dbus.service import signal
from dbus.gobject_service import ExportedGObject
from sugar3.presence import presenceservice

try:
    from sugar3.presence.wrapper import CollabWrapper
except ImportError:
    from collabwrapper import CollabWrapper

from gettext import gettext as _

import logging
_logger = logging.getLogger('fractionbounce-activity')
_logger.setLevel(logging.DEBUG)

from utils import json_load, json_dump, chooser
from svg_utils import svg_str_to_pixbuf, generate_xo_svg

from bounce import Bounce
from aplay import aplay

BALLDICT = {'basketball': [_('basketball'), 'wood'],
            'soccerball': [_('soccer ball'), 'grass'],
            'rugbyball': [_('rugby ball'), 'grass'],
            'bowlingball': [_('bowling ball'), 'wood'],
            'beachball': [_('beachball'), 'sand'],
            'feather': [_('feather'), 'clouds'],
            'custom': [_('user defined'), None]}
BGDICT = {'grass': [_('grass'), 'grass_background.png'],
          'wood': [_('wood'), 'parquet_background.png'],
          'clouds': [_('clouds'), 'feather_background.png'],
          'sand': [_('sand'), 'beach_background.png'],
          'custom': [_('user defined'), None]}

SERVICE = 'org.sugarlabs.FractionBounceActivity'
IFACE = SERVICE
PATH = '/org/augarlabs/FractionBounceActivity'


class FractionBounceActivity(activity.Activity):

    def __init__(self, handle):
        ''' Initiate activity. '''
        super(FractionBounceActivity, self).__init__(handle)

        self.nick = profile.get_nick_name()
        if profile.get_color() is not None:
            self._colors = profile.get_color().to_string().split(',')
        else:
            self._colors = ['#A0FFA0', '#FF8080']

        self.max_participants = 4  # sharing
        self._playing = True

        self._setup_toolbars()
        self._setup_dispatch_table()
        canvas = self._setup_canvas()

        # Read any custom fractions from the project metadata
        if 'custom' in self.metadata:
            custom = self.metadata['custom']
        else:
            custom = None

        self._current_ball = 'soccerball'

        self._toolbar_was_expanded = False

        # Initialize the canvas
        self._bounce_window = Bounce(canvas, activity.get_bundle_path(), self)

        Gdk.Screen.get_default().connect('size-changed', self._configure_cb)

        # Restore any custom fractions
        if custom is not None:
            fractions = custom.split(',')
            for f in fractions:
                self._bounce_window.add_fraction(f)

        if self.shared_activity:
            # We're joining
            if not self.get_shared():
                xocolors = XoColor(profile.get_color().to_string())
                share_icon = Icon(icon_name='zoom-neighborhood',
                                  xo_color=xocolors)
                self._joined_alert = NotifyAlert()
                self._joined_alert.props.icon = share_icon
                self._joined_alert.props.title = _('Please wait')
                self._joined_alert.props.msg = _('Starting connection...')
                self._joined_alert.connect('response', self._alert_cancel_cb)
                self.add_alert(self._joined_alert)

                self._label.set_label(_('Wait for the sharer to start.'))

                # Wait for joined signal
                self.connect("joined", self._joined_cb)

        self._setup_sharing()

    def close(self, **kwargs):
        aplay.close()
        activity.Activity.close(self, **kwargs)

    def _configure_cb(self, event):
        if Gdk.Screen.width() < 1024:
            self._label.set_size_request(275, -1)
            self._label.set_label('')
            self._separator.set_expand(False)
        else:
            self._label.set_size_request(500, -1)
            self._separator.set_expand(True)

        self._bounce_window.configure_cb(event)
        if self._toolbar_expanded():
            self._bounce_window.bar.bump_bars('up')
            self._bounce_window.ball.ball.move_relative(
                (0, -style.GRID_CELL_SIZE))

    def _toolbar_expanded(self):
        if self._activity_button.is_expanded():
            return True
        elif self._custom_toolbar_button.is_expanded():
            return True
        return False

    def _update_graphics(self, widget):
        # We need to catch opening and closing of toolbars and ignore
        # switching between open toolbars.
        if self._toolbar_expanded():
            if not self._toolbar_was_expanded:
                self._bounce_window.bar.bump_bars('up')
                self._bounce_window.ball.ball.move_relative(
                    (0, -style.GRID_CELL_SIZE))
                self._toolbar_was_expanded = True
        else:
            if self._toolbar_was_expanded:
                self._bounce_window.bar.bump_bars('down')
                self._bounce_window.ball.ball.move_relative(
                    (0, style.GRID_CELL_SIZE))
                self._toolbar_was_expanded = False

    def _setup_toolbars(self):
        custom_toolbar = Gtk.Toolbar()
        toolbox = ToolbarBox()
        self._toolbar = toolbox.toolbar
        self._activity_button = ActivityToolbarButton(self)
        self._activity_button.connect('clicked', self._update_graphics)
        self._toolbar.insert(self._activity_button, 0)
        self._activity_button.show()

        self._custom_toolbar_button = ToolbarButton(
            label=_('Custom'),
            page=custom_toolbar,
            icon_name='view-source')
        self._custom_toolbar_button.connect('clicked', self._update_graphics)
        custom_toolbar.show()
        self._toolbar.insert(self._custom_toolbar_button, -1)
        self._custom_toolbar_button.show()

        self._load_standard_buttons(self._toolbar)

        self._separator = Gtk.SeparatorToolItem()
        self._separator.props.draw = False
        self._separator.set_expand(True)
        self._toolbar.insert(self._separator, -1)
        self._separator.show()

        stop_button = StopButton(self)
        stop_button.props.accelerator = _('<Ctrl>Q')
        self._toolbar.insert(stop_button, -1)
        stop_button.show()
        self.set_toolbar_box(toolbox)
        toolbox.show()

        self._load_custom_buttons(custom_toolbar)

    def _load_standard_buttons(self, toolbar):
        fraction_button = RadioToolButton(group=None)
        fraction_button.set_icon_name('fraction')
        fraction_button.set_tooltip(_('fractions'))
        fraction_button.connect('clicked', self._fraction_cb)
        toolbar.insert(fraction_button, -1)
        fraction_button.show()

        sector_button = RadioToolButton(group=fraction_button)
        sector_button.set_icon_name('sector')
        sector_button.set_tooltip(_('sectors'))
        sector_button.connect('clicked', self._sector_cb)
        toolbar.insert(sector_button, -1)
        sector_button.show()

        percent_button = RadioToolButton(group=fraction_button)
        percent_button.set_icon_name('percent')
        percent_button.set_tooltip(_('percents'))
        percent_button.connect('clicked', self._percent_cb)
        toolbar.insert(percent_button, -1)
        percent_button.show()

        self._player = Gtk.Image()
        self._player.set_from_pixbuf(svg_str_to_pixbuf(
            generate_xo_svg(scale=0.8, colors=['#282828', '#282828'])))
        self._player.set_tooltip_text(self.nick)
        toolitem = Gtk.ToolItem()
        toolitem.add(self._player)
        self._player.show()
        toolbar.insert(toolitem, -1)
        toolitem.show()

        self._label = Gtk.Label(_("Click the ball to start."))
        self._label.set_line_wrap(True)
        if Gdk.Screen.width() < 1024:
            self._label.set_size_request(275, -1)
        else:
            self._label.set_size_request(500, -1)
        self.toolitem = Gtk.ToolItem()
        self.toolitem.add(self._label)
        self._label.show()
        toolbar.insert(self.toolitem, -1)
        self.toolitem.show()

    def _load_custom_buttons(self, toolbar):
        self.numerator = Gtk.Entry()
        self.numerator.set_text('')
        self.numerator.set_tooltip_text(_('numerator'))
        self.numerator.set_width_chars(3)
        toolitem = Gtk.ToolItem()
        toolitem.add(self.numerator)
        self.numerator.show()
        toolbar.insert(toolitem, -1)
        toolitem.show()

        label = Gtk.Label('   /   ')
        toolitem = Gtk.ToolItem()
        toolitem.add(label)
        label.show()
        toolbar.insert(toolitem, -1)
        toolitem.show()

        self.denominator = Gtk.Entry()
        self.denominator.set_text('')
        self.denominator.set_tooltip_text(_('denominator'))
        self.denominator.set_width_chars(3)
        toolitem = Gtk.ToolItem()
        toolitem.add(self.denominator)
        self.denominator.show()
        toolbar.insert(toolitem, -1)
        toolitem.show()

        button = ToolButton('list-add')
        button.set_tooltip(_('add new fraction'))
        button.props.sensitive = True
        button.props.accelerator = 'Return'
        button.connect('clicked', self._add_fraction_cb)
        toolbar.insert(button, -1)
        button.show()

        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(False)
        toolbar.insert(separator, -1)
        separator.show()

        button = ToolButton('soccerball')
        button.set_tooltip(_('choose a ball'))
        button.props.sensitive = True
        button.connect('clicked', self._button_palette_cb)
        toolbar.insert(button, -1)
        button.show()
        self._ball_palette = button.get_palette()
        button_grid = Gtk.Grid()
        row = 0
        for ball in BALLDICT.keys():
            if ball == 'custom':
                button = ToolButton('view-source')
            else:
                button = ToolButton(ball)
            button.connect('clicked', self._load_ball_cb, None, ball)
            eventbox = Gtk.EventBox()
            eventbox.connect('button_press_event', self._load_ball_cb,
                             ball)
            label = Gtk.Label(BALLDICT[ball][0])
            eventbox.add(label)
            label.show()
            button_grid.attach(button, 0, row, 1, 1)
            button.show()
            button_grid.attach(eventbox, 1, row, 1, 1)
            eventbox.show()
            row += 1
        self._ball_palette.set_content(button_grid)
        button_grid.show()

        button = ToolButton('insert-picture')
        button.set_tooltip(_('choose a background'))
        button.props.sensitive = True
        button.connect('clicked', self._button_palette_cb)
        toolbar.insert(button, -1)
        button.show()
        self._bg_palette = button.get_palette()
        button_grid = Gtk.Grid()
        row = 0
        for bg in BGDICT.keys():
            if bg == 'custom':
                button = ToolButton('view-source')
            else:
                button = ToolButton(bg)
            button.connect('clicked', self._load_bg_cb, None, bg)
            eventbox = Gtk.EventBox()
            eventbox.connect('button_press_event', self._load_bg_cb, bg)
            label = Gtk.Label(BGDICT[bg][0])
            eventbox.add(label)
            label.show()
            button_grid.attach(button, 0, row, 1, 1)
            button.show()
            button_grid.attach(eventbox, 1, row, 1, 1)
            eventbox.show()
            row += 1
        self._bg_palette.set_content(button_grid)
        button_grid.show()

    def _button_palette_cb(self, button):
        palette = button.get_palette()
        if palette:
            if not palette.is_up():
                palette.popup(immediate=True, state=palette.SECONDARY)
            else:
                palette.popdown(immediate=True)

    def can_close(self):
        # Let everyone know we are leaving...
        if hasattr(self, '_bounce_window') and \
           self._bounce_window.we_are_sharing():
            self._playing = False
            self.send_event('l', {"data": (json_dump([self.nick]))})
        return True

    def _setup_canvas(self):
        canvas = Gtk.DrawingArea()
        canvas.set_size_request(Gdk.Screen.width(),
                                Gdk.Screen.height())
        self.set_canvas(canvas)
        canvas.show()
        return canvas

    def _load_bg_cb(self, widget, event, bg):
        if bg == 'custom':
            chooser(self, 'Image', self._new_background_from_journal)
        else:
            self._bounce_window.set_background(BGDICT[bg][1])

    def _load_ball_cb(self, widget, event, ball):
        if ball == 'custom':
            chooser(self, 'Image', self._new_ball_from_journal)
        else:
            self._bounce_window.ball.new_ball(os.path.join(
                activity.get_bundle_path(), 'images', ball + '.svg'))
            self._bounce_window.set_background(BGDICT[BALLDICT[ball][1]][1])
        self._current_ball = ball

    def _reset_ball(self):
        ''' If we switch back from sector mode, we need to restore the ball '''
        if self._bounce_window.mode != 'sectors':
            return

        if self._current_ball == 'custom':  # TODO: Reload custom ball
            self._current_ball = 'soccerball'
        self._bounce_window.ball.new_ball(os.path.join(
            activity.get_bundle_path(), 'images', self._current_ball + '.svg'))

    def _new_ball_from_journal(self, dsobject):
        ''' Load an image from the Journal. '''
        self._bounce_window.ball.new_ball_from_image(
            dsobject.file_path,
            os.path.join(activity.get_activity_root(), 'tmp', 'custom.png'))

    def _new_background_from_journal(self, dsobject):
        ''' Load an image from the Journal. '''
        self._bounce_window.new_background_from_image(None, dsobject=dsobject)

    def _fraction_cb(self, arg=None):
        ''' Set fraction mode '''
        self._reset_ball()
        self._bounce_window.mode = 'fractions'

    def _percent_cb(self, arg=None):
        ''' Set percent mode '''
        self._reset_ball()
        self._bounce_window.mode = 'percents'

    def _sector_cb(self, arg=None):
        ''' Set sector mode '''
        self._bounce_window.mode = 'sectors'

    def _add_fraction_cb(self, arg=None):
        ''' Read entries and add a fraction to the list '''
        try:
            numerator = int(self.numerator.get_text().strip())
        except ValueError:
            self.numerator.set_text('NAN')
            numerator = 0
        try:
            denominator = int(self.denominator.get_text().strip())
        except ValueError:
            self.denominator.set_text('NAN')
            denominator = 1
        if denominator == 0:
            self.denominator.set_text('ZDE')
        if numerator > denominator:
            numerator = 0
        if numerator > 0 and denominator > 1:
            fraction = '%d/%d' % (numerator, denominator)
            self._bounce_window.add_fraction(fraction)
            if 'custom' in self.metadata:  # Save to Journal
                self.metadata['custom'] = '%s,%s' % (
                    self.metadata['custom'], fraction)
            else:
                self.metadata['custom'] = fraction

            self.alert(
                _('New fraction'),
                _('Your fraction, %s, has been added to the program' %
                  (fraction)))

    def reset_label(self, label):
        ''' update the challenge label '''
        self._label.set_label(label)

    def alert(self, title, text=None):
        alert = NotifyAlert(timeout=5)
        alert.props.title = title
        alert.props.msg = text
        self.add_alert(alert)
        alert.connect('response', self._alert_cancel_cb)
        alert.show()

    def _alert_cancel_cb(self, alert, response_id):
        self.remove_alert(alert)

    # Collaboration-related methods

    def _setup_sharing(self):
        ''' Setup the Presence Service. '''
        self.pservice = presenceservice.get_instance()
        self.initiating = None  # sharing (True) or joining (False)

        owner = self.pservice.get_owner()
        self.owner = owner
        self._bounce_window.buddies.append(self.nick)
        self._player_colors = [self._colors]
        self._player_pixbufs = [
            svg_str_to_pixbuf(generate_xo_svg(scale=0.8, colors=self._colors))
        ]
        self._share = ''
        self.connect('shared', self._shared_cb)
        self.connect('joined', self._joined_cb)

    def _shared_cb(self, activity):
        ''' Either set up initial share...'''
        self._new_tube_common(True)

    def _joined_cb(self, activity):
        ''' ...or join an exisiting share. '''
        self._new_tube_common(False)

    def _new_tube_common(self, sharer):
        ''' Joining and sharing are mostly the same... '''
        if self.shared_activity is None:
            _logger.debug('Error: Failed to share or join activity ... \
                shared_activity is null in _shared_cb()')
            return

        self.initiating = sharer
        self.waiting_for_fraction = not sharer

        self.conn = self.shared_activity.telepathy_conn
        self.tubes_chan = self.shared_activity.telepathy_tubes_chan
        self.text_chan = self.shared_activity.telepathy_text_chan

        self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].connect_to_signal(
            'NewTube', self._new_tube_cb)

        if sharer:
            _logger.debug('This is my activity: making a tube...')
            id = self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].OfferDBusTube(
                SERVICE, {})

            self._label.set_label(_('Wait for others to join.'))
        else:
            _logger.debug('I am joining an activity: waiting for a tube...')
            self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].ListTubes(
                reply_handler=self._list_tubes_reply_cb,
                error_handler=self._list_tubes_error_cb)

        # display your XO on the toolbar
        self._player.set_from_pixbuf(self._player_pixbufs[0])

    def _list_tubes_reply_cb(self, tubes):
        ''' Reply to a list request. '''
        for tube_info in tubes:
            self._new_tube_cb(*tube_info)

    def _list_tubes_error_cb(self, e):
        ''' Log errors. '''
        _logger.debug('Error: ListTubes() failed: %s', e)

    def _new_tube_cb(self, id, initiator, type, service, params, state):
        ''' Create a new tube. '''
        _logger.debug(
            'Newtube: ID=%d initator=%d type=%d service=%s params=%r state=%d',
            id, initiator, type, service, params, state)

        if (type == telepathy.TUBE_TYPE_DBUS and service == SERVICE):
            if state == telepathy.TUBE_STATE_LOCAL_PENDING:
                self.tubes_chan[ \
                              telepathy.CHANNEL_TYPE_TUBES].AcceptDBusTube(id)

            self.collab = CollabWrapper(self)
            self.collab.message.connect(self.event_received_cb)
            self.collab.setup()

            # Let the sharer know a new joiner has arrived.
            if self.waiting_for_fraction:
                self.send_event('j', {"data": (json_dump([self.nick,
                                                     self._colors]))})

    def _setup_dispatch_table(self):
        self._processing_methods = {
            'j': [self._new_joiner, 'new joiner'],
            'b': [self._buddy_list, 'buddy list'],
            'f': [self._receive_a_fraction, 'receive a fraction'],
            't': [self._take_a_turn, 'take a turn'],
            'l': [self._buddy_left, 'buddy left']
            }

    def event_received_cb(self, collab, buddy, msg):
        ''' Data from a tube has arrived. '''
        command = msg.get('command')
        if command is None:
            return
        payload = msg.get('data')
        _logger.error('received an event %s %s', command, payload)
        if self._playing:
            self._processing_methods[command][0](payload)

    def _buddy_left(self, payload):
        [nick] = json_load(payload)
        self._label.set_label(nick + ' ' + _('has left.'))
        if self.initiating:
            self._remove_player(nick)
            payload = json_dump([self._bounce_window.buddies,
                                 self._player_colors])
            self.send_event('b', {"data": payload})
            # Restart from sharer's turn
            self._bounce_window.its_my_turn()

    def _new_joiner(self, payload):
        ''' Someone has joined; sharer adds them to the buddy list. '''
        [nick, colors] = json_load(payload)
        self._label.set_label(nick + ' ' + _('has joined.'))
        if self.initiating:
            self._append_player(nick, colors)
            payload = json_dump([self._bounce_window.buddies,
                                 self._player_colors])
            self.send_event('b', {"data": payload})
            if self._bounce_window.count == 0:  # Haven't started yet...
                self._bounce_window.its_my_turn()

    def _remove_player(self, nick):
        if nick in self._bounce_window.buddies:
            i = self._bounce_window.buddies.index(nick)
            self._bounce_window.buddies.remove(nick)
            self._player_colors.remove(self._player_colors[i])
            self._player_pixbufs.remove(self._player_pixbufs[i])

    def _append_player(self, nick, colors):
        ''' Keep a list of players, their colors, and an XO pixbuf '''
        if not nick in self._bounce_window.buddies:
            _logger.debug('appending %s to the buddy list', nick)
            self._bounce_window.buddies.append(nick)
            self._player_colors.append([str(colors[0]), str(colors[1])])
            self._player_pixbufs.append(svg_str_to_pixbuf(
                generate_xo_svg(scale=0.8,
                                colors=self._player_colors[-1])))

    def _buddy_list(self, payload):
        '''Sharer sent the updated buddy list, so regenerate internal lists'''
        if not self.initiating:
            [buddies, colors] = json_load(payload)
            self._bounce_window.buddies = buddies[:]
            self._player_colors = colors[:]
            self._player_pixbufs = []
            for colors in self._player_colors:
                self._player_pixbufs.append(svg_str_to_pixbuf(
                    generate_xo_svg(scale=0.8,
                                    colors=[str(colors[0]), str(colors[1])])))

    def send_a_fraction(self, fraction):
        ''' Send a fraction to other players. '''
        payload = json_dump(fraction)
        self.send_event('f', {"data": payload})

    def _receive_a_fraction(self, payload):
        ''' Receive a fraction from another player. '''
        fraction = json_load(payload)
        self._bounce_window.play_a_fraction(fraction)

    def _take_a_turn(self, nick):
        ''' If it is your turn, take it, otherwise, wait. '''
        if nick == self.nick:
            self._bounce_window.its_my_turn()
        else:
            self._bounce_window.its_their_turn(nick)

    def send_event(self, command, data):
        ''' Send event through the tube. '''
        _logger.error('sending event: %s', command)
        if hasattr(self, 'collab') and self.collab is not None:
            data["command"] = command
            _logger.error('send_event %r', data)
            self.collab.post(data)

    def set_player_on_toolbar(self, nick):
        ''' Display the XO icon of the player whose turn it is. '''
        self._player.set_from_pixbuf(self._player_pixbufs[
                self._bounce_window.buddies.index(nick)])
        self._player.set_tooltip_text(nick)


class ChatTube(ExportedGObject):
    ''' Class for setting up tube for sharing '''

    def __init__(self, tube, is_initiator, stack_received_cb):
        super(ChatTube, self).__init__(tube, PATH)
        self.tube = tube
        self.is_initiator = is_initiator  # Are we sharing or joining activity?
        self.stack_received_cb = stack_received_cb
        self.stack = ''

        self.tube.add_signal_receiver(self.send_stack_cb, 'SendText', IFACE,
                                      path=PATH, sender_keyword='sender')

    def send_stack_cb(self, text, sender=None):
        if sender == self.tube.get_unique_name():
            return
        self.stack = text
        self.stack_received_cb(text)

    @signal(dbus_interface=IFACE, signature='s')
    def SendText(self, text):
        self.stack = text
