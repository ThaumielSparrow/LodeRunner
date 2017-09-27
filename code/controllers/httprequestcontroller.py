import os
import sys

import socket
import select

import urllib

import zipfile

import Queue

from code.tools.xml import XMLParser
from code.utils.common import log, log2, logn, coalesce, ensure_path_exists, get_flag_value

from code.constants.states import STATUS_ACTIVE, STATUS_INACTIVE


# This request object sends out a web request and processes it.
class HttpRequest:

    def __init__(self, host = "localhost", port = 10000, url = "/", params = {}, tracked = True, binary = False, savepath = None):

        self.status = STATUS_ACTIVE


        # Will the request controller hold on to the results of this request, allowing us to react to it in code,
        # or is this a one-way message to which we don't care about the response?
        self.tracked = tracked


        # We can (optionally) configure the request to save to disk when it finishes
        self.savepath = savepath

        # Maybe we'll want to save it as a binary file?
        self.binary = binary


        # As we download, we'll track how many bytes we've downloaded
        self.bytes_downloaded = 0


        # Optionally, we can set attributes on a request
        self.attributes = {}


        # Scope
        self.socket = None

        # Try to set up the socket.
        # This may fail if the user has no connection, etc.
        try:

            # Set up a "client" socket that will send / receive the HTTP request
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # Connect to the server
            self.socket.connect( (host, port) )

        # If the socket connect attempt fails, return (abort)
        except:

            # Connection failed
            self.socket = None

            # Abort
            return None


        self.inputs = [self.socket]

        self.outputs = []

        self.output_queue = Queue.Queue()


        # We'll track whatever headers we receive in response
        self.response_headers = None

        self.response_body = None


        self.buffer = ""

        self.working_buffer = ""


        path = url

        if ( len(params) > 0 ):

            path += "?"

            path += urllib.urlencode(params)

            #for key in params:
            #    path += "%s=%s&" % (key, params[key])

            # Strip trailing &
            #path = path[0: len(path) - 1]


        self.broadcast("GET %s HTTP/1.1\r\nHost: %s\r\n\r\n" % (path, host))

        log( "HttpRequest created" )


    # Set attributes using a hash
    def set_attributes(self, h):

        # Loop attribute keys
        for key in h:

            # Save attribute
            self.attributes[key] = h[key]


        # For chaining
        return self


    # Get a given attribute by key
    def get_attribute(self, key):

        # Validate
        if (key in self.attributes):

            # Return
            return self.attributes[key]


        # Not found
        return None


    def broadcast(self, data):

        log( "Sending Request:  %s" % data )

        self.output_queue.put(data)

        if (not (self.socket in self.outputs)):

            self.outputs.append(self.socket)


    # Check how many bytes we have downloaded so far
    def get_bytes_downloaded(self):

        return self.bytes_downloaded


    # Check to see if we successfully created a request
    def is_created(self):

        # Check for socket existence
        return ( self.socket != None )


    def is_completed(self):

        return (self.status == STATUS_INACTIVE)


    # Save the results of the request to disk.  We provide the save path when we create the request.
    def save_to_disk(self):

        # Validate that we have a save path
        if (self.savepath):

            # If this is an "archive" file, then we want to unzip the response to the savepath
            if ( self.get_attribute("type") == "archive" ):

                # Define temporary filename
                filename = os.path.join("tmp", "download.zip")

                # Write data to file
                f = open(filename, "wb")
                f.write( self.get_response() ) # Response content is the zipfile (data)
                f.close()


                # Read for unzipping
                z = zipfile.ZipFile(filename, "r")

                # Extract all files
                z.extractall(self.savepath)

                """
                # Loop file objects within zip
                for f in z.infolist():

                    # Get the full path of the file from within the zip.
                    # According to docs, this will implicitly use the correct os.sep (e.g. / on linux, \ on [redacted])
                    path = f.filename
                    logn( "http zip", "Zip path:  %s\n" % path )


                    # Read data
                    data = z.read(f.filename)

                    # Write data to appropriate location
                    f2 = open(
                        os.path.join(self.savepath, path),
                        "w"
                    )
                    f2.write(data)
                    f2.close()
                """

            # Default behavior, save to disk
            else:

                # Take the directory component of the save path; ensure that it exists.
                ensure_path_exists( os.path.dirname(self.savepath) )

                # Now open the file for writing, perhaps in binary mode...
                f = open( self.savepath, "wb" if (self.binary) else "w" )

                # Write the request response into the file
                f.write( self.get_response() )

                # Close file
                f.close()


            # Success
            return True

        else:

            log( "Warning:  Save path not defined for web request!" )
            return False


    def received_headers(self):

        return ( self.response_headers != None )


    def received_body(self):

        return ( self.response_body != None )


    def get_header(self, key):

        if (key in self.response_headers):

            return self.response_headers[key]

        elif ( key.lower() in self.response_headers ):

            return self.response_headers[ key.lower() ]

        else:

            return ""


    # Process a buffer to extract header and body data
    def process_buffer_and_return_buffer(self, buffer):

        # Do we still need to look for headers?
        if ( not self.received_headers() ):

            # Try to find 'em
            delimiter = "\r\n\r\n"

            # Check
            pos = buffer.find(delimiter)

            # Ready?
            if (pos >= 0):

                # Set up headers hash
                self.response_headers = {}

                # Loop through each option...
                lines = buffer[0 : pos].strip().split("\r\n")

                # First line indicates response code; ignore for now.
                lines.pop(0)

                # All other lines contain key/value header data
                for line in lines:

                    # key / value
                    (key, value) = line.split(":", 1)

                    # Get rid of annoying whitespace
                    self.response_headers[ key.strip() ] = value.strip()


                log( "Returning '%s'" % buffer[ (pos + len(delimiter)) : len(buffer) ] )
                # Return buffer without header data
                return buffer[ (pos + len(delimiter)) : len(buffer) ]


            # Haven't received all of the headers yet
            else:

                # We'll try this again soon
                return buffer


        # Have we finalized the response body yet?
        elif ( not self.received_body() ):

            # Is this a chunked response?
            if ( self.get_header("Transfer-Encoding") == "chunked" ):

                # Try to assemble the current buffer into response body data
                remainder = self.assemble_chunks_and_return_remainder(buffer)


                # If we get no remainder, that indicates we have received the full response
                if (remainder == None):

                    # Set response body
                    self.response_body = self.working_buffer

                    log( "Final response body:\n%s" % self.response_body )

                    # Return an empty buffer
                    return ""

                # We have not received the entirety of every chunk
                else:

                    # Return the available unprocessed buffer data
                    return remainder

            # If not, then we'll check for a content-length
            else:

                # Try...
                value = self.get_header("Content-Length")

                # Validate
                if ( not (value in ("", "0")) ):

                    # Convert
                    content_length = int(value)

                    # Do we have the entire body streamed?
                    if ( len(buffer) >= content_length ):

                        # Set response body
                        self.response_body = buffer

                        # Return empty buffer
                        return ""

                    # We're not done yet...
                    else:

                        # Try again
                        return buffer


                else:

                    return buffer


        return ""


    # Try to retrieve the response body
    def get_response(self):

        # Ready to go?
        if ( self.received_body() ):

            # Here you are...
            return self.response_body

        # Not yet, sorry
        else:

            # Indicate that we aren't ready...
            return None


    # When dealing with chunked responses, we'll need to iteratively compile them into a final response body
    def assemble_chunks_and_return_remainder(self, buffer):

        # See if we can find a chunk length
        looping = ( buffer.find("\r\n") > 0 )

        while (looping):

            # Split the chunk length away from the remainder of the provided buffer data
            (chunk_length, remainder) = buffer.split("\r\n", 1)

            # Get the chunk length, converted from hexidecimal to decimal
            size = int(chunk_length, 16)


            # If the chunk has a length of 0, we've received the entirety of the response
            if (size == 0):

                # Return None to indicate that we've fully compiled the response body
                return None


            # Otherwise, check to see if we've received the entirety of this individual chunk
            elif ( len(remainder) >= size ):

                # Get the chunk data itself and, ultimately, clear this entire chunk out of the provided buffer
                chunk_data = remainder[0 : size]

                # Update provided buffer (remove current chunk)
                buffer = remainder[size : len(buffer)].lstrip()


                # Update working buffer with current chunk data
                self.working_buffer += chunk_data

                # Move on to the next chunk, if possible...
                looping = ( buffer.find("\r\n") > 0 )


                if (not looping):

                    # Return remaining buffer data
                    return buffer


            # We haven't received all of this individual chunk yet
            else:

                # Return remaining buffer data
                return buffer


    # Manually end a request, even if it isn't finished
    def end(self):

        # If we are still active, let's close the socket
        if (self.status == STATUS_ACTIVE):

            # Done
            self.socket.close()


    def process(self, timeout = 0.001):

        if ( not self.is_created() ):
            return None


        if ( ( self.status == STATUS_ACTIVE ) and ( not self.is_completed() ) ):#while ( not self.received_body() ):

            (readable, writable, exceptional) = select.select(self.inputs, self.outputs, self.inputs, timeout)

            # Timeout?  Oh well...
            if ( not (readable or writable or exceptional) ):

                pass

            # We can read or write something!  (Or we have an error...)
            else:

                # See if our client socket got a response from the server!
                for s in readable:

                    data = s.recv(1024)

                    log( "Received %d bytes" % len(data) )

                    # No data means we lost connection to the server
                    if (not data):

                        # (?)
                        #self.response_body += self.buffer

                        self.socket.close()
                        log2( "Connection terminated." )

                        #log2( "Buffer contents:  '%s'" % self.buffer )

                        if (self.response_body == None):
                            self.response_body = self.buffer

                        else:
                            self.response_body += self.buffer

                        #log2( "\nResult:\n\n%s" % self.get_response() )

                        self.status = STATUS_INACTIVE

                        return self.get_response()

                    else:

                        # Add data to working buffer
                        self.buffer += data

                        # Track the amount of data we've downloaded
                        self.bytes_downloaded += len(data)


                        #log2( "New buffer data:  '%s'" % data )


                        had_headers = self.received_headers()

                        self.buffer = self.process_buffer_and_return_buffer(self.buffer)
                        #log2( "Current buffer data:\n%s" % self.buffer )

                        if ( (not had_headers) and ( self.received_headers() )):

                            #log2( "Headers processed.  Remaining data:\n%s" % self.buffer )

                            self.buffer = self.process_buffer_and_return_buffer(self.buffer)

                        if ( self.received_body() ):

                            self.socket.close()
                            self.status = STATUS_INACTIVE

                            #log2( "Detected end of response body.  Current response data:\n%s" % self.get_response() )

                            # Return the response
                            return self.get_response()


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
                        s.send(data)

                        #log( "Sending:  ", data )


        if ( not self.received_body() ):

            return None


