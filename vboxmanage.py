import os
import logging
import re

logger = logging.getLogger(__name__)


class VBoxManage(object):
    hostonly_re = re.compile("Host-only Interface \'(vboxnet[0-9]+)\',")

    def __init__(self, shell, bin='/usr/bin/VBoxManage'):
        self.bin = bin
        self.shell = shell
        if not os.path.exists(self.bin):
            raise AttributeError("{0} not found !".format(self.bin))
        if self.bin[-1] != ' ':
            self.bin = self.bin + ' '

    def poweroff_vm(self, vm_name):
        cmd = self.bin + "controlvm '{0}' poweroff".format(vm_name)
        stdout, stderr, returncode = self.shell.command(cmd)
        if returncode != 0:
            logger.warning("Command %s return %s", cmd, returncode)

    def delete_vm(self, vm_name):
        cmd = self.bin + "unregistervm '{0}' --delete".format(vm_name)
        stdout, stderr, returncode = self.shell.command(cmd)
        if returncode != 0:
            logger.warning("Command %s return %s", cmd, returncode)


    def list_runningvms(self, filter=""):
        cmd = self.bin + 'list runningvms'
        stdout, stderr, returncode = self.shell.command(cmd)
        if returncode != 0:
            logger.warning("Command %s return %s", cmd, returncode)

        vms = [l.split('{')[0][1:-2] for l in stdout.split("\n") if l]
        return [vm for vm in vms if vm.startswith(filter)]

    def get_vminfo(self, vm_name):
        cmd = self.bin + "showvminfo '{0}' --details".format(vm_name)
        stdout, stderr, returncode = self.shell.command(cmd)
        if returncode != 0:
            logger.warning("Command %s return %s", cmd, returncode)
        return stdout

    def get_hostonly_iface_name(self, vm_name):
        stdout = self.get_vminfo(vm_name)
        result = VBoxManage.hostonly_re.search(stdout)
        if result is not None:
            return result.group(1)
        return None

    def set_hostonlyadapter(self, vm_name, adapter_id, iface):
        cmd = self.bin + "modifyvm '{0}' ".format(vm_name) + \
                         "--hostonlyadapter{0} {1}".format(adapter_id, iface)
        stdout, stderr, returncode = self.shell.command(cmd)
        if returncode != 0:
            logger.warning("Command %s return %s", cmd, returncode)

    def start_vm(self, vm_name):
        cmd = self.bin + "startvm '{0}' --type headless".format(vm_name)
        stdout, stderr, returncode = self.shell.command(cmd)
        if returncode != 0:
            logger.warning("Command %s return %s", cmd, returncode)

    def clone_vm(self, vm_name, new_name, ifaces, cpus=None,
                 memory=None, vrdeport=None):
        cmd = self.bin + "clonevm '{0}' --register --mode all --name '{1}'".format(vm_name, 
                                                                                   new_name)
        stdout, stderr, returncode = self.shell.command(cmd)
        if returncode != 0:
            logger.warning("Command %s return %s", cmd, returncode)

        for i, iface in enumerate(ifaces):
            mac = iface['mac'].replace(':', '')
            index = i + 1
            adapter_type = iface['adapter_type']
            adapter_iface = iface['adapter_iface']
            cmd = self.bin + "modifyvm '{0}' --macaddress{1} {2}".format(new_name, 
                                                                         index, 
                                                                         mac.replace(':', ''))
            self.shell.command(cmd)

            cmd = self.bin + "modifyvm '{0}' --{1}{2} {3}".format(new_name, adapter_type, 
                                                                  index, adapter_iface)
            self.shell.command(cmd)

        if vrdeport is not None:
            cmd = self.bin + "modifyvm '{0}' --vrde on".format(new_name)
            self.shell.command(cmd)

            cmd = self.bin + "modifyvm '{0}' --vrdeport {1}".format(new_name,
                                                                    vrdeport)
            self.shell.command(cmd)

        if cpus is not None:
            cmd = self.bin + "modifyvm '{0}' --cpus {1}".format(new_name, cpus)
            self.shell.command(cmd)

        if memory is not None:
            cmd = self.bin + "modifyvm '{0}' --memory {1}".format(new_name,
                                                                  memory)
            self.shell.command(cmd)


if __name__ == '__main__':

    from shell import LocalShell
    logging.basicConfig(level=logging.DEBUG)
    s = LocalShell()
    vbm = VBoxManage(s)
    print vbm.list_runningvms()
