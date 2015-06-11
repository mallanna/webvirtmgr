from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.core.urlresolvers import reverse


def upgrade(request):
    """
    upgrade page.
    """
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('login'))