# A wrapper that houses a series of batched requests, spawning some given number of simultaneous requests, moving on
# to the next (pending) requests as each active request finishes.
class HttpRequestBatch:

    def __init__(self, host, port, items, max_requests = 1):

        # Track the host we'll use for each item in this batch
        self.host = host

        # Port, too!
        self.port = port


        # A list of batch items.  Each item contains the path to save to, the url to download from, and possibly other information.  (?)
        self.items = items

        # Define total bytes possible
        self.bytes_possible = 0


        # Ensure each item has all necessary default attributes
        i = 0
        while ( i < len(self.items) ):

            # State defaults, update given attributes
            defaults = {
                "path": None,
                "url": None,
                "bytes": 0,
                "binary": False,
                "type": None
            }

            # Back and forth...
            defaults.update(self.items[i])
            self.items[i] = defaults

            # Each item requires a url
            if ( self.items[i]["url"] == None ):

                # Can't download this
                self.items.pop(i)

            else:

                # Track running total of bytes possible
                self.bytes_possible += self.items[i]["bytes"]

                i += 1


        # At the start, we'll mark down how many files this batch contains
        self.file_count = len(self.items)


        # How many requests should we download at any given time?
        self.max_requests = max_requests


        # Each time we create a web request, we'll track it in this list of active requests.
        self.active_requests = []


        # Each time a download completes, we'll add its final byte length to the number of bytes downloaded.
        # When querying this statistic, we'll have to add in the bytes-in-progress of each active request, though.
        self.bytes_downloaded = 0

        # We'll keep a tally of how many files we have downloaded
        self.files_downloaded = 0


    # Check to see if the batch has yet finished
    def is_completed(self):

        # If we have no pending item and no active request, then we have completed the batch
        return ( ( len(self.items) == 0 ) and ( len(self.active_requests) == 0 ) )


    # Check to see how much data we have so far downloaded
    def get_bytes_downloaded(self):

        # The bytes download must include the bytes-in-progress (so to speak) of each active web request.
        return ( self.bytes_downloaded + sum( o.get_bytes_downloaded() for o in self.active_requests ) )


    # Check how many bytes exist in this batch, overall
    def get_bytes_possible(self):

        # Return
        return self.bytes_possible


    # Check to see how many individual files we have downloaded
    def get_files_downloaded(self):

        return self.files_downloaded


    # Query how many files this batch will download, in total
    def get_file_count(self):

        # We saved this value when we first created the batch
        return self.file_count


    # Manually end a batch
    def end(self):

        # End any active request
        for request in self.active_requests:

            request.end()

        # Clear both pending and active lists
        while ( len(self.items) > 0 ):

            self.items.pop()

        while ( len(self.active_requests) > 0 ):

            self.active_requests.pop()


    # Process the batch
    def process(self):

        # If we have items remaining and we are not at the simultaneous request limit, we'll create some new web requests
        while ( ( len(self.items) > 0 ) and ( len(self.active_requests) < self.max_requests) ):

            # We'll just run them sequentially.  As we move to handle this next batch item, remove it from the "pending" items list.
            item = self.items.pop(0)


            logn( "http", "Now saving '%s' to '%s'\n" % (item["url"], item["path"]) )


            # Before we commit to downloading the file, let's check to see if we already have it on disk.
            # If so, why would we download it again?
            if (
                os.path.exists( item["path"] ) and
                int( os.path.getsize( item["path"] ) ) == item["bytes"]
            ):

                # Updates bytes "downloaded" counter immediately
                self.bytes_downloaded += item["bytes"]

                # Increment file counter immediately
                self.files_downloaded += 1
                logn( "http", "%s\n" % "Skipping previously downloaded %s" % item["path"] )

            # If we haven't downloaded the file (or we didn't download the entire file),
            # then we'll send a legitimate http request.
            else:

                # Create a new active request
                self.active_requests.append(
                    HttpRequest(
                        self.host,
                        self.port,
                        item["url"],
                        binary = item["binary"],
                        savepath = item["path"]
                    ).set_attributes({
                        "type": item["type"]
                    })
                )


        # Handle each active request
        i = 0
        while ( i < len(self.active_requests) ):

            # Process request
            self.active_requests[i].process(timeout = 0.001)

            # If the request has finished, flush its contents to disk and remove the request from the active list
            if ( self.active_requests[i].is_completed() ):

                # Flush it to disk; we gave it the save path when we created the request.
                self.active_requests[i].save_to_disk()

                # As the request has completed, we'll add its final bytes downloaded count to our overall progress tracker
                self.bytes_downloaded += self.active_requests[i].get_bytes_downloaded()

                # We have downloaded another file
                self.files_downloaded += 1

                # We're done with this request; we can move on to the next pending request, if/a
                self.active_requests.pop(i)

            else:

                # Loop
                i += 1


