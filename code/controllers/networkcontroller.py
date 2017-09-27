import sys, time
import re

import random #**debug purposes

import socket
import select
import errno

import Queue

from extensions.networkcontrollerextensions import NetworkControllerSendFunctionsExt, NetworkControllerRecvFunctionsExt
from extensions.networkregisteredmessage import NetworkRegisteredMessage

from tools.netconsole import NetConsole

from code.utils.common import log, log2, logn, coalesce

from code.constants.common import TILE_WIDTH
from code.constants.states import STATUS_ACTIVE, STATUS_INACTIVE

from code.constants.network import *
from code.constants.newsfeeder import NEWS_NET_PLAYER_TIMED_OUT # The only one we need (?)

class NetworkCommand:

    def __init__(self, command = "", source = None):

        # What is the raw command?
        self.command = command

        # Which connection send this command, in case we want to directly reply to them?
        self.source = source


    def get_command(self):

        return self.command


    def get_source(self):

        return self.source


class SocketServer:

    def __init__(self, host = "localhost", port = 8589):

        # **Debug...
        self.simulated_lag = 0


        # Default to active
        self.status = STATUS_ACTIVE

        # Set up the "server" to listen for incoming connection requests
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        #self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Async
        self.server.setblocking(0)

        # Bind the server to a given host and port
        self.server.bind(
            ("", port)
        )

        # Listen for incoming connection quests
        self.server.listen(5)


        self.lock_count = 0


        # A local lock indicates that the local player should stop handling input pending a receipt / timeout
        self.local_lock_count = 0

        # A global lock indicates that all game logic should pause pending receipt / timeout
        self.global_lock_count = 0


        # Listening sockets
        self.inputs = [self.server]

        # Outbound sockets
        self.outputs = []

        # Queue objects that contain data we're sending, keyed by output socket
        self.output_queues_by_connection = {}


        # Let us keep track of which player ids we have already assigned.  New players cannot use these.
        self.active_player_ids = [1] # The server is player 1


        # Translate a socket to a player id;
        self.player_ids_by_connection = {}

        # Translate a player id to a socket.
        self.connections_by_player_id = {}


        # Ping data per connection, hashed by player id
        self.ping_data_by_player_id = {}


        # Whenever we send a message, we will assign it a unique id.  This variable helps us iterate through the possible ids.
        self.next_message_id = 1

        # As we receive messages from each player, we will make a note of which messages we have
        # previously received.  This allows us to ignore duplicates (in case of timeout retries).
        self.received_message_ids_by_connection = {}


        # For each client (by connection), we'll keep a hash of "registered" messages, those being the messages
        # that require a receipt from the given client.
        self.registered_messages_by_connection = {}


        # The server can choose to ignore any given connection when sending messages
        self.ignored_connections = []

        # (?)
        self.awaiting_shutdown = False


        # When a player disconnects, we'll send them an "ok, we know you're leaving" message.
        # At that point, we'll add the player's connection to a list of "finished" connections;
        # when we have sent the last reamining data over the wire (the confirmation data), we'll drop the connection.
        self.finished_connections = []


        # If we do not receive the entirety of a packet in a given read,
        # we will save what we did happen to get in a buffer.
        self.buffers_by_connection = {}

        self.commands = []


        log2( "Server is online at %s:%d and listening for connections." % (host, port) )
        logn( "network", "Server is online at %s:%d and listening for connections." % (host, port) )


    def generate_player_id(self):

        player_id = 2

        while (player_id <= 8):

            if ( not (player_id in self.active_player_ids) ):

                self.active_player_ids.append(player_id)

                return player_id

            else:

                player_id += 1

        return -1


    # Generate a unique (incremental) message id.
    def generate_message_id(self):

        # Just increment the counter
        self.next_message_id += 1

        # Return the new id
        return self.next_message_id


    # Set ping data hash for a given player id
    def set_ping_data_by_player_id(self, player_id, h):

        # Set
        self.ping_data_by_player_id[player_id] = h


    # Get ping data hash for a given player id
    def get_ping_data_by_player_id(self, player_id):

        # Validate
        if (player_id in self.ping_data_by_player_id):

            # Return hash
            return self.ping_data_by_player_id[player_id]


    def get_player_ids(self, shunned_ids):

        results = []

        for player_id in self.active_player_ids:

            if ( not (player_id in shunned_ids) ):

                results.append(player_id)

        return results


    def get_connection_by_player_id(self, player_id):

        if (player_id in self.connections_by_player_id):

            return self.connections_by_player_id[player_id]

        else:

            return None


    def get_player_id_by_connection(self, conn):

        if (conn in self.player_ids_by_connection):

            return self.player_ids_by_connection[conn]

        else:

            return -1


    def announce_shutdown(self):

        # Tell each client we're shutting down
        self.broadcast("shutdown")

        self.awaiting_shutdown = True


    def lock(self):

        self.lock_count += 1


    def unlock(self):

        self.lock_count -= 1

        # Don't go negative
        if (self.lock_count < 0):

            self.lock_count = 0


    def is_locked(self):

        return (self.lock_count > 0)


    # Local lock
    def local_lock(self):

        self.local_lock_count += 1

    # Local unlock
    def local_unlock(self):

        self.local_lock_count -= 1

        # Don't go negative
        if (self.local_lock_count < 0):

            self.local_lock_count = 0

    # Check local lock status
    def is_local_locked(self):

        # Note that a global lock implies a local lock
        return ( (self.local_lock_count > 0) or (self.global_lock_count > 0) )


    # Global lock
    def global_lock(self):

        self.global_lock_count += 1

    # Global unlock
    def global_unlock(self):

        self.global_lock_count -= 1

        # Don't go negative
        if (self.global_lock_count < 0):

            self.global_lock_count = 0

    # Check global lock status
    def is_global_locked(self):

        return (self.global_lock_count > 0)


    # Disabled sending to a given connection
    def ignore(self, conn):

        # Don't duplicate
        if ( not (conn in self.ignored_connections) ):

            # Ignore connection when sending data
            self.ignored_connections.append(conn)


    # Stop ignoring a given connection
    def attend(self, conn):

        # Make sure we never return attention to a finished connection; we will never send another
        # message to a finished connection.
        if ( not (conn in self.finished_connections) ):

            # Try to find the given connection
            i = 0
            while ( i < len(self.ignored_connections) ):

                # Match?
                if ( self.ignored_connections[i] == conn ):

                    # Remove it
                    self.ignored_connections.pop(i)

                # Loop
                else:
                    i += 1


    # Get all active connections (just excludes ignored connections)
    def get_active_connections(self):

        # Track
        connections = []

        # Check all connected players
        for conn in self.output_queues_by_connection:

            # Not ignored?
            if ( not (conn in self.ignored_connections) ):

                # Include
                connections.append(conn)

        # Return active connections
        return connections


    def broadcast(self, data):

        if ( not self.is_locked() ):

            #print "Attempting to broadcast."

            if (not self.awaiting_shutdown):

                #print "\tSearching for clients."

                for conn in self.get_active_connections():#output_queues_by_connection:

                    #print "\t\tFound client:  ", conn

                    self.mail(conn, data)


    def mail(self, conn, data):

        self.send_unregistered_message(conn, data)
        return


        if ( not self.is_locked() ):

            if (not self.awaiting_shutdown):

                if (conn in self.get_active_connections()):#output_queues_by_connection):

                    self.output_queues_by_connection[conn].put(data + NET_COMMAND_SEPARATOR)

                    if (not (conn in self.outputs)):

                        self.outputs.append(conn)

                    log( "Mailing '%s' to:  " % data, conn )


    # Send an unregistered message to a given client.  This message type does not expect any receipt or confirmation.
    def send_unregistered_message(self, conn, data):

        if ( not self.is_locked() ):

            if ( conn in self.get_active_connections() ):

                # Generate a new id for this message
                message_id = self.generate_message_id()

                # Add the new message to the outbox.
                # Note that we specify 0 after the message id to indicate that we do not need a receipt.
                self.output_queues_by_connection[conn].put( "%d;%d;%s%s" % (NET_MESSAGE_UNREGISTERED, message_id, data, NET_COMMAND_SEPARATOR) )


                # Make sure this client's socket is in our active outputs list
                if ( not (conn in self.outputs) ):

                    # We now have data to send to this client
                    self.outputs.append(conn)


    # Send a registered message to a given client.  We will require a receipt for this message; if we don't get one,
    # we'll ultimately drop the player from the game.
    def send_registered_message(self, conn, data, options, message_id = None):

        if ( not self.is_locked() ):

            if ( conn in self.get_active_connections() ):

                # Generate a new id for this message, unless we provided an old one explicitly
                message_id = coalesce( message_id, self.generate_message_id() )


                # Create a registered message entry for this connection
                self.registered_messages_by_connection[conn][message_id] = NetworkRegisteredMessage(data).configure(options)


                # Look up what kind of lock, if any, we applied to this registered message
                net_lock_type = self.registered_messages_by_connection[conn][message_id].get_net_lock_type()

                # If we did a local local, increment the local lock count
                if (net_lock_type == NET_LOCK_LOCAL):

                    # Local player will stop responding to gameplay input until we receive a receipt / timeout
                    self.local_lock()

                elif (net_lock_type == NET_LOCK_GLOBAL):

                    # All game logic will stop until we receive a receipt / timeout
                    self.global_lock()


                # Add the message to the output queue for this client socket.  We'll be expecting a receipt shortly.
                # Note that we indicate 1 after the message to specify that we need a receipt for this message.
                self.output_queues_by_connection[conn].put( "%d;%d;%s%s" % (NET_MESSAGE_REGISTERED, message_id, data, NET_COMMAND_SEPARATOR) )


                # Make sure this client's socket is in our active outputs list
                if ( not (conn in self.outputs) ):

                    # We now have data to send to this client
                    self.outputs.append(conn)

                log2( "Send registered message id '%d' to a client" % message_id )


    # Send raw packet data without attaching a message id
    def send_raw_data(self, conn, data):

        if ( not self.is_locked() ):

            if ( conn in self.get_active_connections() ):

                # Add the new message to the outbox
                self.output_queues_by_connection[conn].put( "%s%s" % (data, NET_COMMAND_SEPARATOR) )


                # Make sure this client's socket is in our active outputs list
                if ( not (conn in self.outputs) ):

                    # We now have data to send to this client
                    self.outputs.append(conn)


    def get_next_command(self):

        if ( len(self.commands) > 0 ):

            return self.commands.pop(0)

        else:

            return None


    def fetch_commands_and_remainder_from_buffer(self, data, conn):

        # **debug:  simulate delayed packet response during local testing...
        if ( self.simulated_lag > 0 ):
            self.simulated_lag -= 1
            return ( [], data )

        commands = []

        pos = data.find(NET_COMMAND_SEPARATOR)

        while (pos >= 0):

            # Fetch the entire packet
            packet = data[0 : pos]

            # We want to remove the message type (the first value) and the given message id (the second value) from the packet, then mark it as processed.
            pieces = packet.split(";", 2)

            # Validate that we got all parts; if not, we'll ignore this packet entirely.
            if ( len(pieces) != 3 ):

                pass

            else:

                # Convenience
                (message_type, message_id, message) = pieces

                # Cast message type and message id as ints
                message_type = int(message_type)
                message_id = int(message_id)


                log2( "Incoming:  ", (message_type, message_id, message) )


                # Did we get a generic receipt packet?
                if (message_type == NET_MESSAGE_RECEIPT):

                    # Check our log of registered messages for the given client.  If we have one by the given
                    # message id, then we can remove it thanks to this confirmation of receipt.
                    if ( message_id in self.registered_messages_by_connection[conn] ):

                        # The given message id is indicating which message id the given client is confirming.
                        registered_message = self.registered_messages_by_connection[conn].pop(message_id)


                        # Check which kind of lock, if any, we had on that registered message.
                        net_lock_type = registered_message.get_net_lock_type()


                        # Unlock as needed
                        if (net_lock_type == NET_LOCK_LOCAL):

                            self.local_unlock()

                        elif (net_lock_type == NET_LOCK_GLOBAL):

                            self.global_unlock()


                # Otherwise, we have a registered/unregistered game data message.
                else:

                    # First, mark down this message id as received (for the given client)
                    if ( not (message_id in self.received_message_ids_by_connection[conn]) ):

                        # We won't process any message with this id again (in case of duplicates)
                        self.received_message_ids_by_connection[conn].append(message_id)

                        # Now add it to the list of pending commands
                        commands.append(
                            NetworkCommand(
                                command = message,
                                source = conn
                            )
                        )


                    # If the message requires a receipt (i.e. registered message), then let's send back a simple packet of message type "receipt"
                    # that carries the id of the message we're confirming.
                    if (message_type == NET_MESSAGE_REGISTERED):

                        # Note that we do this even if we've already processed the message.  The client just doesn't know that we've already processed it; let's re-confirm.
                        self.send_raw_data( conn, "%d;%d;" % (NET_MESSAGE_RECEIPT, message_id) )


            # Strip the message from the front of the buffer
            data = data[pos + len(NET_COMMAND_SEPARATOR): len(data)]

            # Try to find the endpoint of another packet
            pos = data.find(NET_COMMAND_SEPARATOR)


        return (commands, data)


    # Finish up communication to a given connection, prearing to drop the connection when done
    def finish_connection(self, conn):

        # Add it to the list of finished connections.  Avoid duplicates.
        if ( not (conn in self.finished_connections) ):

            # Almost done with this player.  Just need to send whatever data we have left for them before cleaning up.
            self.finished_connections.append(conn)

        # Ignore this connection from here forward...
        self.ignore(conn)


    # Drop a given connection and free the player id associated with it; another player can now take that slot.
    def drop_connection(self, conn):

        # Remove the connection from our inputs list
        i = 0
        while ( i < len(self.inputs) ):

            # Match?
            if ( self.inputs[i] == conn ):

                # Don't need it any more
                self.inputs.pop(i)

            else:
                i += 1


        # Remove it from the outputs list
        i = 0
        while ( i < len(self.outputs) ):

            # Match?
            if ( self.outputs[i] == conn ):

                # Gone
                self.outputs.pop(i)

            else:
                i += 1


        # Remove the output queue we had created for this connection
        if ( conn in self.output_queues_by_connection ):

            # Later!
            self.output_queues_by_connection.pop(conn)


        # Fetch the player id we had given to this connection
        if ( conn in self.player_ids_by_connection ):

            # Fetch and remove
            player_id = self.player_ids_by_connection.pop(conn)

            # Remove it from our list of active player ids
            i = 0
            while ( i < len(self.active_player_ids) ):

                # Match?
                if ( self.active_player_ids[i] == player_id ):

                    # So long
                    self.active_player_ids.pop(i)

                else:
                    i += 1


            # Remove the lookup that translated that player id to a given connection
            if ( player_id in self.connections_by_player_id ):

                # No more
                self.connections_by_player_id.pop(player_id)


        # If we were ignoring this connection, we don't need to do so anymore
        i = 0
        while ( i < len(self.ignored_connections) ):

            # Match?
            if ( self.ignored_connections[i] == conn ):

                # Begone!
                self.ignored_connections.pop(i)

            else:
                i += 1


        # Remove any buffered data we were holding on to for this connection
        if ( conn in self.buffers_by_connection ):

            # Goodbye
            self.buffers_by_connection.pop(conn)


        # Remove our history of received message ids for the given connection
        if ( conn in self.received_message_ids_by_connection ):

            # Later!
            self.received_message_ids_by_connection.pop(conn)


        # If we were waiting for a response to any registered message for this connection, we need to undo whatever
        # lock we had for each message while clearing that hash.
        if ( conn in self.registered_messages_by_connection ):

            # Loop through each pending message
            while ( len(self.registered_messages_by_connection[conn]) > 0 ):

                # Get the next in line
                registered_message = self.registered_messages_by_connection[conn].pop()


                # Undo whatever lock we had for the message we sent
                net_lock_type = registered_message.get_net_lock_type()

                # Unlock as needed
                if (net_lock_type == NET_LOCK_LOCAL):

                    self.local_unlock()

                elif (net_lock_type == NET_LOCK_GLOBAL):

                    self.global_unlock()


        # Lastly, let's close the socket.
        conn.close()


    # Send the web server an updated player count
    def web_update_player_count(self, control_center, universe):

        # Count the number of players currently in the game
        player_count = sum( 1 for i in range(1, 4+1) if int( universe.get_session_variable("net.player%d.joined" % i).get_value() ) == 1 )

        # Update the web server with the new player count.
        # We won't listen for a response.
        control_center.get_http_request_controller().send_get_with_name(
            name = "update-player-count",
            host = None, # use default
            port = 80,
            url = "/games/alrs/sessions/update.player.count.php",
            params = {
                "id": universe.get_session_variable("net.session.id").get_value(),
                "player-count": "%s" % player_count
            },
            tracked = False,
            force = True
        )


    # Send the web server an update on the current level
    def web_update_current_level(self, control_center, universe):

        # Get the active map
        m = universe.get_active_map()

        # Validate
        if (m):

            # Update the web server with the current map title.
            # We won't listen for a response.
            control_center.get_http_request_controller().send_get_with_name(
                name = "update-current-level",
                host = None, # use default
                port = 80,
                url = "/games/alrs/sessions/update.current.level.php",
                params = {
                    "id": universe.get_session_variable("net.session.id").get_value(),
                    "current-level": universe.get_map_data( m.get_name() ).get_title()
                },
                tracked = False,
                force = True
            )


    # Disconnect the server.  Also close any sockets we had open for listening to clients.
    # Theoretically, we close those sockets before ending the server.
    def disconnect(self):

        # Loop through all of our remaining outpue queues, keyed by connection
        while ( len(self.output_queues_by_connection) > 0 ):

            # Get the first remaining connection
            conn = self.output_queues_by_connection.keys()[0]

            # We must make sure to close any connection we still have to any client.
            # This function will drop the given connection entirely, removing it
            # from our "output queues by connection" hash and continuing the loop.
            self.drop_connection(conn)

        # Lastly, close our server listening socket
        self.server.close()

        # We're no longer active
        self.status = STATUS_INACTIVE


    # Process server socket
    def process(self, control_center, universe, timeout = 0.001):

        loops = 0

        command = ""

        if (self.status == STATUS_ACTIVE):

            if (self.awaiting_shutdown):

                if ( len(self.outputs) == 0 ):

                    self.server.close()
                    log( "All messages sent.  Shutting down." )

                    # Disconnect server
                    self.disconnect()

                    # Flag session as offline
                    universe.set_session_variable("net.online", "0")

                    self.status = STATUS_INACTIVE

                    return

            #print self.inputs, self.outputs

            (readable, writable, exceptional) = select.select(self.inputs, self.outputs, self.inputs, timeout)

            # Timeout; do nothing
            if ( not (readable or writable or exceptional) ):

                pass#print "Inactive..."

            # We have some data ready to process (read, write, or exception)
            else:

                # Check any socket with readable data present
                for s in readable:

                    # If the socket with input is the "server" socket, then we have an incoming connection request.
                    if (s == self.server):

                        # Accept the connection request
                        (conn, address) = s.accept()
                        log( "conn = ", conn )

                        logn( "network", "Accepted connection:  ", (conn, address) )


                        # If all slots are currently taken, then we will immediately close and thus reject this connection.
                        if (
                            all(
                                int( universe.get_session_variable("net.player%s.joined" % i).get_value() ) == 1 for i in range( 1, 1 + int( universe.get_session_variable("net.player-limit").get_value() ) )
                            ) or True == False
                        ):

                            # Send a "busy" data (blocking send call, I think?)
                            try:
                                conn.send("//busy//")
                            except:
                                pass

                            # Close connection
                            conn.close()

                        # Slot available!
                        else:

                            # Async
                            conn.setblocking(0)

                            # We'll want to poll this socket for readable data (further messages from the new client)
                            self.inputs.append(conn)

                            # Set up a queue for writing data to the new socket
                            self.output_queues_by_connection[conn] = Queue.Queue()

                            # Set up a registered message hash for this client
                            self.registered_messages_by_connection[conn] = {}

                            # Set up the log of which message ids we've received from this client
                            self.received_message_ids_by_connection[conn] = []

                            # Set up a buffer for streaming in data per connection
                            self.buffers_by_connection[conn] = ""


                            # Generate a player id for the new player
                            player_id = self.generate_player_id()

                            # Lookups
                            self.player_ids_by_connection[conn] = player_id
                            self.connections_by_player_id[player_id] = conn


                            # Flag slot as filled
                            universe.set_session_variable("net.player%d.joined" % player_id, "1")

                            # Make a note that we haven't received the nick yet
                            universe.set_session_variable("net.player%d.received-nick" % player_id, "0")


                            # Update the web server's player count data
                            self.web_update_player_count(control_center, universe)


                            # Ping
                            #self.mail(conn, "%d" % NET_MSG_PING)

                            # Assign player id
                            self.send_registered_message(
                                conn,
                                "%d;%d" % (NET_MSG_PLAYER_ID, self.player_ids_by_connection[conn]),
                                {
                                    "timeout": 2.0,
                                    "retries": 1,
                                    "net-lock-type": NET_LOCK_LOCAL
                                }
                            )
                            logn( "netcode", "Sending player ID at %s\n" % time.time() )

                            # Request player nick data so we can post a news item "so-and-so joined" in a moment
                            self.send_registered_message(
                                conn,
                                "%d;%d" % (NET_MSG_REQ_NICK, self.player_ids_by_connection[conn]),
                                {
                                    "timeout": 2.0,
                                    "retries": 1,
                                    "net-lock-type": NET_LOCK_LOCAL
                                }
                            )


                            # Update the new player with data on all currently-playing players
                            control_center.get_network_controller().send_sync_new_player_by_connection(conn, control_center, universe)

                    # Otherwise, we're getting data from a previously-accepted client...
                    else:

                        # Scope
                        data = None

                        try:

                            # Read in the data, up to 1KB at a time
                            data = s.recv(1024)

                        except:

                            # Drop the connection immediately
                            data = None


                        # If we didn't "get" any data, that signifies a disconnect.  Clean up time...
                        if (data == None):

                            #print "Goodbye, %s" % s.getpeername()
                            #print 5/0

                            # Get the player id before we drop the connection
                            player_id = self.get_player_id_by_connection(s)


                            # Set this slot as "not joined"
                            universe.get_session_variable("net.player%s.joined" % player_id).set_value("0")

                            # Update the web server's player count data
                            self.web_update_player_count(control_center, universe)


                            # In theory, the client just received a note from the server telling the client that this server
                            # is ending the session.  Whatever the case, we've lost connection and it's time to drop it...
                            self.drop_connection(s)

                            """
                            # Validate
                            if (s in self.inputs):

                                # Stop listening to the socket; the user has left.
                                self.inputs.remove(s)

                            # Clean up any output socket dedicated to this socket
                            if (s in self.outputs):

                                # Goodbye!
                                self.outputs.remove(s)

                            (host, port) = s.getpeername()

                            log( "Client @%s:%d disconnected." % (host, port) )
                            """

                        # Otherwise, process the data we did receive...
                        else:

                            self.buffers_by_connection[s] += data

                            """ Debug - Simulated lag flag(s) """
                            if ( "-lag" in sys.argv ):

                                self.simulated_lag = random.randint(10, 20) # **debug, simulated lag
                                log2(
                                    "Simulated lag:  %s" % self.simulated_lag
                                )

                            for i in range( 0, len(sys.argv) ):
                                if ( sys.argv[i].startswith("-lag") ):
                                    self.simulated_lag = int( sys.argv[i].split("=")[1] )

                            """ End debug """

                            #(host, port) = s.getpeername()

                            #print "Received from @%s:%d:  '%s'" % (host, port, data)


                # Check any socket with writable data present
                for s in writable:

                    data = None

                    # Try to get the next message in the queue to be sent to the client
                    try:
                        data = self.output_queues_by_connection[s].get_nowait()

                    # If the queue is empty, we'll remove the socket from the list.
                    except Queue.Empty:

                        # We will add this socket back into the "outputs" list next time we send data...
                        self.outputs.remove(s)

                    # If we have data to send, let's send it...
                    else:
                        log2( "Send:  '%s'" % data )
                        logn( 10, "%s : NET : Sending %s\n" % (time.time(), data) )

                        #print "Sending to:  ", s.getpeername()
                        try:
                            s.send(data)
                            logn( "network-server", "Send @%s:  %s" % (time.time(), data) )
                        except:
                            self.outputs.remove(s)


                # Check for exceptions
                for s in exceptional:

                    if (s in self.inputs):

                        self.inputs.remove(s)

                    if (s in self.outputs):

                        self.outputs.remove(s)

                    self.output_queues_by_connection.pop(s)

                    s.close()

            """
            r, w, e = select.select([sys.stdin], [], [], 0.0001)
            for s in r:
                if (s == sys.stdin):
                    command = sys.stdin.readline().strip()
            """

            # Loop through each connected client
            for conn in self.output_queues_by_connection:

                # Fetch any commands / unfinished packet (buffer) data for this client socket
                (commands, self.buffers_by_connection[conn]) = self.fetch_commands_and_remainder_from_buffer( self.buffers_by_connection[conn], conn )

                # Add the finished packets we got to our list of commands-to-be-processed
                self.commands.extend(commands)


                # Check the status if any registered message we sent to this user and haven't received a receipt for
                for message_id in self.registered_messages_by_connection[conn]:

                    # Convenience
                    registered_message = self.registered_messages_by_connection[conn][message_id]


                    # if we haven't heard back from the client in the time specified...
                    if ( registered_message.is_expired() ):

                        # Can we retry?
                        if ( registered_message.can_retry() ):

                            # Reset the timer as we prepare to resend the original message
                            registered_message.reset_last_send_time()

                            # Send the exact packet we sent last time, using the original message id.
                            # Note that we again provide a 1 after the message id; we still want a receipt for this message!
                            self.send_raw_data( conn, "%d;%d;%s" % ( NET_MESSAGE_REGISTERED, message_id, registered_message.get_message() ) )

                        else:

                            # Mark the connection as "finished."  I can't drop it entirely right now because I'm in the middle of a foreach loop through the hash.
                            self.finish_connection(conn)


                            # Quick player id translation
                            timed_out_player_id = self.get_player_id_by_connection(conn)

                            # Post a newsfeeder item saying "so-and-so timed out."
                            control_center.get_window_controller().get_newsfeeder().post({
                                "type": NEWS_NET_PLAYER_TIMED_OUT,
                                "title": control_center.get_localization_controller().get_label("player-timed-out:title"),
                                "content": universe.get_session_variable("net.player%d.nick" % timed_out_player_id).get_value()
                            })


                            # Set this slot as "not joined"
                            universe.get_session_variable("net.player%s.joined" % timed_out_player_id).set_value("0")

                            # Update the web server's player count data
                            self.web_update_player_count(control_center, universe)


                            # Undo whatever lock we had for the message we sent
                            net_lock_type = registered_message.get_net_lock_type()

                            # Unlock as needed
                            if (net_lock_type == NET_LOCK_LOCAL):

                                self.local_unlock()

                            elif (net_lock_type == NET_LOCK_GLOBAL):

                                self.global_unlock()


                            log2( "Timing out client socket:  ", conn )
                            #print 5/0


            # Check each of our "finished" connections; if we've cleared out the output queue for any
            # such connection, then we should be able to completely drop that connection now.
            i = 0
            while ( i < len(self.finished_connections) ):

                logn( "network", "Finished conn:  ", self.finished_connections[i] )

                # If the connection is no longer in our list of outputs, then we don't have any pending data remaining.
                # Thus, we'll drop the connection now.
                if ( not (self.finished_connections[i] in self.outputs) ):

                    # Drop and pop!
                    self.drop_connection(
                        self.finished_connections.pop(i)
                    )

                    logn( "network", "\tDropped!" )

                else:
                    i += 1
                    logn( "network", "\tNot ready to drop; output pending?" )

            #(commands, self.buffer) = self.fetch_commands_and_remainder_from_buffer( self.buffer )

            #self.commands.extend(commands)

