from subprocess import CalledProcessError, check_call
import os
from syslog import syslog, LOG_ERR, LOG_DEBUG, LOG_INFO, LOG_WARNING


def log_info(message):
    message = 'NIB service:' + message
    print message
    syslog(LOG_INFO, message)


def log_err(message):
    message = 'NIB service:' + message
    print message
    syslog(LOG_ERR, message)


def log_debug(message):
    message = 'NIB service:' + message
    print message
    syslog(LOG_DEBUG, message)


def log_warn(message):
    message = 'NIB service:' + message
    print message
    syslog(LOG_WARNING, message)

def exec_cmd(command):
    try:
        ret = check_call(command)
    except CalledProcessError as e:
        log_err(str(e) + '  error:' + os.strerror(e.returncode))
        return e.returncode
    except OSError as err:
        log_err(err.strerror)
        print err.strerror
        return err.errno
    return ret

def reset_nib(opt):
    command = "/sbin/shutdown " + opt + " -t 1"
    return exec_cmd(command.split())
