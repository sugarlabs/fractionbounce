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

import gtk
import os

from sugar.activity import activity
from sugar import profile
try:  # 0.86+ toolbar widgets
    from sugar.graphics.toolbarbox import ToolbarBox
    HAS_TOOLBARBOX = True
except ImportError:
    HAS_TOOLBARBOX = False
if HAS_TOOLBARBOX:
    from sugar.graphics.toolbarbox import ToolbarButton
    from sugar.activity.widgets import ActivityToolbarButton
    from sugar.activity.widgets import StopButton

import telepathy
from dbus.service import signal
from dbus.gobject_service import ExportedGObject
from sugar.presence import presenceservice
from sugar.presence.tubeconn import TubeConnection

from gettext import gettext as _

import logging
_logger = logging.getLogger('fractionbounce-activity')

from toolbar_utils import image_factory, separator_factory, combo_factory, \
    label_factory, radio_factory, button_factory, entry_factory
from utils import json_load, json_dump, chooser
from svg_utils import svg_str_to_pixbuf, generate_xo_svg

from bounce import Bounce


BALLS = [_('basketball'), _('soccer ball'), _('user defined')]
SERVICE = 'org.sugarlabs.FractionBounceActivity'
IFACE = SERVICE
PATH = '/org/augarlabs/FractionBounceActivity'


