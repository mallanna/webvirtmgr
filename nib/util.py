import os
import socket
import json
from nib.settings import *

def is_nib_super_user(user):
    if user == NIB_SUPER_USER:
        return True
    else:
        return False

def nib_get_maxvms():
    return NIB_MAX_VMS


def get_nib_imagelist():
    img_list = os.listdir(NIB_SW_IMAGE_PATH)
    image_list = []
    for image_name in img_list:
        image_list.append(
            {'name': image_name,
             'size': os.path.getsize(NIB_SW_IMAGE_PATH + '/' + image_name)}
        )
    return image_list


def delete_nib_image(f_name):
    nib_image_path = NIB_SW_IMAGE_PATH + '/' + str(f_name)
    os.remove(nib_image_path)

# TODO: replace  SOCK_DGRAM to SOCK_STREAM
def send_recv(message):
    print message
    json.dumps(message)

    if not os.path.exists(NIB_UNIX_SERVER_SOCKET):
        return {}
    try:
        os.unlink(NIB_UNIX_CLIENT_SOCKET)
    except OSError:
        if os.path.exists(NIB_UNIX_CLIENT_SOCKET):
            print 'unable to remove sock file'
            return {}
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock.bind(NIB_UNIX_CLIENT_SOCKET)
    sock.sendto(json.dumps(message), NIB_UNIX_SERVER_SOCKET)
    ret_msg = json.loads(sock.recv(NIB_RECV_SIZE))
    sock.close()
    os.unlink(NIB_UNIX_CLIENT_SOCKET)
    return ret_msg

def stop_swupgrade():
    req_msg = {'service': 'swupgrade', 'request': 'stop'}
    if send_recv(req_msg):
        print 'software upgrade service stopped successfully'
    else:
        print 'error while stopping software upgrade service'


def create_sw_upgrade_state(image_name):
    if os.path.exists(NIB_SW_UPGRADE_STATE):
        os.remove(NIB_SW_UPGRADE_STATE)
    sw_state = {'image': image_name, 'state': 1}
    with open(NIB_SW_UPGRADE_STATE, "w") as state_file:
        state_file.write(json.dumps(sw_state))
        state_file.close()

def update_sw_upgrade_state(state):
    if not state:
        if os.path.exists(NIB_SW_UPGRADE_STATE):
            os.remove(NIB_SW_UPGRADE_STATE)
    else:
        with open(NIB_SW_UPGRADE_STATE, "r+") as state_file:
            data = json.load(state_file)
            tmp = data['state']
            data['state'] = state
            state_file.seek(0)
            state_file.write(json.dumps(data))
            state_file.truncate()
            state_file.close()


def get_sw_upgrade_state():
    state = {}
    if os.path.exists(NIB_SW_UPGRADE_STATE):
        state_file = open(NIB_SW_UPGRADE_STATE, "r+")
        state = json.load(state_file)
        state_file.close()
    return state





