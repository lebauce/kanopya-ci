#!/usr/bin/env python

from persistence import CIDB
from shell import LocalShell
from vboxmanage import VBoxManage
from SimpleXMLRPCServer import SimpleXMLRPCServer

import daemon
from daemon.pidlockfile import PIDLockFile

import logging
logger = logging.getLogger(__name__)


class WolproxyServer(SimpleXMLRPCServer):
    def __init__(self, host_port):
        SimpleXMLRPCServer.__init__(self, host_port)
        self.vbox = VBoxManage(LocalShell())
        self.register_introspection_functions()
        self.register_function(self.wakeup, 'wakeup')

        self.stdin_path = '/dev/stdin'
        self.stdout_path = '/dev/stdout'
        self.stderr_path = '/dev/stderr'

        self.pidfile_path =  '/var/lib/jenkins/wolproxy.pid'
        self.pidfile_timeout = 5

    def wakeup(self, iface, mac):
        logger.debug("iface: %s, mac: %s", iface, mac)
        with CIDB() as db:
            vmname = db.get_vmname_from_mac(mac)

        if vmname is not None:
            logger.info("start vm %s", vmname)
            self.vbox.start_vm(vmname)
        else:
            logger.error("no vm found with mac %s", mac)

        return True

    def run(self):
        try:
            self.serve_forever()
        except Exception, e:
            logger.info(e)


if __name__ == '__main__':

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler = logging.FileHandler("/var/lib/jenkins/wolproxy.log")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    listen = ('0.0.0.0', 8000)
    logger.info("wolproxy server listening on %s:%s", listen[0], listen[1])

    with daemon.DaemonContext(detach_process = True,
                              files_preserve = [handler.stream],
                              pidfile = PIDLockFile('/var/lib/jenkins/wolproxy.pid')):
        server = WolproxyServer(listen)
        server.run()
