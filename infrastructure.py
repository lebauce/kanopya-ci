from vagrant import VagrantEnvironment
from vboxmanage import VBoxManage
from shell import LocalShell
from hpprocurve import ProcurveSSHClient
from deploymentsolver import DeploymentSolver
import utils

from string import Template
import subprocess
import os
import logging
import shutil
import random
import json
import time


logger = logging.getLogger(__name__)


def new_infrastructure(infra_type):
    """ factory to instanciate proper JobInfrastructure """
    infrastructure = None
    if infra_type == 'physical':
        infrastructure = PhysicalInfrastructure()
    elif infra_type == 'virtual':
        infrastructure = VirtualInfrastructure()
    else:
        infrastructure = NoInfrastructure()

    return infrastructure


class JobInfrastructure(object):
    """ base class """
    def __init__(self):
        self.job = os.environ.get('JOB_NAME')
        box = os.environ.get('BOX', 'debian-wheezy-amd64')
        user = "hedera"

        self.vagrant_data = {
            'box': box,
            'vmname': self.job,
            'memory': 4096,
            'cpus': 1,
            'network': ':hostonly, "10.0.0.2"',
            'ssh_port': 2222,
            'vrde_port': 3333,
            'user': user,
            'mac1': self._get_random_mac().replace(':', ''),
            'mac2': self._get_random_mac().replace(':', '')
        }
        self.workspace = '/var/lib/jenkins/jobs/{0}/workspace'.format(self.job)
        self.vagrantenv = VagrantEnvironment(self.workspace)

    def initialize(self, db):
        # create job data entry in db if necessary
        if not self.job in db.jobs.keys():
            db.jobs[self.job] = {'net': None,
                                 'infra': None,
                                 'ssh_port': None,
                                 'vrde_port': None,
                                 'vlan': None}

        # create result directory
        result_dir = os.path.join(self.workspace, 'result')
        shutil.rmtree(result_dir, ignore_errors=True)
        os.makedirs(result_dir)

        # Pass the environment variables inside the Vagrant VM
        env_file = os.path.join(self.vagrantenv.vagrant_dir, 'environment.sh')
        env_vars = ['MASTERIMAGE', 'GITBRANCH', 'KERNEL', 'WEBUI', 'TEST',
                    'KEEPALIVE', 'JOB_NAME', 'STOP_SERVICES', 'API_TEST_DIR']
        with open(env_file, 'w') as export:
            for var in env_vars:
                value = os.environ.get(var, '')
                line = 'export {0}="{1}"\n'.format(var, value)
                export.write(line)

        # copy some scripts...
        shutil.copy("setup_and_run", self.vagrantenv.vagrant_dir)
        shutil.copy("touch_run_and_unlock", self.vagrantenv.vagrant_dir)

    def update(self, db):
        """ retrieve information for kanopya vagrant box """
        self.vagrantenv.update()

    def get_network_conf(self, db):
        """ retrieve the net config for the current job """
        network, ip = None, None
        if db.jobs[self.job]['net'] is None:
            network, ip = db.new_network()
            logger.debug('new network/ip : %s,%s', network, ip)
            db.jobs[self.job]['net'] = (network, ip)
        else:
            network, ip = db.jobs[self.job]['net']
            logger.debug('reusing network/ip %s/%s', network, ip)

        return network, ip

    def get_ssh_port(self, db):
        """ retrieve the ssh port forwarding for the current job """
        port = None
        if db.jobs[self.job]['ssh_port'] is None:
            port = db.new_ssh_port()
            logger.debug('new ssh port : %s', port)
            db.jobs[self.job]['ssh_port'] = port
        else:
            port = db.jobs[self.job]['ssh_port']
            logger.debug('reusing ssh port %s', port)

        return port

    def get_vrde_port(self, db):
        """ retrieve the vrde port forwarding for the current job """
        port = None
        if db.jobs[self.job]['vrde_port'] is None:
            port = db.new_vrde_port()
            logger.debug('new vrde port : %s', port)
            db.jobs[self.job]['vrde_port'] = port
        else:
            port = db.jobs[self.job]['vrde_port']
            logger.debug('reusing vrde port %s', port)

        return port

    def kanopya_setup_inputs(self, net, ip):
        """
        Generate the file that contains the inputs for the Kanopya setup
        """
        tmpl = Template(open('setup.inputs.tmpl').read())
        inputs = os.path.join(self.vagrantenv.vagrant_dir, 'setup.inputs')
        with open(inputs, 'w') as f:
            f.write(tmpl.substitute({'network': net,
                                     'ip': ip,
                                     'interface': "eth1"}))

    def kanopya_register_hosts(self, hosts):
        """
        Generate the file that contains the hosts list for the
        register_hosts.pl script
        """
        shutil.copy("register_hosts.pl", self.vagrantenv.vagrant_dir)
        hostsfile = os.path.join(self.vagrantenv.vagrant_dir, 'hosts.json')
        with open(hostsfile, 'w') as f:
            json.dump(hosts, f)

    def clean(self):
        logger.debug("clean infra")
        self.vagrantenv.clean()

    def __repr__(self):
        value = str(self.vagrantenv)
        return value

    def _get_random_mac(self):
        """ generate a random virtualbox mac address """
        choice = ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
                  'A', 'B', 'C', 'D', 'E', 'F')

        mac = "08:00:27"
        for i in xrange(3):
            mac += ":{0}{1}".format(random.choice(choice),
                                    random.choice(choice))
        return mac


