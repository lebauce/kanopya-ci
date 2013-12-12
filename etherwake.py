#!/usr/bin/env python

import xmlrpclib
import optparse
import sys

if __name__ == '__main__':

    usage = '%prog [--url http://host:port/] -i iface <mac_address>'

    parser = optparse.OptionParser(usage=usage)
    parser.add_option('-i', action='store', dest='iface')
    parser.add_option('--url', action='store', dest='url',
                      default='http://192.168.2.4:8000/')

    options, args = parser.parse_args()

    if not len(args) or options.iface is None:
        parser.print_help()
        sys.exit(1)

    mac = args[0]

    proxy = xmlrpclib.ServerProxy(options.url)
    proxy.wakeup(options.iface, mac)
