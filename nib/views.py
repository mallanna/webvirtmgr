from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.core.urlresolvers import reverse

from nib.util import is_nib_super_user


def upgrade(request, host_id):
    """
    Upgrade page.
    """

    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('login'))

    superuser = is_nib_super_user(request.user.username)

    return render_to_response('upgrade.html', locals(), context_instance=RequestContext(request))


def reboot(request, host_id):
    """
    Reboot page.
    """
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('login'))

    if request.method == 'POST':
        if 'reboot' in request.POST:
            compute_id = request.POST.get('host_id', '')
            return HttpResponseRedirect(request.get_full_path())
    return render_to_response('reboot.html', locals(), context_instance=RequestContext(request))