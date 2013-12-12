# -*- coding: utf-8 -*-

import os
import logging
import shutil
import json
import subprocess
from string import Template


logger = logging.getLogger(__name__)

VAGRANTFILE_TEMPLATE = """
# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant::Config.run do |config|

  # Every Vagrant virtual environment requires a box to build off of.
  config.vm.box = "${box}"
  config.vm.name = "${vmname}"
  # Boot with a GUI so you can see the screen. (Default is headless)
  # config.vm.boot_mode = :gui

  # MAC address of the NAT interface on the VM
  config.vm.base_mac = "080027B564F0"

  config.vm.customize ["modifyvm", :id, "--audio", "none"]
  config.vm.customize ["modifyvm", :id, "--usb",  "off"]
  config.vm.customize ["modifyvm", :id, "--boot1", "disk"]
  config.vm.customize ["modifyvm", :id, "--biosbootmenu", "disabled"]
  config.vm.customize ["modifyvm", :id, "--cpuhotplug", "off"]
  config.vm.customize ["modifyvm", :id, "--hpet", "on"]

  config.vm.customize ["modifyvm", :id, "--vrde", "on"]
  config.vm.customize ["modifyvm", :id, "--vrdeport", ${vrde_port}]

  config.vm.customize ["modifyvm", :id, "--memory", ${memory}]
  config.vm.customize ["modifyvm", :id, "--cpus", ${cpus}]

  # SSH
  config.ssh.username = "${user}"
  config.ssh.private_key_path = "/var/lib/jenkins/vagrant/id_rsa"
  config.ssh.timeout = 300
  config.ssh.max_tries = 20

  # network configuration

  config.vm.network ${network}, :adapter => 2, :mac => "${mac1}"

  # third interface always use bridge br0 to access our lan
  config.vm.network :bridged, :bridge => "br0", :adapter => 3, :mac => "${mac2}"

  # Forward a port from the guest to the host, which allows for outside
  # computers to access the VM, whereas host only networking does not.
  config.vm.forward_port 22, ${ssh_port}

  # Share an additional folder to the guest VM. The first argument is
  # an identifier, the second is the path on the guest to mount the
  # folder, and the third is the path on the host to the actual folder.
  config.vm.share_folder "v-kanopya", "/opt/kanopya", "../kanopya"
  config.vm.share_folder "v-masterimages", "/masterimages", "/var/lib/jenkins/masterimages"
  config.vm.share_folder "v-result", "/result", "../result"

end
"""


class VagrantEnvironment(object):
    def __init__(self, working_dir):
        self.vagrant_dir = os.path.join(working_dir, 'vagrant')
        self.vagrantfile = os.path.join(self.vagrant_dir, 'Vagrantfile')
        self.vm_id = None

        if not os.path.exists(self.vagrant_dir):
            logger.debug('create directory %s', self.vagrant_dir)
            os.makedirs(self.vagrant_dir)

    def initialize(self, vagrant_data):
        """ generate vagrantfile """
        logger.debug('create Vagrant file %s', self.vagrantfile)
        with open(self.vagrantfile, 'w') as vfile:
            template = Template(VAGRANTFILE_TEMPLATE)
            vfile.write(template.substitute(vagrant_data))
        os.system("cp " + self.vagrantfile + " /tmp/Vagrantfile.job")

    def clean(self):
        """ remove vagrant directory """
        shutil.rmtree(self.vagrant_dir)

    def destroy(self):
        """ try to remove virtualbox vm """
        vagrantid_file = os.path.join(self.vagrant_dir, '.vagrant')
        if os.path.exists(vagrantid_file):
            current_dir = os.getcwd()
            os.chdir(self.vagrant_dir)
            returncode = subprocess.call(['vagrant', 'destroy'])
            os.chdir(current_dir)
        else:
            returncode = subprocess.call(['vboxmanage', 'controlvm',
                                          self.vm_id, 'poweroff'])
            returncode = subprocess.call(['vboxmanage', 'unregistervm',
                                          self.vm_id, '--delete'])

    def update(self):
        """ retrieve virtualbox vm id used for this vagrant vm """
        idfile = os.path.join(self.vagrant_dir, '.vagrant')
        with open(idfile, 'r') as f:
            jsondata = json.load(f)
            self.vm_id = jsondata['active']['default']
            logger.debug('vm_id: %s', self.vm_id)

    def __repr__(self):
        value = "vagrant dir: {0}\n".format(self.vagrant_dir)
        value += "vagrantfile: {0}\n".format(self.vagrantfile)
        value += "vagrant vm id: {0}\n".format(self.vm_id)
        return value

    def command(self, command):
        """ execute a commande via vagrant ssh """
        current_dir = os.getcwd()
        os.chdir(self.vagrant_dir)
        vagrant_ssh = '/opt/vagrant/bin/vagrant ssh -c "{0}"'.format(command)
        subprocess.call(vagrant_ssh, shell=True)
        os.chdir(current_dir)


if __name__ == '__main__':

    vagrant = VagrantEnvironment('/tmp')
    data = {'box': 'debian-squeeze-amd64-last',
            'memory': 2048,
            'cpus': 2,
            'network': ':hostonly, "10.0.0.2"',
            'ssh_port': 2222,
            'vrde_port': 3333}

    vagrant.initialize(data)