class NoInfrastructure(JobInfrastructure):
    def __init__(self):
        JobInfrastructure.__init__(self)

    def initialize(self, db):
        """
        NoInfrastructure initialization only need to init the vagrant
        environment with a new hostonly virtualnet
        """
        JobInfrastructure.initialize(self, db)
        network, ip = self.get_network_conf(db)
        self.vagrant_data['network'] = ':hostonly, "{0}"'.format(ip)
        self.vagrant_data['ssh_port'] = self.get_ssh_port(db)
        self.vagrant_data['vrde_port'] = self.get_vrde_port(db)
        self.vagrantenv.initialize(self.vagrant_data)
        self.kanopya_setup_inputs(network, ip)

    def clean(self, db):
        JobInfrastructure.clean(self)


class VirtualInfrastructure(JobInfrastructure):
    def __init__(self):
        JobInfrastructure.__init__(self)
        self.nbvms = int(os.environ.get('NBVMS'))
        self.vms = []
        self.vbox = VBoxManage(LocalShell())

    def initialize(self, db):
        JobInfrastructure.initialize(self, db)
        shutil.copy("etherwake.py", self.vagrantenv.vagrant_dir)

        network, ip = self.get_network_conf(db)
        sshport = self.get_ssh_port(db)
        vrdeport = self.get_vrde_port(db)

        self.vagrant_data['network'] = ':hostonly, "{0}"'.format(ip)
        self.vagrant_data['ssh_port'] = sshport
        self.vagrant_data['vrde_port'] = vrdeport
        self.vagrantenv.initialize(self.vagrant_data)

        self._create_vms()
        self.kanopya_setup_inputs(network, ip)
        self.kanopya_register_hosts(self.vms)

    def update(self, db):
        JobInfrastructure.update(self, db)
        # we set the correct hostonly iface for the precreated vms
        vboxiface = self.vbox.get_hostonly_iface_name(self.vagrantenv.vm_id)
        logger.debug("hostonly interface is %s", vboxiface)
        for vm in self.vms:
            name = vm['serial_number']
            for i, iface in enumerate(vm['ifaces']):
                logger.debug("update hostonlyadapter for iface %s on vm %s",
                             iface['name'], name)
                self.vbox.set_hostonlyadapter(name, i+1, vboxiface)

    def clean(self, db):
        JobInfrastructure.clean(self)
        self._destroy_vms()

    def _create_vms(self):
        """ create virtualbox vms for the infrastructure """
        for i in xrange(self.nbvms):
            new_vm_name = "{0}_{1}".format(self.job, i)
            ifaces = []
            for i in xrange(4):
                ifaces.append({'name': "eth{0}".format(i),
                               'mac': self._get_random_mac(),
                               'pxe': 0,
                               'adapter_type': 'hostonlyadapter',
                               'adapter_iface': 'eth0'})

            ifaces[0]['pxe'] = 1
            logger.info("create virtualbox vm {0}".format(new_vm_name))
            self.vbox.clone_vm('kanopyahost', new_vm_name, ifaces, cpus=4,
                               memory=4096)
            self.vms.append({'serial_number': new_vm_name,
                             'core': 4,
                             'ram': 4294967296,
                             'ifaces': ifaces,
                             'harddisks': [{'device': '/dev/sda',
                                            'size': '21474836480'}]})

    def _destroy_vms(self):
        """ delete virtualbox vms created for the infrastructure """
        for vm in self.vms:
            name = vm['serial_number']
            logger.info("destroy virtualbox vm %s", name)
            if name in self.vbox.list_runningvms(filter=name):
                self.vbox.poweroff_vm(name)
                time.sleep(3)
            self.vbox.delete_vm(name)

    def __repr__(self):
        value = JobInfrastructure.__repr__(self)
        value += "vms count: {0}".format(self.nbvms)
        return value