class FractionBounceActivity(activity.Activity):

    def __init__(self, handle):
        ''' Initiate activity. '''
        super(FractionBounceActivity, self).__init__(handle)

        self.nick = profile.get_nick_name()
        if profile.get_color() is not None:
            self.colors = profile.get_color().to_string().split(',')
        else:
            self.colors = ['#A0FFA0', '#FF8080']

        self.add_events(gtk.gdk.VISIBILITY_NOTIFY_MASK)
        self.connect('visibility-notify-event', self.__visibility_notify_cb)

        self.max_participants = 4  # sharing

        self._setup_toolbars()
        self._setup_dispatch_table()
        canvas = self._setup_canvas()

        # Read any custom fractions from the project metadata
        if 'custom' in self.metadata:
            custom = self.metadata['custom']
        else:
            custom = None

        # Initialize the canvas
        self.bounce_window = Bounce(canvas, activity.get_bundle_path(), self)

        # Restore any custom fractions
        if custom is not None:
            fractions = custom.split(',')
            for f in fractions:
                self.bounce_window.add_fraction(f)

        self._setup_presence_service()

    def _setup_toolbars(self):
        ''' Add buttons to toolbars '''
        custom_toolbar = gtk.Toolbar()
        if HAS_TOOLBARBOX:
            toolbox = ToolbarBox()
            self.toolbar = toolbox.toolbar
            activity_button = ActivityToolbarButton(self)
            self.toolbar.insert(activity_button, 0)
            activity_button.show()

            custom_toolbar_button = ToolbarButton(
                label=_('Custom'),
                page=custom_toolbar,
                icon_name='view-source')
            custom_toolbar.show()
            self.toolbar.insert(custom_toolbar_button, -1)
            custom_toolbar_button.show()

            self._load_standard_buttons(self.toolbar)
            separator_factory(self.toolbar, expand=True, visible=False)

            stop_button = StopButton(self)
            stop_button.props.accelerator = _('<Ctrl>Q')
            self.toolbar.insert(stop_button, -1)
            stop_button.show()

            self.set_toolbox(toolbox)
            toolbox.show()
        else:
            toolbox = activity.ActivityToolbox(self)
            self.set_toolbox(toolbox)
            self.toolbar = gtk.Toolbar()
            toolbox.add_toolbar(_('Project'), self.toolbar)
            toolbox.add_toolbar(_('Custom'), custom_toolbar)
            self._load_standard_buttons(self.toolbar)

        self._load_custom_buttons(custom_toolbar)

    def _load_standard_buttons(self, toolbar):
        ''' Load buttons onto whichever toolbar we are using '''
        self.fraction_button = radio_factory('fraction', toolbar,
                                             self._fraction_cb,
                                             tooltip=_('fractions'),
                                             group=None)
        self.percent_button = radio_factory('percent', toolbar,
                                            self._percent_cb,
                                            tooltip=_('percents'),
                                            group=self.fraction_button)
        self.player = image_factory(
            svg_str_to_pixbuf(generate_xo_svg(scale=0.8,
                                          colors=['#282828', '#000000'])),
            toolbar, tooltip=self.nick)
        separator_factory(toolbar, expand=False, visible=True)
        self.challenge = label_factory(toolbar, _("Click the ball to start."))

    def _load_custom_buttons(self, toolbar):
        ''' Entry fields and buttons for adding custom fractions '''
        self.numerator = entry_factory('', toolbar, tooltip=_('numerator'))
        label_factory(toolbar, '   /   ')
        self.denominator = entry_factory('', toolbar,
                                          tooltip=_('denominator'))
        separator_factory(toolbar, expand=False, visible=False)
        self.enter_button = button_factory('list-add', toolbar,
                                           self._add_fraction_cb,
                                           tooltip=_('add new fraction'),
                                           accelerator='Return')
        separator_factory(toolbar, expand=False, visible=True)
        self._ball_selector = combo_factory(BALLS, toolbar, self._combo_cb,
                                            default=_('basketball'),
                                            tooltip=_('choose a ball'))

    def _setup_canvas(self):
        ''' Create a canvas '''
        canvas = gtk.DrawingArea()
        canvas.set_size_request(gtk.gdk.screen_width(),
                                gtk.gdk.screen_height())
        self.set_canvas(canvas)
        canvas.show()
        self.show_all()
        return canvas

    def _combo_cb(self, arg=None):
        ''' Load a new ball based on the selector value. '''
        if not hasattr(self, '_ball_selector'):
            return
        if BALLS[self._ball_selector.get_active()] == _('basketball'):
            self.bounce_window.ball.new_ball(os.path.join(
                    activity.get_bundle_path(), 'basketball.svg'))
        elif BALLS[self._ball_selector.get_active()] == _('soccer ball'):
            self.bounce_window.ball.new_ball(os.path.join(
                    activity.get_bundle_path(), 'soccer.svg'))
        else:
            chooser(self, '', self._new_ball_from_journal)

    def _new_ball_from_journal(self, dsobject):
        ''' Load an image from the Journal. '''
        self.bounce_window.ball.new_ball_from_image(dsobject.file_path)

    def _fraction_cb(self, arg=None):
        ''' Set fraction mode '''
        self.bounce_window.mode = 'fractions'

    def _percent_cb(self, arg=None):
        ''' Set percent mode '''
        self.bounce_window.mode = 'percents'

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
            self.bounce_window.add_fraction('%d/%d' % (numerator, denominator))
            if 'custom' in self.metadata:  # Save to Journal
                self.metadata['custom'] = '%s,%d/%d' % (
                    self.metadata['custom'], numerator, denominator)
            else:
                self.metadata['custom'] = '%d/%d' % (numerator, denominator)

    def reset_label(self, fraction):
        ''' update the challenge label '''
        self.challenge.set_label(_('Bounce the ball to a position \
%(fraction)s of the way from the left side of the bar.') \
                                     % {'fraction': fraction})

    def __visibility_notify_cb(self, window, event):
        ''' Callback method for when the activity's visibility changes. '''
        # _logger.debug('%s', str(event.state))
        return

        '''
        # Awaiting resolution of #2570
        if event.state == gtk.gdk.VISIBILITY_FULLY_OBSCURED:
            _logger.debug('pause it')
            self.bounce_window.pause()
        elif event.state in \
            [gtk.gdk.VISIBILITY_UNOBSCURED, gtk.gdk.VISIBILITY_PARTIAL]:
            if not self.bounce_window.paused:
                _logger.debug('unpause it')
                self.challenge.set_label(_('Click the ball to continue'))
        '''

    # Collaboration-related methods

    def _setup_presence_service(self):
        ''' Setup the Presence Service. '''
        self.pservice = presenceservice.get_instance()
        self.initiating = None  # sharing (True) or joining (False)

        owner = self.pservice.get_owner()
        self.owner = owner
        self.bounce_window.buddies.append(self.nick)
        self._player_colors = [self.colors]
        self._player_pixbuf = [svg_str_to_pixbuf(
                generate_xo_svg(scale=0.8, colors=self.colors))]
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
        if self._shared_activity is None:
            _logger.debug('Error: Failed to share or join activity ... \
                _shared_activity is null in _shared_cb()')
            return

        self.initiating = sharer
        self.waiting_for_fraction = not sharer

        self.conn = self._shared_activity.telepathy_conn
        self.tubes_chan = self._shared_activity.telepathy_tubes_chan
        self.text_chan = self._shared_activity.telepathy_text_chan

        self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].connect_to_signal(
            'NewTube', self._new_tube_cb)

        if sharer:
            _logger.debug('This is my activity: making a tube...')
            id = self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].OfferDBusTube(
                SERVICE, {})

            self.challenge.set_label(_('Wait for others to join.'))
        else:
            _logger.debug('I am joining an activity: waiting for a tube...')
            self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].ListTubes(
                reply_handler=self._list_tubes_reply_cb,
                error_handler=self._list_tubes_error_cb)

            self.challenge.set_label(_('Wait for the sharer to start.'))

        # display your XO on the toolbar
        self.player.set_from_pixbuf(self._player_pixbuf[0])
        self.toolbar.show_all()

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

            tube_conn = TubeConnection(self.conn,
                self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES], id, \
                group_iface=self.text_chan[telepathy.CHANNEL_INTERFACE_GROUP])

            self.chattube = ChatTube(tube_conn, self.initiating, \
                self.event_received_cb)

            # Let the sharer know a new joiner has arrived.
            if self.waiting_for_fraction:
                self.send_event('j|%s' % (json_dump([self.nick,
                                                     self.colors])))

    def _setup_dispatch_table(self):
        self._processing_methods = {
            'j': [self._new_joiner, 'new joiner'],
            'b': [self._buddy_list, 'buddy list'],
            'f': [self._receive_a_fraction, 'receive a fraction'],
            't': [self._take_a_turn, 'take a turn'],
            }

    def event_received_cb(self, event_message):
        ''' Data from a tube has arrived. '''
        if len(event_message) == 0:
            return
        try:
            command, payload = event_message.split('|', 2)
        except ValueError:
            _logger.debug('Could not split event message %s', event_message)
            return
        # _logger.debug('received an event %s|%s', command, payload)
        self._processing_methods[command][0](payload)

    def _new_joiner(self, payload):
        ''' Someone has joined; sharer adds them to the buddy list. '''
        [nick, colors] = json_load(payload)
        self.challenge.set_label(nick + ' ' + _('has joined.'))
        self._append_player(nick, colors)
        if self.initiating:
            payload = json_dump([self.bounce_window.buddies,
                                 self._player_colors])
            self.send_event('b|%s' % (payload))
            if self.bounce_window.count == 0:  # Haven't started yet...
                self.bounce_window.its_my_turn()

    def _append_player(self, nick, colors):
        ''' Keep a list of players, their colors, and an XO pixbuf '''
        if not nick in self.bounce_window.buddies:
            # _logger.debug('appending %s to the buddy list', nick)
            self.bounce_window.buddies.append(nick)
            self._player_colors.append(colors)
            self._player_pixbuf.append(svg_str_to_pixbuf(
                generate_xo_svg(scale=0.8, colors=colors)))

    def _buddy_list(self, payload):
        ''' Sharer sent the updated buddy list. '''
        [buddies, colors] = json_load(payload)
        for i, nick in enumerate(buddies):
            self._append_player(nick, colors[i])

    def send_a_fraction(self, fraction):
        ''' Send a fraction to other players. '''
        payload = json_dump(fraction)
        self.send_event('f|%s' % (payload))

    def _receive_a_fraction(self, payload):
        ''' Receive a fraction from another player. '''
        fraction = json_load(payload)
        self.bounce_window.play_a_fraction(fraction)

    def _take_a_turn(self, nick):
        ''' If it is your turn, take it, otherwise, wait. '''
        if nick == self.nick:
            self.bounce_window.its_my_turn()
        else:
            self.bounce_window.its_their_turn(nick)

    def send_event(self, entry):
        ''' Send event through the tube. '''
        # _logger.debug('sending event: %s', entry)
        if hasattr(self, 'chattube') and self.chattube is not None:
            self.chattube.SendText(entry)

    def set_player_on_toolbar(self, nick):
        ''' Display the XO icon of the player whose turn it is. '''
        self.player.set_from_pixbuf(self._player_pixbuf[
                self.bounce_window.buddies.index(nick)])
        self.player.set_tooltip_text(nick)


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
