"""
# File notes:  I don't see any file in this project
#   that uses this apparently obselete file, but I'm
#   leaving it in place just in case.
"""

import sys
import httplib

from code.tools.xml import XMLParser
from code.utils.common import coalesce, get_flag_value

#from utils import log
def log(s):
    #print s
    return


def download_webpage(str_url):

    host = coalesce( get_flag_value("http_host", XMLParser()), "www.mashupgames.com" )

    h = httplib.HTTP(host)

    h.putrequest("GET", str_url)
    h.putheader("Host", host)
    h.putheader("user-agent", "Errr0 Level Downloader") # See, this is from a really old project...
    h.endheaders()

    errcode, errmsg, headers = h.getreply()

    return h.file.read()

def post_multipart(host, selector, fields, files):
    """
    Post fields and files to an http host as multipart/form-data.
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return the server's response page.
    """
    (content_type, body) = encode_multipart_formdata(fields, files)

    #print "<<<%s>>>\n\n" % body
    #sys.exit()

    errcode = 0

    try:
        h = httplib.HTTP(host)
        h.putrequest('POST', selector)
        h.putheader('Host', host)
        h.putheader('Content-Type', content_type)
        h.putheader('Content-Length', str(len(body)))
        h.putheader('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')
        h.putheader('Origin', 'https://translate.google.com')
        h.putheader('User-Agent', 'Mozilla/5.0 (X11; Linux i686 (x86_64)) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.143 Safari/537.36')
        h.endheaders()

        h.send(body)

        errcode, errmsg, headers = h.getreply()

        return h.file.read()

    except:
        log( "Level upload failed" )
        errcode = 0

        return "#fail"

def encode_multipart_formdata(fields, files):
    """
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return (content_type, body) ready for httplib.HTTP instance
    """
    BOUNDARY = '----WebKitFormBoundaryNza5QttbWzyJGJaj'
    CRLF = '\r\n'
    L = []
    for (key, value) in fields:
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"' % key)
        L.append('')
        L.append(value)
    for (key, filename, value) in files:
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
        L.append('Content-Type: %s' % "text/plain")
        L.append('')
        L.append(value)
    L.append('--' + BOUNDARY + '--')
    L.append('')
    body = CRLF.join(L)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return (content_type, body)
