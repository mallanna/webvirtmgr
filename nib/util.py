from webvirtmgr.settings import NIB_SUPER_USER, NIB_MAX_VMS


def is_nib_super_user(user):
    if user == NIB_SUPER_USER:
        return True
    else:
        return False


def nib_get_maxvms():
    return NIB_MAX_VMS
