import time
import sys

from code.tools.xml import XMLParser

from code.utils.common import log, log2, logn, xml_encode, xml_decode

from code.constants.common import TILE_WIDTH, TILE_HEIGHT, COLLISION_NONE, COLLISION_LADDER, COLLISION_MONKEYBAR, GENUS_PLAYER, GENUS_ENEMY, DIG_RESULT_SUCCESS
from code.constants.common import LAYER_FOREGROUND, MODE_GAME # Need these for activating map when client joins

from code.constants.states import STATUS_ACTIVE, STATUS_INACTIVE
from code.constants.death import DEATH_BY_VAPORIZATION

from code.constants.network import *

from code.constants.newsfeeder import *

# The network controller inherits these functions.  These functions
# send various messages over the wire.  Each function may have a
# distinct list of params, but each will include the control center
# and the universe.
class NetworkControllerSendFunctionsExt:

    def __init__(self):

        return


    # Send a simple ping reqeuest to make sure a player is still there somewhere
    def send_ping(self, control_center, universe):

        # Server
        if ( self.get_status() == NET_STATUS_SERVER ):

            # Loop connected players
            for conn in self.get_active_connections():

                # Send a simple ping with current timestamp.
                # When the client responds (with original timestamp),
                # we can calculate the overall travel time.
                self.mail(
                    conn,
                    self.build_message_by_command_type(
                        command_type = NET_MSG_PING,
                        universe = universe,
                        actor = None,
                        params = {
                            "timestamp": "%s" % time.time()
                        }
                    )
                )


    # Send a simple ping response (pong)
    def send_pong(self, timestamp, control_center, universe):

        # Server (not coded)
        if ( self.get_status() == NET_STATUS_SERVER ):

            pass

        # Client sends back a ping response and
        # includes the server's original timestamp.
        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # Send back the pong
            self.send_to_server(
                self.build_message_by_command_type(
                    command_type = NET_MSG_PONG,
                    universe = universe,
                    actor = None,
                    params = {
                        "timestamp": "%s" % timestamp
                    }
                )
            )


    # Server - Send a message to all clients letting them know the server is going offline
    # Client - n/a
    def send_server_disconnecting(self, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            # Main all connected players
            for conn in self.get_active_connections():

                # Query player id
                player_id = self.get_player_id_by_connection(conn)

                # Calculate key to lock with
                key = "server-disconnecting.%d" % player_id


                # Faux lock
                universe.lock_with_key(
                    key = key,
                    timeout = 120,
                    strength = LOCK_NONE,
                    f_on_timeout = None
                )


                # Mail player
                self.mail(
                    conn,
                    self.build_message_by_command_type(
                        command_type = NET_MSG_SERVER_DISCONNECTING,
                        universe = universe,
                        actor = None,
                        params = {
                            "key": key
                        }
                    )
                )


            # Send a message to the web server to remove this session from the list.
            control_center.get_http_request_controller().send_get_with_name(
                name = "end-session",
                host = None, # use default
                port = 80,
                url = "/games/alrs/sessions/end.session.php",
                params = {
                    "id": universe.get_session_variable("net.session.id").get_value()
                },
                tracked = True,
                force = True
            )

            logn( "netcode", "Session id = %s\n" % universe.get_session_variable("net.session.id").get_value() )

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            pass


    # Server - Send a message to any remaining client that some client has disconnected from the game
    # Client - Send a message to the server that we're disconnecting; await receipt (for a bit).
    def send_client_disconnecting(self, disconnecting_player_id, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            # Mail each remaining player
            for conn in self.get_active_connections():

                # Query player id
                player_id = self.get_player_id_by_connection(conn)

                # Calculate key to lock with
                key = "client-disconnecting.%d.%d" % (disconnecting_player_id, player_id)


                # Faux lock
                universe.lock_with_key(
                    key = key,
                    timeout = 120,
                    strength = LOCK_NONE,
                    f_on_timeout = None
                )


                # Mail player
                self.mail(
                    conn,
                    self.build_message_by_command_type(
                        command_type = NET_MSG_CLIENT_DISCONNECTING,
                        universe = universe,
                        actor = None,
                        params = {
                            "key": key,
                            "player-id": disconnecting_player_id
                        }
                    )
                )

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # Set a key
            key = "client-disconnecting"

            # Lock
            universe.lock_with_key(
                key = key,
                timeout = 120,
                strength = LOCK_HARD,
                f_on_timeout = None
            )

            # Send quit notice to the server
            self.send_to_server(
                self.build_message_by_command_type(
                    command_type = NET_MSG_CLIENT_DISCONNECTING,
                    universe = universe,
                    actor = None,
                    params = {
                        "key": key,
                        "player-id": disconnecting_player_id
                    }
                )
            )


    # Server - Send message to a client that we received its "I'm disconnecting" notice
    # Client - Send message to the server confirming that we received its "I'm ending this session" notice
    def send_confirm_disconnect_by_connection(self, conn, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            # Just send it once (?)
            self.mail(
                conn,
                self.build_message_by_command_type(
                    command_type = NET_MSG_CONFIRM_DISCONNECT,
                    universe = universe,
                    actor = None,
                    params = {}
                )
            )

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # Just send it once (?)
            self.send_to_server(
                self.build_message_by_command_type(
                    command_type = NET_MSG_CONFIRM_DISCONNECT,
                    universe = universe,
                    actor = None,
                    params = {}
                )
            )


    # Server - Send a chat message
    # Client - SAME
    def send_chat(self, msg, control_center, universe):

        # What's the local player id?
        player_id = int( universe.get_session_variable("core.player-id").get_value() )

        # What's the local nick?
        nick = universe.get_session_variable("net.player%d.nick" % player_id).get_value()


        # Affix local nick to the message
        chatline = "%s:  %s" % (nick, msg)


        # Special /nick command?
        if ( msg.startswith("/nick ") ):

            # Parse input nick
            new_nick = msg[ len("/nick ") : len(msg) ].strip()


            # Validate nick
            result = self.validate_nick(new_nick)

            # Good?
            if (result == NICK_OK):

                # Update the local nick
                universe.set_session_variable("net.player%d.nick" % player_id, new_nick)

                # Request an update to the intro panel, in case it's needed...
                universe.set_session_variable("net.rebuild-intro-menu", "1")


                # Save the updated netplay preferences
                control_center.save_netplay_preferences(universe)


                # Sync local player
                self.send_sync_local_player(control_center, universe)

                # Send special chatline announcement (x now known as y)
                for conn in self.get_active_connections():

                    # Mail player
                    self.mail(
                        conn,
                        self.build_message_by_command_type(
                            command_type = NET_MSG_CHAT,
                            universe = self,
                            actor = None,
                            params = {
                                "msg": "%s is now known as [color=special]%s[/color]." % (nick, new_nick)
                            }
                        )
                    )


                # Provide confirmation in the console
                self.net_console.add("You are now known as '%s'" % new_nick)

            # No; we'll display an error response...
            else:

                if (result == NICK_ERROR_LENGTH):

                    self.net_console.add("Nick must have a length of 3 - 8 alphanumeric characters...")

                elif (result == NICK_ERROR_INVALID):

                    self.net_console.add("Nick must contain only letters and numbers...")

        # Normal chatline
        else:

            # Send the chatline to each active connection
            for conn in self.get_active_connections():

                # Mail player
                self.mail(
                    conn,
                    self.build_message_by_command_type(
                        command_type = NET_MSG_CHAT,
                        universe = self,
                        actor = None,
                        params = {
                            "msg": chatline
                        }
                    )
                )

            # Also add the message to the local console
            self.net_console.add(chatline)


    # Send an unlock message (receipt of confirmation).
    # Send to a given connection.
    def send_unlock_with_key(self, key, conn, control_center, universe):

        self.mail(
            conn,
            self.build_message_by_command_type(
                command_type = NET_MSG_UNLOCK,
                universe = universe,
                actor = None,
                params = {
                    "key": key
                }
            )
        )


    # Server - Send notice to clients that the "vote to skip level" tally has increased
    # Client - n/a
    def send_vote_to_skip(self, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            # Mail each player
            for conn in self.get_active_connections():

                # Query player id
                player_id = self.get_player_id_by_connection(conn)

                # Calculate key to lock with
                key = "vote-to-skip.%d" % player_id


                # Faux lock
                universe.lock_with_key(
                    key = key,
                    timeout = 120,
                    strength = LOCK_NONE,
                    f_on_timeout = None
                )


                # Mail player
                self.mail(
                    conn,
                    self.build_message_by_command_type(
                        command_type = NET_MSG_VOTE_TO_SKIP,
                        universe = universe,
                        actor = None,
                        params = {
                            "key": key
                        }
                    )
                )


    # Server - Sync a newly-joining player by connection
    # Client - n/a
    def send_sync_new_player_by_connection(self, conn, control_center, universe):

        # Query player id
        player_id = self.get_player_id_by_connection(conn)

        # Calculate key
        key = "sync-new.%d" % player_id


        # Configure an XML string holding each player's data...
        xml = "<data><active-map>%s</active-map>" % xml_encode( universe.get_active_map().get_name() )

        xml += "<players new-client = '1'>"

        for i in range(1, 5):

            # Skip the player id we're sending data to; they already have their local nick/status/avatar data...
            if ( i != player_id ):

                params = (
                    i,
                    xml_encode( universe.get_session_variable("net.player%d.nick" % i).get_value() ),
                    xml_encode( universe.get_session_variable("net.player%d.joined" % i).get_value() ),
                    xml_encode( universe.get_session_variable("net.player%d.ready" % i).get_value() ),
                    xml_encode( universe.get_session_variable("net.player%d.avatar.colors" % i).get_value() )
                )

                xml += "<player id = '%d' nick = '%s' joined = '%s' ready = '%s' avatar-data = '%s' />" % params

        xml += "</players>"

        xml += "</data>"


        # Faux lock
        universe.lock_with_key(
            key = key,
            timeout = 120,
            strength = LOCK_NONE,
            f_on_timeout = None
        )


        # Send sync data
        self.mail(
            conn,
            self.build_message_by_command_type(
                command_type = NET_MSG_SYNC_ALL_PLAYERS,
                universe = universe,
                actor = None,
                params = {
                    "key": key,
                    "xml": xml
                }
            )
        )


    # Server - Update player data for local player;
    #          forward changes to all other players.
    # Client - Update client data for specified (other player).
    def send_sync_local_player(self, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            # Local player id
            local_id = int( universe.get_session_variable("core.player-id").get_value() )


            # Send through all active connections
            for conn in self.get_active_connections():

                # Query player id
                player_id = self.get_player_id_by_connection(conn)

                # Create key
                key = "sync-player.%d.%d" % (local_id, player_id)


                # Faux lock
                universe.lock_with_key(
                    key = key,
                    timeout = 120,
                    strength = LOCK_NONE,
                    f_on_timeout = None
                )


                # Mail message
                self.mail(
                    conn,
                    self.build_message_by_command_type(
                        command_type = NET_MSG_SYNC_PLAYER,
                        universe = universe,
                        actor = None,
                        params = {
                            "key": key,
                            "player-id": local_id,
                            "online-status": "online",
                            "ready-status": universe.get_session_variable("net.player%d.ready" % local_id).get_value(),
                            "nick": universe.get_session_variable("net.player%d.nick" % local_id).get_value(),
                            "avatar-data": universe.get_session_variable("net.player%d.avatar.colors" % local_id).get_value()
                        }
                    )
                )

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # Local player id
            local_id = int( universe.get_session_variable("core.player-id").get_value() )


            # Create key
            key = "sync-player.client"


            # Faux lock
            universe.lock_with_key(
                key = key,
                timeout = 120,
                strength = LOCK_NONE,
                f_on_timeout = None
            )


            # Mail to server
            self.send_to_server(
                self.build_message_by_command_type(
                    command_type = NET_MSG_SYNC_PLAYER,
                    universe = universe,
                    actor = None,
                    params = {
                        "key": key,
                        "player-id": local_id,
                        "online-status": "online",
                        "ready-status": universe.get_session_variable("net.player%d.ready" % local_id).get_value(),
                        "nick": universe.get_session_variable("net.player%d.nick" % local_id).get_value(),
                        "avatar-data": universe.get_session_variable("net.player%d.avatar.colors" % local_id).get_value()
                    }
                )
            )


    # Server - Send all clients a "vote to skip" command, increasing their tallies
    # Client - Send the server notice that we voted to skip.  Wait for confirmation before we tally.
    def send_vote_to_skip(self, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            # Send all active connections a vote tally
            for conn in self.get_active_connections():

                # Query player id
                player_id = self.get_player_id_by_connection(conn)

                # Calculate a key
                key = "vote.%d" % player_id


                # Faux lock
                universe.lock_with_key(
                    key = key,
                    timeout = 120,
                    strength = LOCK_NONE,
                    f_on_timeout = None
                )


                # Mail message
                self.mail(
                    conn,
                    self.build_message_by_command_type(
                        command_type = NET_MSG_VOTE_TO_SKIP,
                        universe = universe,
                        actor = None,
                        params = {
                            "key": key
                        }
                    )
                )

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            key = "vote.send"

            # Faux lock
            universe.lock_with_key(
                key = key,
                timeout = 120,
                strength = LOCK_NONE,
                f_on_timeout = None
            )


            # Send message to server
            self.send_to_server(
                self.build_message_by_command_type(
                    command_type = NET_MSG_VOTE_TO_SKIP,
                    universe = universe,
                    actor = None,
                    params = {
                        "key": key
                    }
                )
            )


    # Server - Send begin game command to all clients
    # Client - n/a
    def send_begin_game(self, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            # Flag the game as being in progress...
            universe.set_session_variable("net.game-in-progress", "1")


            # The server will prepare its local multiplayer session.
            # Clients will follow suit when they receive the begin game message...
            universe.prepare_multiplayer_session()


            # Now inform all clients that the game is beginning
            for conn in self.get_active_connections():

                # Query player id
                player_id = self.get_player_id_by_connection(conn)

                # Calculate a key
                key = "begin.%d" % player_id


                # Faux lock
                universe.lock_with_key(
                    key = key,
                    timeout = 120,
                    strength = LOCK_NONE,
                    f_on_timeout = None
                )


                # Mail player
                self.mail(
                    conn,
                    self.build_message_by_command_type(
                        command_type = NET_MSG_BEGIN_GAME,
                        universe = universe,
                        actor = None,
                        params = {
                            "key": key
                        }
                    )
                )

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            pass


    # Server - Send level complete notice to all clients
    # Client - n/a
    def send_level_complete_with_next_map_name(self, next_map_name, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            # Now inform all clients that the level is complete
            for conn in self.get_active_connections():

                # Query player id
                player_id = self.get_player_id_by_connection(conn)

                # Calculate a key
                key = "level-complete.%d" % player_id


                # Faux lock
                universe.lock_with_key(
                    key = key,
                    timeout = 120,
                    strength = LOCK_NONE,
                    f_on_timeout = None
                )


                # Mail player
                self.mail(
                    conn,
                    self.build_message_by_command_type(
                        command_type = NET_MSG_LEVEL_COMPLETE,
                        universe = universe,
                        actor = None,
                        params = {
                            "key": key,
                            "next-map-name": next_map_name
                        }
                    )
                )

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            pass


    # Server - Send level failed notice to all clients
    # Client - n/a
    def send_level_failed_with_next_map_name(self, next_map_name, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            # Now inform all clients that the level is complete
            for conn in self.get_active_connections():

                # Query player id
                player_id = self.get_player_id_by_connection(conn)

                # Calculate a key
                key = "level-failed.%d" % player_id


                # Faux lock
                universe.lock_with_key(
                    key = key,
                    timeout = 120,
                    strength = LOCK_NONE,
                    f_on_timeout = None
                )


                # Mail player
                self.mail(
                    conn,
                    self.build_message_by_command_type(
                        command_type = NET_MSG_LEVEL_FAILED,
                        universe = universe,
                        actor = None,
                        params = {
                            "key": key,
                            "next-map-name": next_map_name
                        }
                    )
                )

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            pass


    # Server - Command clients to transition to a given map name
    # Client - n/a
    def send_transition_to_map(self, name, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            # Send to each connected player
            for conn in self.get_active_connections():

                # Query player id
                player_id = self.get_player_id_by_connection(conn)

                # Calculate a key
                key = "transition.%d" % player_id


                # Faux lock
                universe.lock_with_key(
                    key = key,
                    timeout = 120,
                    strength = LOCK_NONE,
                    f_on_timeout = None
                )


                # Mail player
                self.mail(
                    conn,
                    self.build_message_by_command_type(
                        command_type = NET_MSG_TRANSITION_TO_MAP,
                        universe = universe,
                        actor = None,
                        params = {
                            "key": key,
                            "map": name
                        }
                    )
                )

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            pass


    # Server - n/a (server controls scripts locally)
    # Client - Send server a request to run a script
    def send_script_request(self, script, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            pass

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # Calculate key
            key = "req-script"


            """
            # Full universe lock, pending approval / rejection
            universe.lock_with_key(
                key = key,
                timeout = 120,
                strength = LOCK_HARD
            )
            """


            # Ask server to run script
            self.send_registered_message(
                None,
                self.build_message_by_command_type(
                    command_type = NET_REQ_CALL_SCRIPT,
                    universe = universe,
                    actor = None,
                    params = {
                        "key": xml_encode( key ),
                        "script": xml_encode( script )
                    }
                ),
                {
                    "timeout": 2.0,
                    "retries": 1,
                    "net-lock-type": NET_LOCK_GLOBAL
                }
            )


    # Server - Command each client to run a given script
    # Client - n/a
    def send_call_script(self, script, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            # Present level
            m = universe.get_active_map()

            # Save map status so we can sync each client
            xml = m.save_state().compile_xml_string()


            # Send to each connected player
            for conn in self.get_active_connections():

                # Query player id
                player_id = self.get_player_id_by_connection(conn)

                # Calculate a key
                key = "call-script.%d" % player_id


                """
                # Lock the server until it receives a confirmation from each and every client
                universe.lock_with_key(
                    key = key,
                    timeout = 120,
                    strength = LOCK_HARD,
                    f_on_unlock = lambda a = script, b = m, c = control_center, u = universe: b.run_script(a, c, u)
                )
                """


                # Mail player
                self.send_registered_message(
                    conn,
                    self.build_message_by_command_type(
                        command_type = NET_MSG_CALL_SCRIPT,
                        universe = universe,
                        actor = None,
                        params = {
                            "key": xml_encode( key ),
                            "map-state": xml,
                            "script": xml_encode( script )
                        }
                    ),
                    {
                        "timeout": 2.0,
                        "retries": 1,
                        "net-lock-type": NET_LOCK_GLOBAL
                    }
                )

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            pass


    # Server - Send sync data for all players to each client
    # Client - n/a
    def send_sync_all_players(self, control_center, universe):

        # All active connections
        for conn in self.get_active_connections():

            # Query player id
            player_id = self.get_player_id_by_connection(conn)

            # Calculate key
            key = "sync-all.%d" % player_id


            # Configure an XML string holding each player's data...
            xml = "<players>"

            for i in range(1, 5):

                params = (
                    i,
                    xml_encode( universe.get_session_variable("net.player%d.nick" % i).get_value() ),
                    xml_encode( universe.get_session_variable("net.player%d.joined" % i).get_value() ),
                    xml_encode( universe.get_session_variable("net.player%d.ready" % i).get_value() ),
                    xml_encode( universe.get_session_variable("net.player%d.avatar.colors" % i).get_value() )
                )

                xml += "<player id = '%d' nick = '%s' joined = '%s' ready = '%s' avatar-data = '%s' />" % params

            xml += "</players>"


            # Faux lock
            universe.lock_with_key(
                key = key,
                timeout = 120,
                strength = LOCK_NONE,
                f_on_timeout = None
            )


            # Send sync data
            self.mail(
                conn,
                self.build_message_by_command_type(
                    command_type = NET_MSG_SYNC_ALL_PLAYERS,
                    universe = universe,
                    actor = None,
                    params = {
                        "key": key,
                        "xml": xml
                    }
                )
            )


    # Server - A given entity moves in a given direction.
    # Client - SAME
    def send_entity_start_motion(self, entity, direction, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            # Send to all connected ids
            for conn in self.get_active_connections():

                self.mail(
                    conn,
                    self.build_message_by_command_type(
                        command_type = NET_MSG_ENTITY_START_MOTION,
                        universe = universe,
                        actor = entity,
                        params = {
                            "direction": direction
                        }
                    )
                )

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # Send to server
            self.send_to_server(
                self.build_message_by_command_type(
                    command_type = NET_MSG_ENTITY_START_MOTION,
                    universe = universe,
                    actor = entity,
                    params = {
                        "direction": direction
                    }
                )
            )


    # Server - A given entity stops moving
    # Client - SAME
    def send_entity_stop_motion(self, entity, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            # Send to all connected players
            for conn in self.get_active_connections():

                self.mail(
                    conn,
                    self.build_message_by_command_type(
                        command_type = NET_MSG_ENTITY_STOP_MOTION,
                        universe = universe,
                        actor = entity,
                        params = {}
                    )
                )

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # Send to server
            self.send_to_server(
                self.build_message_by_command_type(
                    command_type = NET_MSG_ENTITY_STOP_MOTION,
                    universe = universe,
                    actor = entity,
                    params = {}
                )
            )

    # A given entity digs in a given direction
    def send_entity_dig(self, entity, direction, tx, ty, control_center, universe):

        # Send to all players
        for conn in self.get_active_connections():

            self.mail(
                conn,
                self.build_message_by_command_type(
                    command_type = NET_MSG_ENTITY_DIG,
                    universe = universe,
                    actor = entity,
                    params = {
                        "perfect-x": entity.get_x(),
                        "tx": tx,
                        "ty": ty,
                        "direction": direction
                    }
                )
            )


    # Server - n/a (server digs locally)
    # Client - A given entity requests permission to dig in a given direction
    def send_entity_dig_validation_request_with_key(self, key, entity, direction, tx, ty, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER):

            pass

        elif ( self.get_status() == NET_STATUS_CLIENT):

            # Send to server
            self.send_to_server(
                self.build_message_by_command_type(
                    command_type = NET_REQ_CONFIRM_DIG_TILE,
                    universe = universe,
                    actor = entity,
                    params = {
                        "key": key,
                        "perfect-x": entity.get_x(),
                        "tx": tx,
                        "ty": ty,
                        "direction": direction
                    }
                )
            )


    # Server - Send notice to clients that a given entity has died
    # Client - Send message to server informing of death
    def send_entity_die(self, entity, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            # Message all active connections
            for conn in self.get_active_connections():

                # Query player id
                player_id = self.get_player_id_by_connection(conn)

                # Calculate key
                key = "kill-entity.%s.%d" % (entity.name, player_id)


                # Faux lock
                universe.lock_with_key(
                    key = key,
                    timeout = 120,
                    strength = LOCK_NONE,
                    f_on_timeout = None
                )


                # Mail player
                self.mail(
                    conn,
                    self.build_message_by_command_type(
                        command_type = NET_MSG_ENTITY_DIE,
                        universe = universe,
                        actor = entity,
                        params = {
                            "key": key
                        }
                    )
                )

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # Lock key
            key = "local-player.die"

            # Faux lock
            universe.lock_with_key(
                key = key,
                timeout = 120,
                strength = LOCK_NONE,
                f_on_timeout = None
            )

            # Tell server
            self.send_to_server(
                self.build_message_by_command_type(
                    command_type = NET_MSG_ENTITY_DIE,
                    universe = universe,
                    actor = entity,
                    params = {
                        "key": key
                    }
                )
            )


    # Server - Command clients to respawn a given entity at another given entity (i.e. respawn location entity)
    # Client - n/a
    def send_respawn_entity_at_entity(self, entity, respawn_entity, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            # Mail all active connections
            for conn in self.get_active_connections():

                # Query player id
                player_id = self.get_player_id_by_connection(conn)

                # Calculate a key
                key = "respawn-entity.%s.%d" % (entity.name, player_id)


                # Faux lock
                universe.lock_with_key(
                    key = key,
                    timeout = 120,
                    strength = LOCK_NONE,
                    f_on_timeout = None
                )


                # Mail message
                self.mail(
                    conn,
                    self.build_message_by_command_type(
                        command_type = NET_MSG_ENTITY_RESPAWN,
                        universe = universe,
                        actor = entity,
                        params = {
                            "key": key,
                            "respawn.id": respawn_entity.name
                        }
                    )
                )

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            pass


    # Server - n/a (server bombs are local and live)
    # Client - Validate the ability to place a bomb at a given location
    def send_bomb_validation_request_with_key(self, key, bomb, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            pass

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            self.send_to_server(
                self.build_message_by_command_type(
                    command_type = NET_REQ_VALIDATE_BOMB,
                    universe = universe,
                    actor = bomb,
                    params = {
                        "key": xml_encode( key )
                    }
                )
            )


    # Server - Inform a client that the bomb request is approved
    # Client - n/a
    def send_bomb_success_by_name_and_connection_with_key(self, key, name, conn, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            self.mail(
                conn,
                self.build_message_by_command_type(
                    NET_MSG_VALIDATE_BOMB_OK,
                    universe = universe,
                    actor = None,
                    params = {
                        "key": xml_encode( key ),
                        "name": xml_encode( name )
                    }
                )
            )

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            pass


    # Server - Inform a client that the bomb request is denied
    # Client - n/a
    def send_bomb_failure_by_name_and_connection_with_key(self, key, name, conn, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            self.mail(
                conn,
                self.build_message_by_command_type(
                    NET_MSG_VALIDATE_BOMB_UNAUTHORIZED,
                    universe = universe,
                    actor = None,
                    params = {
                        "key": xml_encode( key ),
                        "name": xml_encode( name )
                    }
                )
            )

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            pass


    # Server - Send a notice to all clients that they should create a bomb
    # Client - n/a
    def send_create_bomb(self, bomb, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            # Mail all active connections
            for conn in self.get_active_connections():

                # Query player id
                player_id = self.get_player_id_by_connection(conn)

                # Calculate a key
                key = "create-bomb.%s.%d" % (bomb.name, player_id)


                # Faux lock
                universe.lock_with_key(
                    key = key,
                    timeout = 120,
                    strength = LOCK_NONE,
                    f_on_timeout = None
                )


                # Mail player
                self.mail(
                    conn,
                    self.build_message_by_command_type(
                        NET_MSG_CREATE_BOMB,
                        universe = universe,
                        actor = bomb,
                        params = {
                            "key": xml_encode( key )
                        }
                    )
                )

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            pass


    # Server - Sync the state of a given piece of gold to all players
    # Client - n/a
    def send_sync_one_gold(self, gold, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            # Message each active connection
            for conn in self.get_active_connections():

                # Query player id
                player_id = self.get_player_id_by_connection(conn)

                # Create key
                key = "%d.%d" % ( int( time.time() ), player_id )


                """
                # We need a receipt from each player
                universe.lock_with_key(
                    key = key,
                    timeout = 120,
                    strength = LOCK_NONE, # Faux lock
                    f_on_timeout = None
                )
                """


                # Mail player
                self.send_registered_message(
                    conn,
                    self.build_message_by_command_type(
                        command_type = NET_MSG_SYNC_ONE_GOLD,
                        universe = universe,
                        actor = gold,
                        params = {}
                    ),
                    {
                        "timeout": 5.0,
                        "retries": 1,
                        "net-lock-type": NET_LOCK_NONE
                    }
                )

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            pass


    # Server - sync all enemy AI to all clients
    # Client - n/a
    def send_sync_enemy_ai(self, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):
            logn( "netplay ai", "Syncing enemy AI (%s)\n" % time.time() )

            # Fetch active map
            m = universe.get_active_map()

            # Serialize AI into XML
            xml = "<enemies>"

            for e in m.master_plane.entities[GENUS_ENEMY]:

                #xml += e.compile_memory_string_with_ai_state(m)
                xml += e.save_ai_state(compress = True).compile_xml_string(pretty = False)

            xml += "</enemies>"


            # Message to all active players
            for conn in self.get_active_connections():

                # Mail player
                self.mail(
                    conn,
                    self.build_message_by_command_type(
                        command_type = NET_MSG_SYNC_ENEMY_AI,
                        universe = universe,
                        actor = None,
                        params = {
                            "xml": xml
                        }
                    )
                )

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            pass


    # Server - send local player coordinates to all clients
    # Client - send local player coordinates to server (for distribution to any other client)
    def send_sync_player_by_id(self, player_id, control_center, universe):

        # Get player object
        player = universe.get_active_map().get_entity_by_name("player%d" % player_id)

        # Validate player object
        if (player):

            # Both server and client will send the same message;
            # let's build it first.
            xml = "<player id = '%d' x = '%d' y = '%d' direction = '%d' />" % (
                #int( universe.get_session_variable("core.player-id").get_value() ),
                player_id,
                player.get_x(),
                player.get_y(),
                player.get_direction()
            )


            # Server will send to all clients
            if ( self.get_status() == NET_STATUS_SERVER ):

                # Message to all active players
                for conn in self.get_active_connections():

                    # Mail player
                    self.mail(
                        conn,
                        self.build_message_by_command_type(
                            command_type = NET_MSG_SYNC_PLAYER_BY_ID,
                            universe = universe,
                            actor = None,
                            params = {
                                "xml": xml
                            }
                        )
                    )


            # Clients will send only to server
            elif ( self.get_status() == NET_STATUS_CLIENT ):

                self.send_to_server(
                    self.build_message_by_command_type(
                        command_type = NET_MSG_SYNC_PLAYER_BY_ID,
                        universe = universe,
                        actor = None,
                        params = {
                            "xml": xml
                        }
                    )
                )


# The network controller will also inherit these functions.  These
# functions react to incoming messages.  Every function takes
# the same parameters (data, source, control center, and universe).
class NetworkControllerRecvFunctionsExt:

    def __init__(self):

        return


    # Server - (not coded)
    # Client - Responsd to server's ping request
    def recv_ping(self, data, source, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):
            pass

        # Server sends back a pong with the received timestamp
        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # "Parse" data into server's original timestamp (one param message)
            timestamp = data

            # Send a pong
            self.send_pong(timestamp, control_center, universe)


    # Server - Receive pong from any client
    # Client - (not coded)
    def recv_pong(self, data, source, control_center, universe):

        # Server receives pong and checks time for travel
        if ( self.get_status() == NET_STATUS_SERVER ):

            # "Parse" data into the original timestamp (one param message)
            timestamp = data

            # Safety
            if (1):#try:

                # Calculate total travel time in milliseconds, rounded to 3 digits.
                ms = int( 1000 * ( time.time() - float(timestamp) ) )

                # Get the player id for this connection
                player_id = self.get_player_id_by_connection(source)

                # Do we need to create a new hash to track ping data for this player?
                if ( not self.get_ping_data_by_player_id(player_id) ):

                    # Init a new hash
                    self.set_ping_data_by_player_id(
                        player_id,
                        {
                            "sum": 0.0, # Sum of all ping times
                            "count": 0, # Number of ping responses received
                            "mean": 0.0 # Current mean
                        }
                    )


                # Get ping data hash
                ping_data = self.get_ping_data_by_player_id(player_id)


                # Increase sum
                ping_data["sum"] += ms

                # Increase count
                ping_data["count"] += 1

                # Recalculate mean
                ping_data["mean"] = int( ping_data["sum"] / ping_data["count"] )

            else:#except:
                pass


    # Server - n/a
    # Client - Receive notice that the server is going offline.  Send back receipt,
    #          then clean up sockets and return ot the main menu, giving a "lost connection"
    #          message to the player along the way.
    def recv_server_disconnecting(self, data, source, control_center, universe):

        # "Parse" data
        key = data


        if ( self.get_status() == NET_STATUS_SERVER ):

            pass

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # Send receipt immediately
            self.send_unlock_with_key(key, source, control_center, universe)

            # Confirm disconnect notice to the server
            self.send_confirm_disconnect_by_connection(source, control_center, universe)


            # (?) For now, let's just post a newsfeeder item alerting the player to the server disconnecting
            control_center.get_window_controller().get_newsfeeder().post({
                "type": NEWS_NET_PLAYER_DISCONNECTED,
                "title": control_center.get_localization_controller().get_label("server-quit:title"),
                "content": control_center.get_localization_controller().get_label("server-quit:message")
            })


            # Clean up the socket once these last messages have gone over the wire
            self.finish_connection()


            # (?) For now, we're just fading the app back to the main menu with no redirect / transition
            control_center.get_window_controller().fade_out(
                on_complete = "app:leave-game"
            )


    # Server - Receive notice that a given client is disconnecting.  Send that player a receipt,
    #          clean up the socket for that player, and then tell any other client that a player left.
    # Client - Receive notice from the server that some other player (not the local player, and not
    #          the server player) has left the game.
    def recv_client_disconnecting(self, data, source, control_center, universe):

        # Parse data
        (key, disconnecting_player_id) = data.split(";")

        # Cast disconnecting player id as an int
        disconnecting_player_id = int(disconnecting_player_id)


        if ( self.get_status() == NET_STATUS_SERVER ):

            # Send back receipt
            self.send_unlock_with_key(key, source, control_center, universe)

            # SEnd a "confirm disconnect" message
            self.send_confirm_disconnect_by_connection(source, control_center, universe)


            # Post a "so-and-so left the game" newsfeeder item while we're still holding on to net data for that slot
            control_center.get_window_controller().get_newsfeeder().post({
                "type": NEWS_NET_PLAYER_DISCONNECTED,
                "title": control_center.get_localization_controller().get_label("player-disconnected:title"),
                "content": universe.get_session_variable("net.player%d.nick" % disconnecting_player_id).get_value()
            })


            # Clear net data for the slot this player was using
            universe.clear_net_player_data_in_slot(disconnecting_player_id)

            # Clean up the socket once these last messages have gone over the wire
            self.finish_connection(
                self.get_connection_by_player_id(disconnecting_player_id)
            )


            # Use a main network controller function to update the active player count
            self.web_update_player_count(control_center, universe)


            # If we have any other player in the game, inform them that one of the clients just left...
            active_connections = self.get_active_connections()

            # More players left?
            if ( len(active_connections) > 0 ):

                # Mail each remaining player
                for conn in active_connections:

                    # Query player id
                    player_id = self.get_player_id_by_connection(conn)

                    # Calculate key to lock with
                    key = "client-disconnecting.%d.%d" % (disconnecting_player_id, player_id)


                    # Faux lock
                    universe.lock_with_key(
                        key = key,
                        timeout = 120,
                        strength = LOCK_NONE,
                        f_on_timeout = None
                    )


                    # Mail player
                    self.mail(
                        conn,
                        self.build_message_by_command_type(
                            command_type = NET_MSG_CLIENT_DISCONNECTING,
                            universe = universe,
                            actor = None,
                            params = {
                                "key": key,
                                "player-id": disconnecting_player_id
                            }
                        )
                    )

            # If no other player remains, the we should prompt the now-alone server player
            # to either return to the pregame lobby (to await more players) or to end the session...
            else:

                # Wait a minute, though.  If we're already in the pregame lobby, then there's no need to do anything
                # special.  We'll just stay in the pregame lobby, waiting for more players.
                if ( int( universe.get_session_variable("net.countdown-in-progress").get_value() ) == 1 ):

                    # Add a "now what do you want to do, now that no players are remaining?" menu
                    control_center.get_menu_controller().add(
                        control_center.get_widget_dispatcher().create_net_no_players_menu()
                    )



        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # The client shall return a receipt to the server here
            self.send_unlock_with_key(key, source, control_center, universe)

            # Post a "so-and-so left the game" newsfeeder item while we're still holding on to net data for that slot
            control_center.get_window_controller().get_newsfeeder().post({
                "type": NEWS_NET_PLAYER_DISCONNECTED,
                "title": control_center.get_localization_controller().get_label("player-disconnected:title"),
                "content": universe.get_session_variable("net.player%d.nick" % disconnecting_player_id).get_value()
            })


            # Clear net data for the slot this player was using
            universe.clear_net_player_data_in_slot(disconnecting_player_id)


    # Server - Receive confirmation from a client that it received the server's "game is ending" message.
    #          We should receive n number of these, one for each client that joined the game.
    # Client - Receive a note from the server indicating that it received our "client is quitting" message
    #          and is cleaning up the connection as needed.
    def recv_confirm_disconnect(self, data, source, control_center, universe):

        # No data to consider...
        #pass

        if ( self.get_status() == NET_STATUS_SERVER ):

            # If we are out of active connections, then we've closed all client connections
            # and we can drop into offline mode.
            if ( len( self.get_active_connections() ) == 0 ):

                # Mark as offline
                self.set_status(NET_STATUS_OFFLINE)


        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # Disconnect from the server; clean up the socket.
            #self.disconnect()

            #control_center.get_window_controller().fade_out(
            #    on_complete = "fwd.return-to-menu.commit"
            #)

            # Mark network controller as offline now
            self.set_status(NET_STATUS_OFFLINE)


    # Server - Receive unlock notice
    # Client - Receive unlock notice
    def recv_unlock(self, data, source, control_center, universe):

        # The only data is the key
        key = data

        # Unlock universe by key
        universe.unlock(key)
        log( "Unlocked key '%s'" % key )


    # Server - n/a (server controls its own player id of 1 locally)
    # Client - Receive player id after joining game
    def recv_player_id(self, data, source, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            pass

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            logn( "netcode", "Receiving player ID at %s\n" % time.time() )

            # Track player id
            universe.set_session_variable("core.player-id", "%d" % int(data))

            # Track ourself as joined
            universe.set_session_variable("net.player%d.joined" % int(data), "1")

            # Track that we did in fact receive a player id
            universe.set_session_variable("core.received-player-id", "1")


            # Now that the client knows their player id, we should load in any previous netplay settings (nick, avatar, etc.?).
            # (The loading function can now assign the data to the now-known player id / slot.)
            control_center.load_netplay_preferences(universe)


            # Get the player object this client will control
            player = universe.get_active_map().get_entity_by_name(
                "player%s" % universe.get_session_variable("core.player-id").get_value()
            )

            # Validate
            if (player):

                # Place that entity at the "end" of the list of players so that it renders on top at all times
                universe.get_active_map().spotlight_entity_by_type(player, GENUS_PLAYER)


            # Unlock the universe by key
            universe.unlock("test.key1")


    # Server - n/a
    # Client - Receive a request for nick data
    def recv_req_nick(self, data, source, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            pass

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # Get player id from data (the only piece of data)
            player_id = int(data)

            # Track player id.  We probably already did this in recv_player_id, but let's just make sure.
            universe.set_session_variable("core.player-id", "%d" % int(data))


            # Load in previous netplay preferences to the local player slot
            control_center.load_netplay_preferences(universe)


            # Set up a key
            key = "resp-nick"

            # Faux lock
            universe.lock_with_key(
                key = key,
                timeout = 120,
                strength = LOCK_NONE,
                f_on_timeout = None
            )


            # Reply to the request
            self.mail(
                source,
                self.build_message_by_command_type(
                    command_type = NET_MSG_SYNC_PLAYER,
                    universe = universe,
                    actor = None,
                    params = {
                        "key": key,
                        "player-id": player_id,
                        "online-status": "online",
                        "ready-status": universe.get_session_variable("net.player%d.ready" % player_id).get_value(),
                        "nick": universe.get_session_variable("net.player%d.nick" % player_id).get_value(),
                        "avatar-data": universe.get_session_variable("net.player%d.avatar.colors" % player_id).get_value()
                    }
                )
            )


    # Server - Receive a player's avatar data.
    #          Forward to other players.
    # Client - Receive only.
    def recv_avatar_data(self, data, source, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            # player id and semicolon-separated values (the color data)
            (player_id, ssv) = data.split(";", 1)

            # int
            player_id = int( player_id )


            # Update the data in the current session
            universe.set_session_variable("net.player%d.avatar.colors" % player_id, ssv)

            # Also flag the coop intro menu to refresh (so that we can update the profile cards using the new color data)
            universe.set_session_variable("net.rebuild-intro-menu", "1")


            """ Forwarding """
            # Ignore the player who sent this... they already know their data
            self.ignore(source)

            # Send this avatar data along
            self.send_avatar_data(data, control_center, universe)

            # Stop ignoring the source
            self.attend(source)

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # player id and semicolon-separated values (the color data)
            (player_id, ssv) = data.split(";", 1)

            # int
            player_id = int( player_id )


            # Update the data in the current session
            universe.set_session_variable("net.player%d.avatar.colors" % player_id, ssv)

            # Also flag the coop intro menu to refresh (so that we can update the profile cards using the new color data)
            universe.set_session_variable("net.rebuild-intro-menu", "1")


    # Server - Receive and tally vote.
    #          Forward to other players so they can tally.
    # Client - Tally vote.
    def recv_vote_to_skip(self, data, source, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            # Parcel data
            key = data

            # Increment total skip votes counter
            universe.increment_session_variable("net.votes-to-skip", 1)

            # Flag to rebuild lobby menu (to reflect new vote skip total)
            universe.set_session_variable("net.rebuild-intro-menu", "1")


            # Confirm receipt
            self.send_unlock_with_key(key, source, control_center, universe)


            """ Forwarding """
            # Send this message to every player; even the client who submitted this vote
            # won't see their tally increase until we confirm it.
            self.send_vote_to_skip(control_center, universe)

        # Client simply sends confirmation back to the server
        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # Reply key
            key = data


            # Increment total skip votes counter
            universe.increment_session_variable("net.votes-to-skip", 1)

            # Flag to rebuild lobby menu (to reflect new vote skip total)
            universe.set_session_variable("net.rebuild-intro-menu", "1")


            # Confirm receipt
            self.send_unlock_with_key(key, source, control_center, universe)


    # Server - n/a
    # Client - Flag game as underway, confirm receipt to server
    def recv_begin_game(self, data, source, control_center, universe):

        # Server controls its local game; server has all authority.
        if ( self.get_status() == NET_STATUS_SERVER ):

            pass


        # Client cannot begin a game until the server tells it to.
        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # Flag the game as being in progress now.  The client's net lobby menu
            # will monitor this flag, hiding itself and dismissing the splash controller.
            universe.set_session_variable("net.game-in-progress", "1")


            # Final setup for coloring characters, showing/hiding characters, etc.
            universe.prepare_multiplayer_session()


            # Run universe's coop ready script
            universe.run_script("global.coop.ready", control_center, execute_all = True)

            # Run the map's coop.ready script
            universe.get_active_map().run_script("coop.ready", control_center, universe, execute_all = True)


            # Reply key.  That's all the data there is in this message.
            key = data

            # Reply with confirmation
            self.send_unlock_with_key(key, source, control_center, universe)


    """
    # Server - n/a (server controls map locally)
    # Client - Receive map sync data (entire map) as an XML string
    def recv_sync_map(self, data, source, control_center, universe):

        xml = data

        m = universe.get_active_map()

        m.load_memory_from_xml(xml)

        log( "Syncing map / everything..." )
    """


    # Server - Receive player data for a given client.
    #          Forward to all other players
    # Client - Receive player data for a given client, but do not forward.
    def recv_sync_player(self, data, source, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            # Parcel data
            (key, player_id, online_status, ready_status, nick, avatar_data) = data.split(";", 5)

            # Cast player id to int
            player_id = int( player_id )

            # Conversion
            online_status = "%d" % ( online_status == "online" )


            # Use the universe session to track data for this client
            universe.set_session_variable("net.player%d.nick" % player_id, nick)
            universe.set_session_variable("net.player%d.joined" % player_id, online_status)
            universe.set_session_variable("net.player%d.ready" % player_id, ready_status)

            # Avatar data goes in session as well
            universe.set_session_variable("net.player%d.avatar.colors" % player_id, avatar_data)


            # If we haven't received a nick for this player yet, then post a note that the player has joined
            if ( int( universe.get_session_variable("net.player%d.received-nick" % player_id).get_value() ) == 0 ):

                # Flag as nick received
                universe.set_session_variable("net.player%d.received-nick" % player_id, "1")

                # Post note
                control_center.get_window_controller().get_newsfeeder().post({
                    "type": NEWS_NET_PLAYER_CONNECTED,
                    "title": control_center.get_localization_controller().get_label("player-joined:title"),
                    "content": "%s" % nick
                })

                # (already done in socket server accept logic) Sync this one new player, send them info on all current lobby / game members
                #self.send_sync_new_player_by_connection(source, control_center, universe)


            # We need to rebuild the lobby to reflect potential changes
            universe.set_session_variable("net.rebuild-intro-menu", "1")


            # Receipt
            self.send_unlock_with_key(key, source, control_center, universe)


            """ Forwarding """
            # Let's go ahead and forward this data to all players except for the source.
            # Remember that we synced the source just above.
            self.ignore(source)

            # Sync the remaining clients
            self.send_sync_all_players(control_center, universe)

            # Stop ignoring the source
            self.attend(source)


        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # Parcel data
            (key, player_id, online_status, ready_status, nick, avatar_data) = data.split(";", 5)

            # Cast player id to int
            player_id = int( player_id )

            # Conversion
            online_status = "%d" % ( online_status == "online" )


            # Use the universe session to track data for this client
            universe.set_session_variable("net.player%d.nick" % player_id, nick)
            universe.set_session_variable("net.player%d.joined" % player_id, online_status)
            universe.set_session_variable("net.player%d.ready" % player_id, ready_status)

            # Avatar data goes in session as well
            universe.set_session_variable("net.player%d.avatar.colors" % player_id, avatar_data)


            # If we haven't received a nick for this player yet, then post a note that the player has joined
            if ( int( universe.get_session_variable("net.player%d.received-nick" % player_id).get_value() ) == 0 ):

                # Flag as nick received
                universe.set_session_variable("net.player%d.received-nick" % player_id, "1")

                # Post note
                control_center.get_window_controller().get_newsfeeder().post({
                    "type": NEWS_NET_PLAYER_CONNECTED,
                    "title": control_center.get_localization_controller().get_label("player-joined:title"),
                    "content": "%s" % nick
                })

                # (already done in socket server accept logic) Sync this one new player, send them info on all current lobby / game members
                #self.send_sync_new_player_by_connection(source, control_center, universe)


            # We need to rebuild the lobby to reflect potential changes
            universe.set_session_variable("net.rebuild-intro-menu", "1")


            # Receipt
            self.send_unlock_with_key(key, source, control_center, universe)


    # Server - n/a (server controls player data locally)
    # Client - Receive sync data for all players in the game (even the current local player)
    def recv_sync_all_players(self, data, source, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            pass

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # Parse data
            (key, xml) = data.split(";", 1)

            log( "xml = '%s'" % xml )

            # Compile XML
            root = XMLParser().create_node_from_xml(xml)

            # Validate
            if (root):

                # Find active map node
                ref_active_map = root.find_node_by_tag("active-map")

                # Validate
                if (ref_active_map):

                    # Activate the given map
                    m = universe.activate_map_on_layer_by_name(
                        ref_active_map.innerText,
                        layer = LAYER_FOREGROUND,
                        game_mode = MODE_GAME,
                        control_center = control_center,
                        ignore_adjacent_maps = True # Cooperative maps always ignore adjacent maps
                    )

                    # Validate that we activated a map
                    if (m):

                        # Center the camera on the selected map
                        m.center_camera_on_entity_by_name( universe.get_camera(), "player1", zap = True )


                # Find player data node
                ref_players = root.find_node_by_tag("players")

                # Validate
                if (ref_players):

                    # Loop all players
                    player_collection = ref_players.get_nodes_by_tag("player")

                    # Is this data for a brand new player?
                    new_client_data = False

                    # Check and see
                    if ( ref_players.get_attribute("new-client") ):

                        # Read attribute
                        new_client_data = ( int( ref_players.get_attribute("new-client") ) == 1 )


                    # Loop
                    for ref_player in player_collection:

                        # Parse data
                        (player_id, nick, joined, ready, avatar_data) = (
                            int( ref_player.get_attribute("id") ),
                            xml_decode( ref_player.get_attribute("nick") ),
                            xml_decode( ref_player.get_attribute("joined") ),
                            xml_decode( ref_player.get_attribute("ready") ),
                            xml_decode( ref_player.get_attribute("avatar-data") ),
                        )

                        # Update universe session data
                        universe.set_session_variable("net.player%d.nick" % player_id, nick)
                        universe.set_session_variable("net.player%d.joined" % player_id, joined)
                        universe.set_session_variable("net.player%d.ready" % player_id, ready)
                        universe.set_session_variable("net.player%d.avatar.colors" % player_id, avatar_data)

                        # If we haven't received a nick for this player, then they must be new to the game since we joined.
                        if ( int( universe.get_session_variable("net.player%d.received-nick" % player_id).get_value() ) == 0 ):

                            # Flag as having received the nick
                            universe.set_session_variable("net.player%d.received-nick" % player_id, "1")

                            # Post a newsfeeder item announcing the new player, unless this is data
                            # being sent to a newly joining player.
                            if (not new_client_data):

                                control_center.get_window_controller().get_newsfeeder().post({
                                    "type": NEWS_NET_PLAYER_CONNECTED,
                                    "title": control_center.get_localization_controller().get_label("player-joined:title"),
                                    "content": "%s" % nick
                                })


                    # If this is data for a new player, we'll give them a special welcome message
                    if (new_client_data):

                        # count how many other players are in the game
                        other_players_count = -1 + sum( int( universe.get_session_variable("net.player%d.joined" % i).get_value() ) == 1 for i in range( 1, (1 + int( universe.get_session_variable("net.player-limit").get_value() )) ) )

                        # Post a news item
                        control_center.get_window_controller().get_newsfeeder().post({
                            "type": NEWS_NET_CLIENT_ONLINE,
                            "title": control_center.get_localization_controller().get_label("joined-session:title"),
                            "content": control_center.get_localization_controller().get_label( "joined-session:message", { "@n": "%s" % other_players_count, "@s": "s" if (other_players_count != 1) else "" } )
                        })


                # Flag that this client should update the lobby UI, if it's visible
                universe.set_session_variable("net.rebuild-intro-menu", "1")


    # Server - Receive a client's request to run a script (flip a lever, etc.)
    #          If approved, send a "call script" command to every client (and run locally).
    # Client - n/a
    def recv_script_request(self, data, source, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            # Parse data
            (key, script) = data.split(";")


            # Validate that the universe is not already busy
            if ( not universe.is_locked() ):

                log( "Call script request:  Approved" )

                # Run the script locally
                universe.get_active_map().run_script(script, control_center, universe)

                # Instruct all clients to run the given script
                self.send_call_script(script, control_center, universe)

            else:

                log( "Call script request:  Rejected" )


            # Irregardless, always send an unlock receipt
            #self.send_unlock_with_key(key, source, control_center, universe)

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            pass


    # Server - n/a (server controls script execution locally)
    # Client - Receive notice that we should call a script.  Command includes
    #          map sync data.
    def recv_call_script(self, data, source, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            pass

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            #return

            # All is XML
            xml = data

            # Compile XML
            root = XMLParser().create_node_from_xml(xml)

            # Get wrapper
            ref_packet = root.get_first_node_by_tag("packet")

            # Get command data references
            (ref_key, ref_script, ref_map_state) = (
                ref_packet.get_first_node_by_tag("key"),
                ref_packet.get_first_node_by_tag("script"),
                ref_packet.get_first_node_by_tag("map-state")
            )


            # Grab active map
            m = universe.get_active_map()

            # Sync map state before running the script
            #m.load_memory_from_xml( ref_map_state.compile_inner_xml_string() )
            m.load_state(ref_map_state)#.compile_inner_xml_string() )

            log( "Syncing map / everything, preparing to call script..." )
            log( "Call script:  '%s'" % ref_script.innerText )

            # Execute the script
            m.run_script(ref_script.innerText, control_center, universe)


            # Receipt
            #self.send_unlock_with_key(ref_key.innerText, source, control_center, universe)


    # Server - Receive notice that an entity has started moving.
    #          Forward message to other connected players.
    # Client - Receive notice and process.
    def recv_entity_start_motion(self, data, source, control_center, universe):

        # Grab current map
        m = universe.get_active_map()

        # Parse data
        (entity_id, x, y, direction) = data.split(";")

        # Case direction as an int
        direction = int(direction)


        # Fetch entity
        entity = m.get_entity_by_name(entity_id)

        # Validate
        if (entity):

            # Send a motion message to the entity
            entity.handle_message("start-motion", None, "%s;%s;%s" % (x, y, direction), control_center, universe = universe)


            # (?)
            if ( len( m.query_interentity_collision_for_entity(entity).get_results() ) > 0 ):

                entity.set_sync_status(SYNC_STATUS_PENDING)

            else:

                entity.set_sync_status(SYNC_STATUS_READY)


            """ Server forwarding """
            # The server must forward to all OTHER players
            if ( self.get_status() == NET_STATUS_SERVER ):

                # Ignore the source of this message
                self.ignore(source)

                # Forward to all active connections
                self.send_entity_start_motion(entity, direction, control_center, universe)

                # Stop ignoring the source
                self.attend(source)


    # Server - Receive notice that an entity has stopped moving.
    #          Forward this notice to all other players.
    # Client - Receive notice, process.  No forwarding.
    def recv_entity_stop_motion(self, data, source, control_center, universe):

        # Fetch active map
        m = universe.get_active_map()

        # Parcel
        (entity_id, x, y) = data.split(";")


        # Grab entity
        entity = m.get_entity_by_name(entity_id)

        # Validate
        if (entity):

            # Send a stop motion message to the entity
            entity.handle_message("stop-motion", None, "%s;%s" % (x, y), control_center, universe = universe)#, p_map = m, session = self.session)


            #if ( m.check_interentity_collision(entity) ):
            # (?)
            if ( len( m.query_interentity_collision_for_entity(entity).get_results() ) > 0 ):

                entity.set_sync_status(SYNC_STATUS_PENDING)

            else:

                entity.set_sync_status(SYNC_STATUS_READY)


            """ Server forwarding """
            # The server should forward to all OTHER players
            if ( self.get_status() == NET_STATUS_SERVER ):

                # Ignore the source (they already know they stopped!)
                self.ignore(source)

                # Send stop motion command
                self.send_entity_stop_motion(entity, control_center, universe)

                # Stop ignoring source
                self.attend(source)


    # Server - Evaluate a client's request to dig a given tile.  If successful,
    #          send confirmation to source, then propogate dig to other players.
    # Client - n/a
    def recv_entity_dig_validation_request(self, data, source, control_center, universe):

        # Server
        if ( self.get_status() == NET_STATUS_SERVER ):

            # Grab the current map to dig on
            m = universe.get_active_map()


            # Separate ssv
            pieces = data.split(";")

            # Distribute
            (key, entity_id, x, y, direction, tx, ty) = (
                pieces[0],
                pieces[1],
                int( pieces[2] ),
                int( pieces[3] ),
                int( pieces[4] ),
                int( pieces[5] ),
                int( pieces[6] )
            )


            # Fetch the entity that wants to dig (which player?)
            entity = m.get_entity_by_name(entity_id)

            # Validate
            if (entity):

                # Position
                entity.set_x(x)
                entity.set_y(y)

                entity.direction = direction

                # Is it ok to put the client at that location?  Nothing in the way?
                #if ( m.master_plane.count_entities_in_rect( (x, y, self.width, self.height), exceptions = [entity] ) == 0 ):
                if (True):

                    # Try to dig
                    result = m.dig_tile_at_tile_coords(tx, ty)


                    # On success, we must send all OTHER clients a dig message.
                    if (result == DIG_RESULT_SUCCESS):

                        # Ignore the source while we broadcast to the other players
                        self.ignore(source)

                        # Send dig message
                        self.send_entity_dig(
                            entity = entity,
                            direction = direction,
                            tx = tx,
                            ty = ty,
                            control_center = control_center,
                            universe = universe
                        )

                        # Stop ignoring source
                        self.attend(source)


                    # If the dig is not valid, we must send a message back to the source letting them know it's not validated
                    else:

                        self.mail(
                            source,
                            self.build_message_by_command_type(
                                command_type = NET_MSG_INVALIDATE_DIG,
                                universe = universe,
                                actor = None,
                                params = {
                                    "tx": tx,
                                    "ty": ty
                                }
                            )
                        )

                # Whether or not we approved the dig, the client committed a local dig (which they might to have to undo, but still!),
                # and they stopped moving at that spot.  Let's emulate a "stop motion" event locally to keep sync locally.
                entity.handle_message("stop-motion", None, "%s;%s" % (x, y), control_center, universe = universe)#, p_map = m, session = self.session)

                # Now we're going to have to forward this stop motion event to any other connected client.
                # Note that we won't bother sending this to the player who tried to dig; they already stopped locally.
                self.ignore(source)

                # Send stop motion command
                self.send_entity_stop_motion(entity, control_center, universe)

                # Stop ignoring source
                self.attend(source)

            
            # Irregardless of anything else, always message back an unlock to the source (the player who sent the dig request)
            self.send_unlock_with_key(key, source, control_center, universe)


        # client does nothing here.  Should never receive this message.
        elif ( self.get_status() == NET_STATUS_CLIENT ):

            pass


    # Server - n/a
    # Client - Receive dig approval / confirmation from server
    def recv_entity_dig_success(self, data, source, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            pass

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # Parse.  Why do I have so much data in a confirmation?!
            (entity_id, x, y, direction, tx, ty, key) = data.split(";")

            #self.process_network_command( "%d;%s" % (NET_MSG_ENTITY_DIG, ";".join(pieces[1 : len(pieces) - 1])) )
            #self.process_network_command( "%d;%s" % (NET_MSG_ENTITY_DIG, data), control_center )#";".join(pieces[1 : len(pieces) - 1])) )


    # Server - n/a
    # Client - Receive dig rejection message; cancel the dig (fill the tile in).  The client may have encountered a sync issue or something.
    def recv_entity_dig_failure(self, data, source, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            pass

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            log2( "**Dig invalidated, let's clean this up!" )


    # Server - n/a (server only receives dig requests... server controls all digs locally)
    # Client - Receive notice that an entity has digged a tile
    def recv_entity_dig(self, data, source, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            pass

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # Get active level
            m = universe.get_active_map()

            # Bit by bit
            (entity_id, x, y, direction, tx, ty) = data.split(";")
            log( (entity_id, x, y, direction, tx, ty) )


            # Get digging entity
            entity = m.get_entity_by_name(entity_id)

            # Validate
            if (entity):

                # Send a "net dig" event to the entity
                entity.handle_message("net.dig", None, "%s;%s;%s;%s;%s;" % (x, y, direction, tx, ty), control_center, universe = universe)

                # ??
                #if ( m.check_interentity_collision(entity) ):
                # (?)
                if ( len( m.query_interentity_collision_for_entity(entity).get_results() ) > 0 ):

                    entity.set_sync_status(SYNC_STATUS_PENDING)

                else:

                    entity.set_sync_status(SYNC_STATUS_READY)


    # Server - Does not process message (server controls entity states locally),
    #          but DOES forward message to all OTHER clients.
    # Client - Receive notice that an entity has died
    def recv_entity_die(self, data, source, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            # Parse data
            (key, entity_id) = data.split(";")


            # Grab active map
            m = universe.get_active_map()


            # Fetch entity
            entity = m.get_entity_by_name(entity_id)

            # Validate
            if (entity):

                # Kill it
                entity.die(DEATH_BY_VAPORIZATION, control_center, universe, server_approved = True)

                """ Forwarding """
                # Ignore the source, source already knows they died
                self.ignore(source)

                # Send message
                self.send_entity_die(entity, control_center, universe)

                # Stop ignoring the source
                self.attend(source)


            # Receipt, irregardless of validation
            self.send_unlock_with_key(key, source, control_center, universe)

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # Current level
            m = universe.get_active_map()

            # Parse data
            (key, entity_id) = data.split(";")


            # Fetch entity
            entity = m.get_entity_by_name(entity_id)

            # Validate
            if (entity):

                # Entity officially dies, has final server approval
                entity.die(DEATH_BY_VAPORIZATION, control_center, universe = universe, server_approved = True)


            # Receipt
            self.send_unlock_with_key(key, source, control_center, universe)


    # Server - n/a (controls entity spawns locally)
    # Client - Receive notice that an entity should respawn
    def recv_entity_respawn(self, data, source, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            pass

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # Get map
            m = universe.get_active_map()

            # Distribute
            (key, entity_id, respawn_id) = data.split(";")


            # Fetch entity
            entity = m.get_entity_by_name(entity_id)

            # Validate
            if (entity):

                # Where are we respawning the entity?
                respawn_entity = m.get_entity_by_name(respawn_id)

                # Validate respawn marker
                if (respawn_entity):

                    # Respawn entity
                    entity.respawn_at_entity(respawn_entity, control_center, universe)


            # Receipt
            self.send_unlock_with_key(key, source, control_center, universe)


    # Server - Receive a bomb validation request from a client.
    #          If authorized, forward bomb create command to all other players.
    # Client - n/a
    def recv_bomb_validation_request(self, data, source, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            # Current map
            m = universe.get_active_map()

            # Data
            pieces = data.split(";")

            # Parcel
            (key, entity_id, x, y, radius, remote) = (
                pieces[0],
                pieces[1],
                int( pieces[2] ),
                int( pieces[3] ),
                int( pieces[4] ),
                ( int( pieces[5] ) == 1)
            )

            # Convert raw coordinates to tile coordinates
            (tx, ty) = (
                int( x / TILE_WIDTH ),
                int( y / TILE_HEIGHT )
            )

            log2( "bomb requested at:  ", (tx, ty) )

            # Validate that we can place a bomb at that location
            if ( (m.master_plane.check_collision(tx, ty) in (COLLISION_NONE, COLLISION_LADDER, COLLISION_MONKEYBAR)) ):

                # The server begins by creating a local version of the bomb at the given location
                bomb = m.create_bomb_with_unique_id(x = (tx * TILE_WIDTH), y = (ty * TILE_HEIGHT))

                # Update radius
                bomb.set_radius(radius)

                # Remote bomb?  (Never in multiplayer?)
                if (remote):

                    # Tag it and track it!
                    self.tag_bomb_as_remote(bomb)


                # Validation to the source
                self.send_bomb_success_by_name_and_connection_with_key(key, entity_id, source, control_center, universe)


                """ Forwarding """
                # Ignore the source; we just need to validate their bomb
                self.ignore(source)

                # Send create bomb to all active connections
                self.send_create_bomb(bomb, control_center, universe)

                # Stop ignoring the source
                self.attend(source)




                log( "Bomb placement:  OK" )

            # We can't place a bomb there
            else:

                # Define a key for the rejection
                key = "reject-bomb.%s.%d" % (entity_id, network_controller.get_player_id_by_connection( command.get_source() ))

                # Create a faux lock
                universe.lock_with_key(
                    key = key,
                    timeout = 120,
                    strength = LOCK_NONE,
                    f_on_timeout = None
                )

                self.mail(
                    command.get_source(),
                    self.build_message_by_command_type(
                        NET_MSG_VALIDATE_BOMB_UNAUTHORIZED,
                        universe = universe,
                        actor = None,
                        params = {
                            "key": xml_encode( key ),               # The key we'll require back from the client, receipt
                            "name": xml_encode( entity_id )      # The entity id of the bomb we're denying so the client can remove it...
                        }
                    )
                )

                log( "Bomb placement:  Unauthorized" )

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            pass


    # Server - n/a (server doesn't have to authorize bombs)
    # Client - Receive confirmation that a bomb is valid
    def recv_bomb_success(self, data, source, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            pass

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # Active map
            m = universe.get_active_map()

            # Parse data
            (key, entity_id) = data.split(";")


            # Find bomb
            entity = m.get_entity_by_name(entity_id)

            # Validate
            if (entity):

                # Bomb is approved and should detonate on schedule
                entity.unlock()


            # Unlock universe with key
            universe.unlock(key)


    # Server - n/a (server doesn't have to authorize bombs)
    # Client - Receive notice that a bomb is not approved
    def recv_bomb_failure(self, data, source, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            pass

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # Present map
            m = universe.get_active_map()

            # Fetch data
            (key, entity_id) = data.split(";")


            # Find bomb
            entity = m.get_entity_by_name(entity_id)

            # Validate
            if (entity):

                # Take the bomb away; we optimistically placed it, but now we must take it away.  Sorry!
                entity.remove_silently()


            # Unlock with key
            universe.unlock(key)


    # Server - n/a (all bombs created locally)
    # Client - Receive notice that the client should spawn a bomb at a given location (some other player placed it there)
    def recv_create_bomb(self, data, source, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            pass

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # Active map
            m = universe.get_active_map()

            # Bit by bit
            pieces = data.split(";")

            # Distribute
            (key, x, y, radius, remote) = (
                pieces[0],
                int( pieces[1] ),
                int( pieces[2] ),
                int( pieces[3] ),
                ( int( pieces[4] ) == 1)
            )


            # Create a bomb
            bomb = m.create_bomb_with_unique_id(x = x, y = y)

            # Update radius
            bomb.set_radius(radius)


            # Remote bomb?  (Never in multiplayer, I don't think...)
            if (remote):

                # Tag it and track it!
                self.tag_bomb_as_remote(bomb)


            # Receipt
            self.send_unlock_with_key(key, source, control_center, universe)


    # Server - n/a (control gold locally)
    # Client - Sync the status of a given gold entity
    def recv_sync_one_gold(self, data, source, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            pass

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # Grab current map
            m = universe.get_active_map()

            # Ferret data
            pieces = data.split(";")

            # Distribute
            (entity_id, x, y, status) = (
                pieces[0],
                int( pieces[1] ),
                int( pieces[2] ),
                int( pieces[3] )
            )


            # Get the gold in question
            entity = m.get_entity_by_name(entity_id)

            log2( "Sync gold entity:  ", entity, "\n", data )

            # Validate
            if (entity):

                # Position
                entity.set_x(x)
                entity.set_y(y)


                # Before sync-ing the status let's see if we're changing from active to inactive.
                # If so, I'll call the mark_as_collected method real quick for the client, for the visual / audio effects.
                if ( (entity.get_status() == STATUS_ACTIVE) and (status == STATUS_INACTIVE) ):

                    # Just for show and tell
                    entity.mark_as_collected_by_actor(control_center, universe, actor = None) # (?) None I guess, it ignores it in netplay at the moment either way.


                # Status
                entity.set_status(status)


                # Set to active?
                if (status == STATUS_ACTIVE):

                    # Queue it for reactivation
                    entity.queue_for_reactivation()


    # Server - n/a (server controls enemy AI locally)
    # Client - Receive enemy AI sync data in the form of XML
    def recv_sync_enemy_ai(self, data, source, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            pass

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            log( "Syncing AI..." )

            # Compile XML
            root = XMLParser().create_node_from_xml(data)

            # Fetch current level
            m = universe.get_active_map()


            # Loop enemies
            for ref_entity in root.get_first_node_by_tag("enemies").get_nodes_by_tag("entity"):

                # Fetch enemy
                entity = m.get_entity_by_name( ref_entity.get_attribute("name") )

                # Validate
                if (entity):

                    # Get ai state node
                    ref_ai_state = ref_entity.find_node_by_tag("ai-state")

                    # Validate
                    if (ref_ai_state):

                        # Update AI state data
                        entity.load_ai_state(ref_entity, m, compress = True)
                        entity.sync_ai_state(ref_entity)

                        # Update the enemy object to keep the current target's name in sync
                        entity.set_current_target_name(entity.ai_state.ai_target_name, control_center, universe)

                        """
                        # (?) what is this for?
                        #colliding_players = m.check_interentity_collision_against_entity_types( (GENUS_PLAYER,), entity )
                        colliding_players = m.query_interentity_collision_for_entity_against_entity_types( (GENUS_PLAYER,), entity ).get_results()

                        for player in colliding_players:

                            # (?) why?
                            # (...) (Don't do this for the local player, local always knows own state 100%)
                            if ( player != universe.get_local_player() ):
                                player.set_sync_status(SYNC_STATUS_PENDING)
                        """


            log( "Done." )


    # Server - Update given player's location and update latency offset for that player,
    #          then broadcast message to all clients (excluding sender)
    # Client - Update given player's location and update latency offset for that player.
    def recv_sync_player_by_id(self, data, source, control_center, universe):

        # Both the server and any client will update in the same fashion, so we'll
        # take care of that right now.
        root = XMLParser().create_node_from_xml(data)

        # Validate that xml compiled successfully
        if (root):

            # Get player node
            node = root.find_node_by_tag("player")

            # Get player id / slot
            player_id = int( node.get_attribute("id") )

            # Get player entity
            player = universe.get_active_map().get_entity_by_name("player%d" % player_id)

            # Validate
            if (player):

                # Sync player
                player.sync_ai_state(node)


            """ Server forwarding """
            # If this is the server, we should forward the received player sync data to all other clients
            if ( self.get_status() == NET_STATUS_SERVER ):

                # Ignore the player who sent this... they already know their data
                self.ignore(source)

                # Send this player sync data along
                self.send_sync_player_by_id(player_id, control_center, universe)

                # Stop ignoring the source
                self.attend(source)


    # Server - n/a (server controls map-to-map transitions locally)
    # Client - Receive notice that the client should transition to the next level (or some other level)
    def recv_transition_to_map(self, data, source, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            pass

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # Lock key, map name
            (key, name) = data.split(";")


            # Fetch the window controller
            window_controller = control_center.get_window_controller()


            # Hook the universe into the window controller
            window_controller.hook(universe)

            # App-level fade out, triggering a (forwarded) net transition event on complete
            window_controller.fade_out(
                on_complete = "fwd.net.transition.finalize"
            )


            # Track the map we're going to transition to in the universe's session
            universe.set_session_variable("net.transition.target", name)


            # Receipt
            self.send_unlock_with_key(key, source, control_center, universe)


    # Server - n/a (server controls level complete locally)
    # Client - Receive notice that the level is complete
    def recv_level_complete(self, data, source, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            pass

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # Parcel
            (key, next_map_name) = data.split(";")


            # Fetch window controller
            window_controller = control_center.get_window_controller()

            # Handle
            localization_controller = control_center.get_localization_controller()


            # Hook the universe into the window controller
            window_controller.hook(universe)


            # Throw a brief delay on the planned fade
            window_controller.delay(NET_TRANSITION_DELAY)

            # App-level fade out
            window_controller.fade_out(
                on_complete = "fwd.net.transition.finalize"
            )


            # Track the map we're going to load next
            universe.set_session_variable("net.transition.target", next_map_name)

            # Save linear progress data (mark current level as complete, best time, etc.)
            universe.save_linear_progress(control_center, universe)

            # Add a newsfeed item
            window_controller.get_newsfeeder().post({
                "type": NEWS_NET_LEVEL_COMPLETE,
                "title": localization_controller.get_label("level-complete:label"),
                "content": localization_controller.get_label("moving-to-next-level:label")
            })


            # Receipt
            self.send_unlock_with_key(key, source, control_center, universe)


    # Server - n/a (server controls level failure locally)
    # Client - Receive notice that the players have all died, level failed
    def recv_level_failed(self, data, source, control_center, universe):

        if ( self.get_status() == NET_STATUS_SERVER ):

            pass

        elif ( self.get_status() == NET_STATUS_CLIENT ):

            # Parcel
            (key, next_map_name) = data.split(";")


            # Fetch window controller
            window_controller = control_center.get_window_controller()


            # Hook the universe into the window controller
            window_controller.hook(universe)


            # Throw a brief delay on the planned fade
            window_controller.delay(90)

            # App-level fade out
            window_controller.fade_out(
                on_complete = "fwd.net.transition.finalize"
            )


            # Track the map we're going to load "next"
            universe.set_session_variable("net.transition.target", next_map_name)

            # Add a newsfeed item
            window_controller.get_newsfeeder().post({
                "type": NEWS_NET_LEVEL_FAILED,
                "title": control_center.get_localization_controller().get_label("level-failed:title"),
                "content": control_center.get_localization_controller().get_label("level-failed:message")
            })


            # Receipt
            self.send_unlock_with_key(key, source, control_center, universe)

