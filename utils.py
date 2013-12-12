import subprocess


def sudo(command):
    """ run a command with sudo """
    c = ['sudo']
    c.extend(command)
    p = subprocess.Popen(c)
    p.communicate()


def create_vlan_device(interface_name, vlan_id):
    """
    create virtual ethernet device which represents the virtual lans 
    on the physical lan. 
    """
    sudo(['vconfig', 'add', interface_name, vlan_id])
    vlan_device = "{0}.{1}".format(interface_name, vlan_id) 
    sudo(['ip', 'link', 'set', vlan_device, 'up'])
    return vlan_device


def remove_vlan_device(vlan_device):
    """ remove virtual ethernet device """
    sudo(['vconfig', 'rem', vlan_device])