# Control http requests.
class HttpRequestController:

    def __init__(self):

        # Default host for all relative HTTP requests
        self.default_host = "www.mashupgames.com"

        # Check for http_host flag
        value = get_flag_value("http_host", XMLParser())
        if (value != None):

            # Update default host
            self.default_host = value


        # We can add new web requests by name.  For instance, we might create a request called "dlc-level-list" and use
        # that key to monitor the status of the given request.
        self.requests = {}

        # Occasionally we'll send out "batched" requests; this allows us to download a given set of files to a given
        # set of locations.  We can periodically check in on the batch to see if all of the downloads have completed.
        self.batches = {}


    # Send a GET request, specifying a given name for the request.
    def send_get_with_name(self, name, host, port, url, params = {}, tracked = True, force = False):

        # Ensure host has a value
        host = coalesce(host, self.default_host)

        # If we already have a request by the given name, we won't do anything
        # unless this is a "forced" request...
        if ( (not force) and (name in self.requests) ):

            # Return failure
            return False

        # Otherwise, let's create the request...
        else:

            # Hash by given name
            self.requests[name] = HttpRequest(host, port, url, params, tracked)


    # Grab a GET request by its name
    def get_request_by_name(self, name):

        # Validate
        if (name in self.requests):

            # Return
            return self.requests[name]

        # Could not find it
        else:
            return None


    # Download a collection of files using a given batch name.
    def download_batch_with_name(self, name, host, port, items, max_requests = 1):

        # Ensure host has a value
        host = coalesce(host, self.default_host)

        # Create a new download batch
        self.batches[name] = HttpRequestBatch(host, port, items, max_requests)


    # Check to see if a given response is ready.  This doesn't actually return or modify data availability in any way.
    def is_named_request_ready(self, name):

        # Validate
        if (name in self.requests):

            # Let's just see if it's ready...
            return self.requests[name].is_completed()

        else:
            log( "Warning:  HTTP request by name '%s' does not exist!" % name )
            return False


    # Check to see if a given response exists.
    def does_request_exist(self, name):

        # Simple check
        return (name in self.requests)


    # Get a reference to a given request batch, by name
    def get_batch_by_name(self, name):

        # Validate
        if (name in self.batches):

            # Return batch
            return self.batches[name]

        else:

            log( "Warning:  Batch by name '%s' does not exist!" % name )
            return None


    # Peeking at the response for a given named request allows us to look at the data
    # without removing the request from the hash.
    def peek_response_by_request_name(self, name):

        # Validate
        if (name in self.requests):

            # Is it complete?
            if ( self.requests[name].is_completed() ):

                # Return the response, keeping the request object on record...
                return self.requests[name].get_response()

            else:

                return None

        else:
            log( "Warning:  HTTP request by name '%s' does not exist!" % name )
            return None


    # Try to get the content results of a given request.  If we have not finished the request, return nothing.
    # If we have finished the request, return the data and remove the given request (by name) from the tracker hash.
    def fetch_response_by_request_name(self, name):

        # Validate
        if (name in self.requests):

            # Have we completed the request?
            if ( self.requests[name].is_completed() ):

                # Remove it from the tracker
                request = self.requests.pop(name)

                # Return the content response
                return request.get_response()

            # Nope, not yet!
            else:

                # Return nothing
                return None

        else:
            log( "Warning:  HTTP request by name '%s' does not exist!" % name )
            return None


    # Manually clear a given request, by name
    def end_request_by_name(self, name):

        # Validate
        if (name in self.requests):

            # Make sure to clean up if necessary
            self.requests[name].end()

            # Remove the request
            self.requests.pop(name)


    # Manually clear a given batch, by name
    def end_batch_by_name(self, name):

        # Validate
        if (name in self.batches):

            # Make sure to clean up if necessary
            self.batches[name].end()

            # Remove the batch
            self.batches.pop(name)


    # Process any active http request
    def process(self):

        # Grab keys
        keys = self.requests.keys()

        # Loop all
        i = 0
        while ( i < len(keys) ):

            # Convenience
            name = keys[i]

            # Process the request.  Does nothing if it's already done.
            self.requests[name].process(timeout = 0.001)
            log( "Processing %s . . .\n" % name )

            # If the request does not use tracking, then we'll remove it when it's finished...
            if (not self.requests[name].tracked):

                # Is it done?
                if ( self.requests[name].is_completed() ):

                    # Let's clear it from the list.  This is why we're doing the i += 1 stuff; I want to remove
                    # it from the hash immediately here.
                    self.requests.pop(name)

            # Always increment loop counter; we're on to the next key, even if we removed the previous (untrackeD) request from the actual hash.
            i += 1


        # Get batch keys
        keys = self.batches.keys()

        # Process each batch key
        i = 0
        while ( i < len(keys) ):

            # Convenience
            batch = self.batches[ keys[i] ]

            # Process the batch
            batch.process()

            # Loop
            i += 1
