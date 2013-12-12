import os
import socket
import sys
import traceback
import time
import paramiko
import string
import re
import logging


logger = logging.getLogger(__name__)


class ProcurveSSHClient(object):
    def __init__(self, hostname, port, username, password):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.load_system_host_keys()
            client.connect(hostname, port, username, password)
            self.client = client

            self.chan = self.client.invoke_shell()
            self.chan.setblocking(0)

            # wait the banner, send a key to continue and wait the prompt
            logger.debug('wait for banner')
            self.wait_for_text('Press any key to continue')
            logger.debug('send key to continue')
            self.send_data(' ')
            logger.debug('wait for prompt')
            self.wait_for_text('ProCurve-Switch#')

            # disable paging
            logger.debug('send no page')
            self.send_data('no page\n')
            logger.debug('wait for prompt')
            self.wait_for_text('ProCurve-Switch#')

        except Exception as e:
            print '*** Caught exception: %s: %s' % (e.__class__, e)
            traceback.print_exc()

    def wait_for_text(self, text):
        data = ''
        text = text.replace('(', '\(')
        text = text.replace(')', '\)')
        while True:
            if self.chan.recv_ready():
                data += self.chan.recv(1024)
                if re.search(text, data.split('\n')[-1]):
                    break
            time.sleep(0.2)
        return data

    def send_data(self, data):
        while True:
            if self.chan.send_ready():
                self.chan.send(data)
                break

            time.sleep(0.2)

    def set_untagged_port(self, port, vlan):
        # enter config context
        logger.debug('send config')
        self.send_data('config\n')
        logger.debug('wait for config prompt')
        self.wait_for_text('ProCurve-Switch(config)#')
        # enter specific vlan context
        logger.debug('send vlan nb')
        self.send_data('vlan {0}\n'.format(vlan))
        logger.debug('wait for vlan prompt')
        self.wait_for_text('ProCurve-Switch(vlan-{0})#'.format(vlan))
        # set the untagged port
        logger.debug('send unttaged command')
        self.send_data('untagged {0}\n'.format(port))
        logger.debug('wait for vlan prompt')
        self.wait_for_text('ProCurve-Switch(vlan-{0})#'.format(vlan))
        # return to manager context
        logger.debug('send end')
        self.send_data('end\n')
        logger.debug('wait for prompt')
        self.wait_for_text('ProCurve-Switch#')

    def __del__(self):
        try:
            self.chan.close()
            self.client.close()
        except:
            pass

    def logout(self, save=True):
        self.send_data('logout\n')
        data = self.wait_for_text('Do you want to log out [y/n]?')
        if re.search('Do you want to save current configuration [y/n]?',
                     data.split('\n')[-1]):
            self.send_data('y')

        self.chan.close()
        self.client.close()


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)
    switch = ProcurveSSHClient('procurve-switch', 22, 'manager', 'manager')
    switch.set_untagged_port(13, 11)
