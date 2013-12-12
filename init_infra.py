#!/usr/bin/env python

from infrastructure import new_infrastructure
from persistence import CIDB
import logging
import os
import subprocess
import urllib2


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('shell').setLevel(logging.INFO)
    logging.getLogger('paramiko.transport').setLevel(logging.INFO)
    logging.getLogger('hpprocurve').setLevel(logging.INFO)

    # TRICKS to avoid file descriptors leak on jenkins
    urllib2.urlopen('http://localhost:8080/gc')

    os.chdir(os.path.dirname(__file__))

    infra_type = os.environ.get('INFRASTRUCTURE', 'none')
    job_name = os.environ.get('JOB_NAME')

    with CIDB('/var/lib/jenkins/ciplatform/cidb.pickled') as db:
        # first we check if the job infrastructure has been correctly clean
        # during the previous build
        if job_name in db.jobs.keys():
            infra = db.jobs[job_name]['infra']
            if infra is not None:
                logging.warning("Job %s already has a infrastructure, " + \
                                "try to clean it", job_name)

        infra = new_infrastructure(infra_type)
        infra.initialize(db)
        db.jobs[job_name]['infra'] = infra
        db.save()
        