class PhysicalInfrastructure(JobInfrastructure):
    BRIDGE = 'eth1'
    SWITCH_PORT = 2

    def __init__(self):
        JobInfrastructure.__init__(self)
        self.booked_hosts = None

    def initialize(self, db):
        JobInfrastructure.initialize(self, db)

        network, ip = self.get_network_conf(db)
        sshport = self.get_ssh_port(db)
        vrdeport = self.get_vrde_port(db)
        vlan = self.get_vlan_conf(db)
        bridge = "{0}.{1}".format(self.BRIDGE, vlan)

        # determine physical hosts needed and book them
        self.booked_hosts = self._book_hosts(db)

        # apply vlan configuration
        # on the switch...
        switch = ProcurveSSHClient('procurve-switch.intranet.hederatech.com',
                                   22, 'manager', 'manager')
        for host in self.booked_hosts:
            for iface in host['ifaces']:
                if 'switch_port' not in iface.keys():
                    continue
                port = iface['switch_port']
                logger.debug("set switch port %s on vlan %s untagged",
                             port, vlan)
                switch.set_untagged_port(port, vlan)

        # on jenkins interface
        utils.create_vlan_device(self.BRIDGE, str(vlan))
        logger.debug("create vlan device on %s with vlan %s", 
                     self.BRIDGE, vlan)

        # set vagrant data
        self.vagrant_data['network'] = ':bridged, ' + \
                                       ':bridge => "{0}", '.format(bridge) + \
                                       ':auto_config => false'
        self.vagrant_data['ssh_port'] = sshport
        self.vagrant_data['vrde_port'] = vrdeport
        self.vagrantenv.initialize(self.vagrant_data)

        self.kanopya_register_hosts(self.booked_hosts)
        self.kanopya_setup_inputs(network, ip)

    def update(self, db):
        JobInfrastructure.update(self, db)
        # as vagrant do not configure bridge interface, you do it here by hand
        network, ip = self.get_network_conf(db)
        logger.debug("apply ip configuration on the vm bridged interface eth1")
        command = "sudo ip addr add {0}/24 dev eth1 ".format(ip) + \
                  "&& sudo ip link set eth1 up"
        self.vagrantenv.command(command)

    def clean(self, db):
        JobInfrastructure.clean(self)
        # remove vlan on the switch (move ports to vlan 1) and unbook hosts
        switch = ProcurveSSHClient('procurve-switch.intranet.hederatech.com',
                                   22, 'manager', 'manager')
        vlan = 1
        for host in self.booked_hosts:
            for iface in host['ifaces']:
                if 'switch_port' not in iface.keys():
                    continue
                port = iface['switch_port']
                logger.debug("set switch port %s on vlan %s untagged",
                             port, vlan)
                switch.set_untagged_port(port, vlan)
            host['job'] = None
        self.booked_hosts = None
        
        # remove vlan device
        vlan_device = "{0}.{1}".format(self.BRIDGE, self.get_vlan_conf(db))
        utils.remove_vlan_device(vlan_device)
        logger.debug("remove vlan device %s", vlan_device)

    def get_vlan_conf(self, db):
        """ retrieve the vlan used by the current job """
        vlan = None
        if db.jobs[self.job]['vlan'] is None:
            vlan = db.new_vlan()
            logger.debug('new vlan : %s', vlan)
            db.jobs[self.job]['vlan'] = vlan
        else:
            vlan = db.jobs[self.job]['vlan']
            logger.debug('reusing vlan %s', vlan)

        return vlan

    def _book_hosts(self, db):
        """ use deployment solver to determine required hosts """
        lines = [line for line in os.environ.get('HOSTS').split('\n')
                 if len(line)]
        free_hosts = db.get_available_hosts()
        dsolver = DeploymentSolver(self.workspace)
        booked_hosts = []
        for constraints in lines:
            dsolver.generate_hosts_file(free_hosts)
            dsolver.generate_host_constraint(constraints)
            index = dsolver.select_host()
            if index != -1:
                booked_hosts.append(free_hosts.pop(index))
            else:
                msg = "deployment_solver was enable to find a host " + \
                      "matching the constraints {0}".format(constraints)
                raise RuntimeError()

        for host in booked_hosts:
            logger.info("book %s", host['serial_number'])
            host['job'] = self.job

        return booked_hosts
