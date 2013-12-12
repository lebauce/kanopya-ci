import json
import os
import subprocess
import logging


logger = logging.getLogger(__name__)


class DeploymentSolver(object):
    def __init__(self, directory,
                 jar='/var/lib/jenkins/bin/deployment_solver.jar'):
        self.jar = jar
        self.hosts_file = os.path.join(directory, 'hosts.json')
        self.constraints_file = os.path.join(directory, 'constraints.json')
        self.result_file = os.path.join(directory, 'result.json')

    def generate_hosts_file(self, available_hosts):
        """ generate a json file to describe available hosts """
        hosts = []
        for host in available_hosts:
            h = {'cpu': {'nbCores': host['core']},
                 'ram': {'qty': host['ram'] / 1048576},
                 'network': {'ifaces': []},
                 'storage': {'hardDisks': []},
                 'tags': []}
            for iface in host['ifaces']:
                h['network']['ifaces'].append({'bondsNumber': 1, 'netIPs': []})

            for hdd in host['harddisks']:
                h['storage']['hardDisks'].append(
                    {'size': int(hdd['size']) / 1073741824})

            hosts.append(h)

        with open(self.hosts_file, 'w') as f:
            f.write(json.dumps(hosts))

    def generate_host_constraint(self, constraints):
        """
        Generate a json file to describe host constraints.
        WARNING: input must be a valid json string to pass to
        deployment solver.
        """
        # remove double quotes added by jenkins
        if constraints[0] == '"':
            constraints = constraints[1:]
        if constraints[-1] == '"':
            constraints = constraints[:-1]

        with open(self.constraints_file, 'w') as f:
            f.write(constraints)

    def select_host(self):
        """ call the java jar and read the result json file """
        p = subprocess.Popen(['java', '-jar', self.jar,
                              self.hosts_file, self.constraints_file,
                              self.result_file])
        p.communicate()
        if p.returncode != 0:
            raise RuntimeError("deployment_solver failed")

        with open(self.result_file, 'r') as f:
            r = json.loads(f.read())

        logger.debug("selectedHostIndex : %s", r['selectedHostIndex'])
        return r['selectedHostIndex']
