from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

from nib.util import *


def upgrade(request, host_id):
    """
    Upgrade page.
    """

    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('login'))

    errors = []
    images = get_nib_imagelist()
    image_name = ''

    def handle_uploaded_file(f_name):
        target = NIB_SW_IMAGE_PATH + '/' + str(f_name)
        destination = open(target, 'wb+')
        for chunk in f_name.chunks():
            destination.write(chunk)
        destination.close()

    if request.method == 'POST':
        if 'del_image' in request.POST:
            image_name = request.POST.get('img_name', '')
            try:
                delete_nib_image(image_name)
                return HttpResponseRedirect(request.get_full_path())
            except OSError as error_msg:
                errors.append(error_msg.strerror)
        if 'image_upload' in request.POST:
            if str(request.FILES['file']) in images:
                msg = _("NIB software image already exist")
                errors.append(msg)
            else:
                handle_uploaded_file(request.FILES['file'])
                return HttpResponseRedirect(request.get_full_path())
        if 'upgrade_image' in request.POST:
            image_name = request.POST.get('img_name', '')
            """
            send message to nib sw management server start
            software upgrade
            """
            # if software upgrade is running
            send_recv({'service': 'swupgrade', 'request': 'stop'})

            nib_sw_upgrade_req = {
                'service': 'swupgrade',
                'request': 'start',
                'data': {'image': NIB_SW_IMAGE_PATH + '/' + image_name}
            }
            nibmngr_status = send_recv(nib_sw_upgrade_req)
            if nibmngr_status and nibmngr_status['status'] == 'running':
                create_sw_upgrade_state(image_name)
            else:
                errors.append('Unable to start software update, check NIB syslog')
        if 'upgrade_cancel' in request.POST:
            print 'User aborted software upgrade'
            stop_swupgrade()
            update_sw_upgrade_state(0)
        if 'activation_cancel' in request.POST:
            print 'User canceled software upgrade activation'
            update_sw_upgrade_state(0)

    upgrade_state = get_sw_upgrade_state()
    if upgrade_state:
        image_name = upgrade_state['image']
        activation = 0
        if upgrade_state['state'] == 2:
            activation = 1
        return render_to_response('upgrade.html', locals(), context_instance=RequestContext(request))
    else:
        return render_to_response('nibimage.html', locals(), context_instance=RequestContext(request))


def upgrade_status(request, host_id):
    """
    Return upgrade status
    """

    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('login'))

    if not get_sw_upgrade_state():
        return HttpResponseRedirect(reverse('upgrade', args=[host_id]))
    errors = []

    status_msg = {
        'status': 'failed',
        'message': 'software upgrade failed (error: 1200)',
        'progress': -1
    }
    nibsw_upgrade_req = {'service': 'swupgrade', 'request': 'status'}
    update_status = send_recv(nibsw_upgrade_req)

    if update_status:
        try:
            status_msg['message'] = update_status['message']
            status_msg['progress'] = update_status['progress']
            status_msg['status'] = update_status['status']
            if update_status['status'] == 'abort':
                status_msg['status'] = 'failed'
            if update_status['status'] == 'completed':
                update_sw_upgrade_state(2)
                stop_swupgrade()
            if update_status['status'] == 'failed':
                update_sw_upgrade_state(0)
                stop_swupgrade()
        except KeyError:
            print 'invalid message nib service manger'
            print update_status

    response = HttpResponse()
    response['Content-Type'] = "text/javascript"
    response.write(json.dumps(status_msg))
    return response


def reboot(request, host_id):
    """
    Reboot page.
    """

    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('login'))
    errors = []
    req_type = ''
    if request.method == 'POST':
        if 'reboot' in request.POST:
            print 'Reboot triggered'
            req_type = 'reboot'
            req_msg = {'service': 'reset', 'request': req_type}
            activation = request.POST.get('activation', '')
            if activation == 'true':
                update_sw_upgrade_state(0)
            st = send_recv(req_msg)
            if st:
                print 'reboot command successful'
                return render_to_response('reboot_action.html', locals(), context_instance=RequestContext(request))
            else:
                print 'Unable to reboot the system'
                errors.append('Unable to reboot the system')
        if 'shutdown' in request.POST:
            print 'shutdown triggered'
            req_type = 'shutdown'
            req_msg = {'service': 'reset', 'request': req_type}
            st = send_recv(req_msg)
            if st:
                print 'shutdown command successful'
                return render_to_response('reboot_action.html', locals(), context_instance=RequestContext(request))
            else:
                print 'Unable to shutdown the system'
                errors.append('Unable to shutdown the system')
    disable_reboot = 0
    is_act = 'false'
    is_upgrade = get_sw_upgrade_state()
    if is_upgrade:
        disable_reboot = is_upgrade['state']
        if disable_reboot == 2:
            is_act = 'true'
    return render_to_response('reboot.html', locals(), context_instance=RequestContext(request))
