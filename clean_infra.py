#!/usr/bin/env python

from infrastructure import new_infrastructure
from persistence import CIDB
import logging
import os


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('shell').setLevel(logging.INFO)
    logging.getLogger('paramiko.transport').setLevel(logging.INFO)
    logging.getLogger('hpprocurve').setLevel(logging.INFO)

    os.chdir(os.path.dirname(__file__))

    job_name = os.environ.get('JOB_NAME')

    with CIDB('/var/lib/jenkins/ciplatform/cidb.pickled') as db:
        infra = db.jobs[job_name]['infra']
        infra.clean(db)

        db.jobs[job_name]['infra'] = None
        db.save()
