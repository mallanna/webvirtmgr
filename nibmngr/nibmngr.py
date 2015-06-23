import socket
import json
import errno
import time
from threading import Thread
from pwd import getpwnam
from settings import *
from util import *
from swupgrade import NibSwUpdater

updater = None

# TODO: 1. replace udp unix socket to tcp
# TODO: 2. handle signals
# TODO: 3. handle service shutdown based on signals

class NibServiceMngr:
    def __init__(self, is_daemon):

        if not os.path.exists(NIB_RUN_DIR):
            try:
                os.mkdir(NIB_RUN_DIR)
            except OSError:
                raise
        os.chown(NIB_RUN_DIR, getpwnam(NIB_SOCKET_USER)[2], getpwnam(NIB_SOCKET_USER)[2])
        self.sock_path = NIB_UNIX_SERVER_SOCKET
        try:
            os.unlink(self.sock_path)
        except OSError:
            if os.path.exists(self.sock_path):
                raise
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sock.bind(self.sock_path)
        os.chown(self.sock_path, getpwnam(NIB_SOCKET_USER)[2], getpwnam(NIB_SOCKET_USER)[2])
        self.thread = Thread(target=self.listener)
        self.thread.setDaemon(is_daemon)
        self.thread.start()

    def _send(self, data):
        s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        s.sendto(data, NIB_UNIX_CLIENT_SOCKET)
        s.close()

    def listener(self):
        log_info('NibServiceMngr: started')
        while True:
            try:
                data, _ = self.sock.recvfrom(NIB_RECV_SIZE)
            except socket.error as e:
                if e.errno == errno.EINTR:
                    log_warn('received EINTR')
                else:
                    log_err('error while receiving')
                    print e
                continue
            req_msq = json.loads(data)
            resp_msg = self.process_req(req_msq)
            self._send(json.dumps(resp_msg))

    def process_req(self, message):
        print "processing message %s" % message['service']
        ret_msg = {}
        service = message['service'];
        if service == 'reset':
            _msg = 'OK'
            req_type = message['request']
            log_info('NibServiceMngr: requested for system %s' % req_type)
            if req_type == 'reboot':
                ret_value = reset_nib('-r')
            elif req_type == 'shutdown':
                ret_value = reset_nib('-h')
            else:
                ret_value = -1
                _msg = 'Invalid request'
            if ret_value:
                _msg = os.strerror(ret_value)
            ret_msg = {'return_code': ret_value, 'message': _msg}
        elif service == 'lmpconfig':
            req_type = message['request']
        elif service == 'swupgrade':
            global updater
            req_type = message['request']
            if req_type == 'start':
                if isinstance(updater, NibSwUpdater):
                    ret_msg = {'status': 'warning', 'message': 'software upgrade thread already active', 'progress': -1}
                    log_warn('software upgrade thread already active')
                    return ret_msg
                updater = NibSwUpdater(message['data']['image'])
                updater.start()
                if updater.isAlive():
                    ret_msg = updater.get_status()
                else:
                    ret_msg = {'status': 'failed', 'message': 'software upgrade thread died', 'progress': -1}
                    log_err('software upgrade thread died')
            if req_type == 'stop':
                if isinstance(updater, NibSwUpdater):
                    ret_msg = updater.get_status()
                    updater.stop()
                    updater.join()
                    updater = None
                else:
                    ret_msg = {'status': 'failed', 'message': 'software upgrade thread not active', 'progress': -1}
                    log_info('software upgrade thread not active')
            if req_type == 'status':
                if isinstance(updater, NibSwUpdater):
                    ret_msg = updater.get_status()
                else:
                    ret_msg = {'status': 'failed', 'message': 'software upgrade is not active', 'progress': -1}
                    log_err('software upgrade thread is not active')
        else:
            print 'Invalid service'
            ret_msg = {'return_code': -1, 'message': 'Invalid service'}
        return ret_msg


def main():
    NibServiceMngr(is_daemon=False)

if __name__ == "__main__":
    main()