class SocketClient:

    def __init__(self, host = "localhost", port = 8589):

        # **Debug...
        self.simulated_lag = 0


        # Default to active
        self.status = STATUS_ACTIVE

        # Set up a "client" socket that will send messages to the server
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # (?) (Do I need this?) Async
        self.client.setblocking(0)

        # Connect to the server
        try:
            self.client.connect( (host, port) )

        except socket.error, e:

            if (e.args[0] == errno.EINPROGRESS):
                pass

            # (windows only?)
            elif (e.args[0] == errno.EWOULDBLOCK):
                pass

            # (windows only?)
            elif (e.args[0] == errno.EISCONN):
                pass

            else:
                raise e

        else:
            raise Exception("Unknown client connection failure.")


        self.online = False


        self.lock_count = 0


        # A local lock indicates that the local player should stop handling input pending a receipt / timeout
        self.local_lock_count = 0

        # A global lock indicates that all game logic should pause pending receipt / timeout
        self.global_lock_count = 0


        # Listening sockets
        self.inputs = [self.client]

        # Outbound sockets
        self.outputs = []

        # A Queue object that holds any packet data we want to send to the server.
        self.output_queue = Queue.Queue()


        # When time comes to disconnect from the session (perhaps server notified us that the session is ending),
        # we'll put our socket in a "finished" list.  Once we are out of queued messages for the connection, we'll disconnect.
        self.finished_connections = []


        # Whenever we send a message, we will assign it a unique id.  This variable helps us iterate through the possible ids.
        self.next_message_id = 1

        # As we receive messages from the server, we will make a note of which messages we have
        # previously received.  This allows us to ignore duplicates (in case of timeout retries).
        self.received_message_ids = []


        # Use a hash to store any registered messages we need to send.  Hash by message id.
        self.registered_messages = {}


        # If we don't receive the entirety of a given packet, we'll save what we have in this buffer.
        self.buffer = ""

        self.commands = []


        log( "Client created, hoping to connect?" )


    # Generate a unique (incremental) message id.
    def generate_message_id(self):

        # Just increment the counter
        self.next_message_id += 1

        # Return the new id
        return self.next_message_id


    def fetch_commands_and_remainder_from_buffer(self, data):

        # **debug:  simulate delayed packet response during local testing...
        if ( self.simulated_lag > 0 ):
            self.simulated_lag -= 1
            return ( [], data )

        commands = []

        pos = data.find(NET_COMMAND_SEPARATOR)

        while (pos >= 0):

            # Fetch the entire packet
            packet = data[0 : pos]

            # We want to remove the message type (the first value) and the given message id (the second value) from the message and mark it as processed
            pieces = packet.split(";", 2)

            # Validate that we got all parts; if not, we'll ignore this packet entirely.
            if ( len(pieces) != 3 ):

                pass

            else:

                # Convenience
                (message_type, message_id, message) = pieces

                # Cast message type and message id as ints
                message_type = int(message_type)
                message_id = int(message_id)


                log2( "Incoming:  ", (message_type, message_id, message) )


                # Did we get a generic receipt packet?
                if (message_type == NET_MESSAGE_RECEIPT):

                    # Check to see if we're looking for a receipt for a message by the given message id.
                    if ( message_id in self.registered_messages ):

                        # The given message id indicates which message the server is confirming.
                        registered_message = self.registered_messages.pop(message_id)


                        # Check which lock type we used with this message (if any)
                        net_lock_type = registered_message.get_net_lock_type()


                        # Unlock as needed
                        if (net_lock_type == NET_LOCK_LOCAL):

                            self.local_unlock()

                        elif (net_lock_type == NET_LOCK_GLOBAL):

                            self.global_unlock()


                # Any other message is a registered/unregistered message containing game data
                else:

                    # Make sure we haven't already received a message with this id; don't process repeats.
                    if ( not (message_id in self.received_message_ids) ):

                        # First, mark down this message id as received from the server
                        self.received_message_ids.append(message_id)

                        # Now add it to the list of pending commands
                        commands.append(
                            NetworkCommand(
                                command = message,
                                source = self.client
                            )
                        )


                    # Registered messages require a confirmation of receipt.  We'll send back a receipt
                    # each time, even if we've already processed the game data.
                    if (message_type == NET_MESSAGE_REGISTERED):

                        # **Debug:  Add a make-believe packet loss chance...
                        if ( random.randint(1, 10) > 0 ):

                            # Even if we've processed it before, the server somehow might not have received our receipt.
                            self.send_raw_data( "%d;%d;" % (NET_MESSAGE_RECEIPT, message_id) )

                        else:
                            log2( "**Emulating packet loss; not sending receipt." )


            # Strip the message from the front of the buffer
            data = data[pos + len(NET_COMMAND_SEPARATOR): len(data)]

            # Try to find the endpoint of another packet
            pos = data.find(NET_COMMAND_SEPARATOR)


        return (commands, data)


    def get_next_command(self):

        if ( len(self.commands) > 0 ):

            return self.commands.pop(0)

        else:

            return None


    def lock(self):

        self.lock_count += 1


    def unlock(self):

        self.lock_count -= 1

        # Don't go negative
        if (self.lock_count < 0):

            self.lock_count = 0


    def is_locked(self):

        return (self.lock_count > 0)


    # Local lock
    def local_lock(self):

        self.local_lock_count += 1

    # Local unlock
    def local_unlock(self):

        self.local_lock_count -= 1

        # Don't go negative
        if (self.local_lock_count < 0):

            self.local_lock_count = 0

    # Check local lock status
    def is_local_locked(self):

        # Note that a global lock implies a local lock
        return ( (self.local_lock_count > 0) or (self.global_lock_count > 0) )


    # Global lock
    def global_lock(self):

        self.global_lock_count += 1

    # Global unlock
    def global_unlock(self):

        self.global_lock_count -= 1

        # Don't go negative
        if (self.global_lock_count < 0):

            self.global_lock_count = 0

    # Check global lock status
    def is_global_locked(self):

        return (self.global_lock_count > 0)


    def get_connection(self):

        return self.client


    def broadcast(self, data):

        self.send_unregistered_message(data)
        return

        if ( not self.is_locked() ):

            log( "Attempting to talk to server." )

            if (self.online):

                log( "\tSearching for server." )

                self.output_queue.put(data + NET_COMMAND_SEPARATOR)

                if (not (self.client in self.outputs)):

                    self.outputs.append(self.client)


    def reply_to_server(self, data):

        self.send_unregistered_message(data)
        return

        self.broadcast(data)


    def send_to_server(self, data):

        self.send_unregistered_message(data)
        return

        self.broadcast(data)


    # Send an unregistered message to the server.  This message type does not expect any receipt or confirmation.
    def send_unregistered_message(self, data):

        if ( not self.is_locked() ):

            # Generate a new id for this message
            message_id = self.generate_message_id()

            # Add the new message to the outbox.
            # Note that we enter a 0 after the message id to indicate that we don't need any receipt for this message.
            self.output_queue.put( "%d;%d;%s%s" % (NET_MESSAGE_UNREGISTERED, message_id, data, NET_COMMAND_SEPARATOR) )


            # Make sure our connection to the server is in the active outputs list; we have data to send!
            if ( not (self.client in self.outputs) ):

                # We now have data to send to this client
                self.outputs.append(self.client)


    # Send a registered message to the server.  We will require a receipt for this message; if we don't get one,
    # we'll ultimately drop out of the game.
    def send_registered_message(self, data, options, message_id = None):

        if ( not self.is_locked() ):

            # Generate a new id for this message, unless we provided an old one explicitly
            message_id = coalesce( message_id, self.generate_message_id() )

            # Create a registered message entry for this special message.
            self.registered_messages[message_id] = NetworkRegisteredMessage(data).configure(options)


            # Look up what kind of lock, if any, we applied to this registered message
            net_lock_type = self.registered_messages[message_id].get_net_lock_type()

            # If we did a local local, increment the local lock count
            if (net_lock_type == NET_LOCK_LOCAL):

                # Local player will stop responding to gameplay input until we receive a receipt / timeout
                self.local_lock()

            elif (net_lock_type == NET_LOCK_GLOBAL):

                # All game logic will stop until we receive a receipt / timeout
                self.global_lock()


            # Add the message to the output queue.  We'll be expecting a receipt shortly.
            # Note that we specify 1 after the message id to signal that we demand a receipt for this message.
            self.output_queue.put( "%d;%d;%s%s" % (NET_MESSAGE_REGISTERED, message_id, data, NET_COMMAND_SEPARATOR) )


            # Make sure our connection to the server is in the active outputs list; we have data to send!
            if ( not (self.client in self.outputs) ):

                # We now have data to send to this client
                self.outputs.append(self.client)


            log2( "Send registered message id '%d' to the server" % message_id )


    # Send raw packet data without attaching a message id
    def send_raw_data(self, data):

        if ( not self.is_locked() ):

            # Add the new message to the outbox
            self.output_queue.put( "%s%s" % (data, NET_COMMAND_SEPARATOR) )


            # Make sure this client's socket is in our active outputs list
            if ( not (self.client in self.outputs) ):

                # We now have data to send to this client
                self.outputs.append(self.client)


    # Finish communicating with the server; send our last goodbye messages, then disconnect.
    def finish_connection(self):

        # Add our connection to the server to the list of finished connections.  Avoid duplicates.
        if ( not (self.client in self.finished_connections) ):

            # Almost done with this player.  Just need to send whatever data we have left for them before cleaning up.
            self.finished_connections.append(self.client)


    # Drop connection to the server
    def disconnect(self):

        log2( "Client preparing to disconnect" )

        # Clear all inputs (there should only be one, but hey...)
        while ( len(self.inputs) > 0 ):

            # All gone
            self.inputs.pop()

        # Same for outputs
        while ( len(self.outputs) > 0 ):

            # Ciao
            self.outputs.pop()


        log2( "Client closing socket" )


        # Remove our history of received message ids from the server
        self.received_message_ids = []


        # If we were waiting for a response to any registered message from the server, then we need to undo the
        # lock we had for each message while clearing that hash.
        while ( len(self.registered_messages) > 0 ):

            # Get the next in line
            registered_message = self.registered_messages.pop()


            # Undo whatever lock we had for the message we sent
            net_lock_type = registered_message.get_net_lock_type()

            # Unlock as needed
            if (net_lock_type == NET_LOCK_LOCAL):

                self.local_unlock()

            elif (net_lock_type == NET_LOCK_GLOBAL):

                self.global_unlock()


        # Close socket
        self.client.close()


        log2( "Client disconnected" )


        # Set status as inactive
        self.status = STATUS_INACTIVE


    # Process client socket
    def process(self, control_center, universe, timeout = 0.001):

        if (self.status == STATUS_ACTIVE):

            #print self.inputs, self.outputs

            (readable, writable, exceptional) = select.select(self.inputs, self.outputs, self.inputs, timeout)

            # Timeout?  Oh well...
            if ( not (readable or writable or exceptional) ):

                pass#print "Client inactive; no message from server."

            # We can read or write something!  (Or we have an error...)
            else:

                # See if our client socket got a response from the server!
                for s in readable:

                    # If we haven't connected yet, then this must be the acceptance ping...
                    if (not self.online):

                        # We're online!
                        self.online = True


                        # Set up a registered message hash
                        self.registered_messages = {}

                        # Set up the log of which message ids we've received from the server
                        self.received_message_ids = []


                        (host, port) = s.getpeername()

                        log( "Client connected successfully to server @%s%d." % (host, port) )

                    else:

                        # Scope
                        data = None

                        # Try to read data
                        try:

                            # Read from socket
                            data = s.recv(1024)
                            logn( 10, "%s : NET : Receiving %s\n" % (time.time(), data) )
                            logn( "network-client", "Recv @%s:  %s" % (time.time(), data) )

                        # Bad socket?
                        except:

                            # We'll leave data as None and deal with it below
                            pass


                        # No data means we lost connection to the server
                        if (not data):

                            # Disconnect the client.  Ideally, this "loss of response to server" happened
                            # because it received our quit notice and closed communications.
                            self.disconnect()

                            # Flag session as no longer online
                            universe.set_session_variable("net.online", "0")


                            #self.client.close()
                            #log( "Lost connection to server.  Closing connection." )
                            #print 5/0
                            self.status = STATUS_INACTIVE

                            return

                        # Check for a "server was too busy" message (connection refused)
                        elif (data == "//busy//"):

                            # Disconnect
                            self.disconnect()

                            # Flag session as offline
                            universe.set_session_variable("net.online", "0")


                            self.status = STATUS_INACTIVE

                        else:

                            self.buffer += data

                            (host, port) = s.getpeername()

                            #print "Received from @%s:%d:  '%s'" % (host, port, data)

                            """ Debug """
                            if ( "-lag" in sys.argv ):

                                self.simulated_lag = random.randint(10, 20) # **debug, simulated lag
                                log2(
                                    "Simulated lag:  %s" % self.simulated_lag
                                )

                            for i in range( 0, len(sys.argv) ):
                                if ( sys.argv[i].startswith("-lag") ):
                                    self.simulated_lag = int( sys.argv[i].split("=")[1] )
                            """ End Debug """

                # Do we have data to write?
                for s in writable:

                    data = None

                    # Try to get the next message in the queue to be sent to the client
                    try:
                        data = self.output_queue.get_nowait()

                    # If the queue is empty, we'll remove the socket from the list.
                    except Queue.Empty:

                        # We will add this socket back into the "outputs" list next time we send data...
                        self.outputs.remove(s)

                    # If we have data to send, let's send it...
                    else:

                        try:
                            s.send(data)
                        except:
                            self.outputs.remove(s)


                # Check for exceptions
                for s in exceptional:

                    # Just disconnect the client
                    self.disconnect()

                    # Flag session as no longer online
                    universe.set_session_variable("net.online", "0")

                    # Clear commands list
                    self.commands = []

                    # Abort
                    return


            #print self.fetch_commands_from_buffer( self.buffer )
            (commands, self.buffer) = self.fetch_commands_and_remainder_from_buffer( self.buffer )

            self.commands.extend(commands)


            # Check the status if any registered message we sent to the server and haven't received a receipt for
            for message_id in self.registered_messages:

                # Convenience
                registered_message = self.registered_messages[message_id]


                # if we haven't heard back from the client in the time specified...
                if ( registered_message.is_expired() ):

                    # Can we retry?
                    if ( registered_message.can_retry() ):

                        # Reset the timer as we prepare to resend the original message
                        registered_message.reset_last_send_time()

                        # Send the exact packet we sent last time, using the original message id.
                        # Note that we again provide a 1 after the message id; we still want a receipt for this message!
                        self.send_raw_data( "%d;%d;%s" % ( NET_MESSAGE_REGISTERED, message_id, registered_message.get_message() ) )

                    else:

                        # Mark our connection to the server as "finished."  I could drop it now (I'm not in a hash like I am with the server), but
                        # I want to keep the code parallel.
                        self.finish_connection()


                        # Check which lock type we used with this message (if any)
                        net_lock_type = registered_message.get_net_lock_type()


                        # Unlock as needed
                        if (net_lock_type == NET_LOCK_LOCAL):

                            self.local_unlock()

                        elif (net_lock_type == NET_LOCK_GLOBAL):

                            self.global_unlock()


                        log2( "Lost server connection." )


            # Check each of our "finished" connections; if we've cleared out the output queue for any
            # such connection, then we should be able to completely drop that connection now.
            i = 0
            while ( i < len(self.finished_connections) ):

                logn( "network", "Finished connection to server:  ", self.finished_connections[i] )

                # If the connection is no longer in our list of outputs, then we don't have any pending data remaining.
                # Thus, we'll drop the connection now.
                if ( not (self.finished_connections[i] in self.outputs) ):

                    # Disconnect
                    self.disconnect()

                    # Flag session as no longer online
                    universe.set_session_variable("net.online", "0")

                    logn( "network", "\Client disconnected!" )
                    return

                else:
                    i += 1
                    logn( "network", "\tNot ready to drop; output pending?" )


