import subprocess
import logging


logger = logging.getLogger(__name__)


class LocalShell(object):
    def command(self, cmd, input=None):
        """ run a command in a shell """
        p = subprocess.Popen(cmd, shell=True,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)

        stdout, stderr = p.communicate(input)
        logger.debug("command: %s", cmd)
        logger.debug("returncode: %s", p.returncode)
        logger.debug("stdout:\n%s", stdout)
        logger.debug("stderr:\n%s", stderr)

        return stdout, stderr, p.returncode


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    s = LocalShell()
    print s.command('hostname')