class NetworkController(NetworkControllerSendFunctionsExt, NetworkControllerRecvFunctionsExt):

    def __init__(self):

        NetworkControllerSendFunctionsExt.__init__(self)
        NetworkControllerRecvFunctionsExt.__init__(self)


        # Track the state (are we offline?; hosting?; joining?)
        self.status = NET_STATUS_OFFLINE

        # We'll track the necessary object here
        self.socket_controller = None


        # Keep a console object handy
        self.net_console = NetConsole()


        # Default port
        self.default_port = 8589 # Hard-coded default, overridden by preferences if applicable


    # Get network controller status (offline, server, client)
    def get_status(self):

        return self.status


    # Set network controller status
    def set_status(self, status):

        self.status = status


    # Get default port
    def get_default_port(self):

        # Return
        return self.default_port


    # Set default port
    def set_default_port(self, port):

        # Update
        self.default_port = port


    def start_server(self, port = None):

        self.status = NET_STATUS_SERVER

        try:

            self.socket_controller = SocketServer(port = port)

            return True

        except:

            return False


    def stop_server(self):

        if (self.socket_controller):

            self.socket_controller.announce_shutdown()



    def start_clientUnsafe(self, host = "localhost", port = None):

        self.status = NET_STATUS_CLIENT

        self.socket_controller = SocketClient(host = host, port = port)

        return True


    def start_client(self, host = "localhost", port = None):

        self.status = NET_STATUS_CLIENT

        #self.socket_controller = SocketClient(host = host, port = port)
        #return False

        try:

            self.socket_controller = SocketClient(host = host, port = port)

            return True

        except:

            return False


    def is_active(self):

        if (self.socket_controller):

            return self.socket_controller.status == STATUS_ACTIVE

        else:
            return False


    def lock(self):

        if (self.socket_controller):

            self.socket_controller.lock()


    def unlock(self):

        if (self.socket_controller):

            self.socket_controller.unlock()


    # Is the network controller locally locked?
    # When it is, the game should not allow the local player to respond to gameplay input.
    def is_local_locked(self):

        if (self.socket_controller):

            if (self.socket_controller.status == STATUS_ACTIVE):

                return self.socket_controller.is_local_locked()

            else:

                return False

        else:

            return False


    # Is the network controller globally locked?
    # When it is, the game should not process any gameplay logic at all.
    def is_global_locked(self):

        if (self.socket_controller):

            if (self.socket_controller.status == STATUS_ACTIVE):

                return self.socket_controller.is_global_locked()

            else:

                return False

        else:

            return False


    # Get a handle to the NetConsole
    def get_net_console(self):

        # Return
        return self.net_console


    # Build data string by for a given command type
    def build_message_by_command_type(self, command_type, universe, actor, params):

        if (command_type == NET_MSG_UNLOCK):

            return "%d;%s" % (command_type, params["key"])

        elif (command_type == NET_MSG_PING):

            return "%d;%s" % (command_type, params["timestamp"])

        elif (command_type == NET_MSG_PONG):

            return "%d;%s" % (command_type, params["timestamp"])

        elif (command_type == NET_MSG_ENTITY_START_MOTION):

            return "%d;%s;%d;%d;%d" % (command_type, actor.name, actor.get_x(), actor.get_y(), params["direction"])

        elif (command_type == NET_MSG_ENTITY_STOP_MOTION):

            return "%d;%s;%d;%d" % (command_type, actor.name, actor.get_x(), actor.get_y())

        elif (command_type == NET_MSG_SYNC_ENEMY_AI):

            return "%d;%s" % (command_type, params["xml"])

        elif (command_type == NET_MSG_SYNC_PLAYER_BY_ID):

            return "%d;%s" % (command_type, params["xml"])

        elif (command_type == NET_MSG_CALL_SCRIPT):

            return "%d;<packet><key>%s</key><script>%s</script><map-state>%s</map-state></packet>" % (command_type, params["key"], params["script"], params["map-state"])

        elif (command_type == NET_REQ_CALL_SCRIPT):

            return "%d;%s;%s" % (command_type, params["key"], params["script"])

        elif (command_type == NET_REQ_CONFIRM_DIG_TILE):

            return "%d;%s;%s;%d;%d;%d;%d;%d" % (command_type, params["key"], actor.name, params["perfect-x"], actor.get_y(), params["direction"], params["tx"], params["ty"])

        elif (command_type == NET_MSG_ENTITY_DIG):

            return "%d;%s;%d;%d;%d;%d;%d" % (command_type, actor.name, actor.get_x(), actor.get_y(), params["direction"], params["tx"], params["ty"])

        elif (command_type == NET_MSG_INVALIDATE_DIG):

            return "%d;%d;%d" % (command_type, params["tx"], params["ty"])

        # command_type; gold.name; gold.x; gold.y; gold.status
        elif (command_type == NET_MSG_SYNC_ONE_GOLD):

            return "%d;%s;%d;%d;%d" % (command_type, actor.name, actor.get_x(), actor.get_y(), actor.status)

        # command type; key; bomb.name; bomb.x; bomb.y; bomb.radius. bomb.remote
        elif (command_type == NET_REQ_VALIDATE_BOMB):

            return "%d;%s;%s;%d;%d;%d;%d" % (command_type, params["key"], actor.name, actor.get_x(), actor.get_y(), actor.get_radius(), actor.is_remote())

        # command type; key; bomb.name
        elif (command_type == NET_MSG_VALIDATE_BOMB_OK):

            return "%d;%s;%s" % (command_type, params["key"], params["name"])

        # command type; key; bomb.name
        elif (command_type == NET_MSG_VALIDATE_BOMB_UNAUTHORIZED):

            return "%d;%s;%s" % (command_type, params["key"], params["name"])

        # command type; key; bomb.x; bomb.y; bomb.y; bomb.radius; bomb.remote
        elif (command_type == NET_MSG_CREATE_BOMB):

            return "%d;%s;%d;%d;%d;%d" % (command_type, params["key"], actor.get_x(), actor.get_y(), actor.get_radius(), actor.is_remote())

        # command type; key; entity id
        elif (command_type == NET_MSG_ENTITY_DIE):

            return "%d;%s;%s" % (command_type, params["key"], actor.name)

        # command type; key; entity id; respawn.id
        elif (command_type == NET_MSG_ENTITY_RESPAWN):

            return "%d;%s;%s;%s" % (command_type, params["key"], actor.name, params["respawn.id"])

        # command type; key; player id; online status; ready status; nick
        elif (command_type == NET_MSG_SYNC_PLAYER):

            return "%d;%s;%d;%s;%s;%s;%s" % (command_type, params["key"], params["player-id"], params["online-status"], params["ready-status"], params["nick"], params["avatar-data"])

        # command type; key; xml
        elif (command_type == NET_MSG_SYNC_ALL_PLAYERS):

            return "%d;%s;%s" % (command_type, params["key"], params["xml"])

        # command type; key
        elif (command_type == NET_MSG_VOTE_TO_SKIP):

            return "%d;%s" % (command_type, params["key"])

        # command type; key; map name
        elif (command_type == NET_MSG_TRANSITION_TO_MAP):

            return "%d;%s;%s" % (command_type, params["key"], params["map"])

        # command type; chat message
        elif (command_type == NET_MSG_CHAT):

            return "%d;%s" % (command_type, params["msg"])

        # command type; key
        elif (command_type == NET_MSG_BEGIN_GAME):

            return "%d;%s" % (command_type, params["key"])

        # command type; key; next map name
        elif (command_type == NET_MSG_LEVEL_COMPLETE):

            return "%d;%s;%s" % (command_type, params["key"], params["next-map-name"])

        # command type; key; next (i.e. current, reload) map name
        elif (command_type == NET_MSG_LEVEL_FAILED):

            return "%d;%s;%s" % (command_type, params["key"], params["next-map-name"])

        # command type; key
        elif (command_type == NET_MSG_SERVER_DISCONNECTING):

            return "%d;%s" % (command_type, params["key"])

        # command type; key; client id
        elif (command_type == NET_MSG_CLIENT_DISCONNECTING):

            return "%d;%s;%s" % (command_type, params["key"], params["player-id"])

        # command type
        elif (command_type == NET_MSG_CONFIRM_DISCONNECT):

            return "%d" % command_type

        # avatar data for a given player id
        elif (command_type == NET_MSG_AVATAR_DATA):

            player_id = int( params["player-id"] )

            return "%d;%d;%s" % ( command_type, player_id, self.get_session_variable("net.player%d.avatar.colors" % player_id).get_value() )


    def broadcast(self, data):

        if (self.socket_controller):

            if (self.status == NET_STATUS_SERVER):

                self.socket_controller.broadcast(data)

            elif (self.status == NET_STATUS_CLIENT):

                self.socket_controller.broadcast(data)


    def mail(self, conn, data):

        if (self.socket_controller):

            if (self.status == NET_STATUS_SERVER):

                self.socket_controller.mail(conn, data)

            elif (self.status == NET_STATUS_CLIENT):

                #print "Client does not support this method."
                self.socket_controller.broadcast(data)


    def send_registered_message(self, conn, data, options):

        if (self.socket_controller):

            if (self.status == NET_STATUS_SERVER):

                self.socket_controller.send_registered_message(conn, data, options)

            elif (self.status == NET_STATUS_CLIENT):

                self.socket_controller.send_registered_message(data, options)


    def send_unregistered_message(self, conn, data):

        if (self.socket_controller):

            if (self.status == NET_STATUS_SERVER):

                self.socket_controller.send_unregistered_message(conn, data)

            elif (self.status == NET_STATUS_CLIENT):

                self.socket_controller.send_unregistered_message(data)


    # Server - Ignore a given connection
    # Client - n/a
    def ignore(self, conn):

        if (self.socket_controller):

            if (self.status == NET_STATUS_SERVER):

                self.socket_controller.ignore(conn)

            elif (self.status == NET_STATUS_CLIENT):

                log( "Warning:  Client does not support .ignore method" )


    # Server - Stop ignoring a given connection
    # Client - n/a
    def attend(self, conn):

        if (self.socket_controller):

            if (self.status == NET_STATUS_SERVER):

                self.socket_controller.attend(conn)

            elif (self.status == NET_STATUS_CLIENT):

                log( "Warning:  Client does not support .attend method" )


    # Server - Get all active connections
    # Client - n/a
    def get_active_connections(self):

        if (self.socket_controller):

            # The server can have multiple active connections
            if (self.status == NET_STATUS_SERVER):

                return self.socket_controller.get_active_connections()

            # The client only has one active connection; we'll wrap it in a disposable list...
            elif (self.status == NET_STATUS_CLIENT):

                return [ self.socket_controller.get_connection() ]

            else:

                return []

        else:

            return []


    def reply_to_server(self, data):

        if (self.socket_controller):

            if (self.status == NET_STATUS_SERVER):

                log( "Server does not support this function." )

            elif (self.status == NET_STATUS_CLIENT):

                self.socket_controller.reply_to_server(data)


    # Alias
    def send_to_server(self, data):

        self.reply_to_server(data)


    # Set ping data hash for a given player id
    def set_ping_data_by_player_id(self, player_id, h):

        if (self.socket_controller):

            if (self.status == NET_STATUS_SERVER):

                self.socket_controller.set_ping_data_by_player_id(player_id, h)


    # Get ping data hash for a given player id
    def get_ping_data_by_player_id(self, player_id):

        if (self.socket_controller):

            if (self.status == NET_STATUS_SERVER):

                return self.socket_controller.get_ping_data_by_player_id(player_id)


    def get_player_ids(self, shunned_ids = []):

        if (self.socket_controller):

            if (self.status == NET_STATUS_SERVER):

                return self.socket_controller.get_player_ids(shunned_ids)


    def get_connected_player_ids(self, shunned_ids = []):

        if (self.socket_controller):

            if (self.status == NET_STATUS_SERVER):

                return self.socket_controller.get_player_ids(shunned_ids)

            elif (self.status == NET_STATUS_CLIENT):

                return [1] # Only the server


    def get_connection_by_player_id(self, player_id):

        if (self.socket_controller):

            if (self.status == NET_STATUS_SERVER):

                return self.socket_controller.get_connection_by_player_id(player_id)

            elif (self.status == NET_STATUS_CLIENT):

                return self.socket_controller.get_connection()


    def get_player_id_by_connection(self, conn):

        if (self.socket_controller):

            if (self.status == NET_STATUS_SERVER):

                return self.socket_controller.get_player_id_by_connection(conn)

            elif (self.status == NET_STATUS_CLIENT):

                return -1


    def validate_nick(self, nick):

        # Length check
        if ( ( len(nick) < NICK_LENGTH_MINIMUM ) or ( len(nick) > NICK_LENGTH_MAXIMUM ) ):

            return NICK_ERROR_LENGTH

        # Alphanumeric only
        else:

            # Check with regex for any non-alphanumeric character; a valid nick will return no result.
            validated = ( re.search("[^a-zA-Z0-9]", nick) == None)


            if (validated):

                return NICK_OK

            else:

                return NICK_ERROR_INVALID


    def get_next_command(self):

        if (self.socket_controller):

            return self.socket_controller.get_next_command()

        else:

            return None


    def finish_connection(self, conn = None):

        if (self.socket_controller):

            if ( self.get_status() == NET_STATUS_SERVER ):

                self.socket_controller.finish_connection(conn)

            elif ( self.get_status() == NET_STATUS_CLIENT ):

                self.socket_controller.finish_connection()


    def disconnect(self):

        if (self.socket_controller):

            if ( self.get_status() == NET_STATUS_SERVER ):

                self.socket_controller.disconnect()

            elif ( self.get_status() == NET_STATUS_CLIENT ):

                self.socket_controller.disconnect()


    def web_update_player_count(self, control_center, universe):

        if (self.socket_controller):

            if ( self.get_status() == NET_STATUS_SERVER ):

                self.socket_controller.web_update_player_count(control_center, universe)


    def web_update_current_level(self, control_center, universe):

        if (self.socket_controller):

            if ( self.get_status() == NET_STATUS_SERVER ):

                self.socket_controller.web_update_current_level(control_center, universe)


    def process(self, control_center, universe):

        if (self.socket_controller):

            if (self.status == NET_STATUS_SERVER):

                self.socket_controller.process(control_center, universe)

            elif (self.status == NET_STATUS_CLIENT):

                self.socket_controller.process(control_center, universe)


