import threading
import time
from util import *


class NibSwUpdater(threading.Thread):
    def __init__(self, sw_image):
        threading.Thread.__init__(self)
        self.sw_image = sw_image
        self.lock = threading.Lock()
        self.progress_msg = {'status': 'running', 'message': 'initializing software upgrade', 'progress': 2}
        self.stop_thread = 0
        self.parts = {
            'set1': {'boot': '/dev/sda1', 'root': '/dev/sda5', 'config': '/dev/sda7', 'bootflag': '-A1'},
            'set2': {'boot': '/dev/sda2', 'root': '/dev/sda6', 'config': '/dev/sda8', 'bootflag': '-A2'},
            'root_mnt': '/tmp/target',
            'boot_mnt': '/tmp/target/boot',
            'conf_mnt': '/tmp/target/config',
            'sys_mnt' : '/tmp/target/sys',
            'proc_mnt': '/tmp/target/proc',
            'dev_mnt' : '/tmp/target/dev'
        }
        self.passive = ''
        self.mnt_points = []
        log_info('initializing software upgrade')

    def run(self):
        upgrade_steps = {
            'step 1': {'func': self.prepare_upgrade, 'msg': 'preparing software upgrade', 'prg': 5},
            'step 2': {'func': self.format_parts, 'msg': 'formatting partitions', 'prg': 15},
            'step 3': {'func': self.extract_image, 'msg': 'extracting image to hard disk', 'prg': 35},
            'step 4': {'func': self.configure_system, 'msg': 'configuring system', 'prg': 55},
            'step 5': {'func': self.update_grub, 'msg': 'updating grub', 'prg': 75},
            'step 6': {'func': self.cleanup, 'msg': 'cleanup', 'prg': 90},
        }
        _len = len(upgrade_steps)
        steps = 1
        for k, v in upgrade_steps.iteritems():
            if not self.stop_thread:
                msg = k + '/' + str(_len) + ':' + v['msg']
                log_info(msg)
                self.progress_msg = {'status': 'running', 'message': msg, 'progress': v['prg']}
                ret = v['func']()
                if ret:
                    msg = '{0}(failed)'.format(msg)
                    log_err(msg)
                    self.progress_msg = {'status': 'failed', 'message': msg, 'progress': -1}
                    break
            else:
                self.cleanup()
                self.progress_msg = {'status': 'abort', 'message': 'user aborted software upgrade', 'progress': -1}
                log_info('user aborted software upgrade')
                break
            steps += 1

        if (steps - 1) == _len:
            self.progress_msg = {'status': 'completed', 'message': 'software upgrade completed', 'progress': 100}
            log_info('software upgrade completed')

        while True:
            if not self.stop_thread:
                time.sleep(1)
            else:
                log_info('software upgrade thread exits')
                break

    def prepare_upgrade(self):
        # check which partition needed to upgraded
        root_minor = os.stat('/')[2]
        boot_minor = os.stat('/boot')[2]
        set1_root = int((self.parts['set1']['root'])[-1:])
        set1_boot = int((self.parts['set1']['boot'])[-1:])
        set2_root = int((self.parts['set2']['root'])[-1:])
        set2_boot = int((self.parts['set2']['boot'])[-1:])
        if (root_minor & set1_root) & (boot_minor & set1_boot):
            self.passive = 'set1'
        elif (root_minor & set2_root) & (boot_minor & set2_boot):
            self.passive = 'set2'
        else:
            log_err('invalid partitions combinations')
            return -1
        if not os.path.isfile(self.sw_image):
            log_err('software image not found {0}'.format(self.sw_image))
        return 0

    def format_parts(self):
        # format partitions and mount
        f_cmd = "mkfs.ext4 -F -E lazy_itable_init {0}"
        root_f_cmd = f_cmd.format(self.parts[self.passive]['root'])
        boot_f_cmd = f_cmd.format(self.parts[self.passive]['boot'])
        conf_f_cmd = f_cmd.format(self.parts[self.passive]['config'])

        ret = exec_cmd(root_f_cmd.split())
        if ret:
            return ret
        ret = exec_cmd(boot_f_cmd.split())
        if ret:
            return ret
        ret = exec_cmd(conf_f_cmd.split())
        if ret:
            return ret

        # mount the partition boot
        mnt_cmd = "mount -t ext4 {0} {1}"
        if not os.path.exists(self.parts['root_mnt']):
            os.mkdir(self.parts['root_mnt'])
        ret = exec_cmd(mnt_cmd.format(self.parts[self.passive]['root'], self.parts['root_mnt']).split())
        if ret:
            return ret
        # store mount points in array for cleanup
        self.mnt_points.append(self.parts['root_mnt'])

        if not os.path.exists(self.parts['boot_mnt']):
            os.mkdir(self.parts['root_mnt'])
        ret = exec_cmd(mnt_cmd.format(self.parts[self.passive]['boot'], self.parts['boot_mnt']).split())
        if ret:
            return ret
        self.mnt_points.append(self.parts['boot_mnt'])

        if not os.path.exists(self.parts['conf_mnt']):
            os.mkdir(self.parts['conf_mnt'])
        ret = exec_cmd(mnt_cmd.format(self.parts[self.passive]['conf'], self.parts['conf_mnt']).split())
        if ret:
            return ret
        self.mnt_points.append(self.parts['conf_mnt'])

        return 0

    def extract_image(self):
        return exec_cmd("tar xfz {0} -C  {1}".format(self.sw_image, self.parts['root_mnt']).split())

    def configure_system(self):
        fstab_string = (
            self.parts[self.passive]['root'] + "/ ext4    errors=remount-ro 0 1\n" +
            self.parts[self.passive]['boot'] + "/boot ext4 defaults 0 2\n" +
            self.parts[self.passive]['conf'] + "/config ext4 defaults 0 2\n" +
            "/dev/sda9 /mnt/storage ext4 defaults 0 2\n" +
            "/dev/sda3 none swap sw 0 0\n")
        fstab_file = open("{0}/etc/fstab".format(self.parts['root_mnt']), "w")
        fstab_file.write(fstab_string)
        fstab_file.close()

        ret = exec_cmd("mount -o bind /sys {0}".format(self.parts['sys_mnt']).split())
        if ret:
            return ret
        self.mnt_points.append(self.parts['sys_mnt'])

        ret = exec_cmd("mount -o bind /dev {0}".format(self.parts['dev_mnt']).split())
        if ret:
            return ret
        self.mnt_points.append(self.parts['dev_mnt'])

        ret = exec_cmd("chroot {0} mount -t proc /proc /proc".format(self.parts['root_mnt']).split())
        if ret:
            return ret
        self.mnt_points.append(self.parts['proc_mnt'])

        return ret

    def update_grub(self):
        ret = exec_cmd("chroot {0} grub-install /dev/sda".format(self.parts['root_mnt']).split())
        if ret:
            return ret
        ret = exec_cmd("chroot {0} update-grub".format(self.parts['root_mnt']).split())
        if ret:
            return ret
        ret = exec_cmd("sfdisk {0} /dev/sda".format(self.parts[self.passive]['bootflag']).split())
        return ret

    def cleanup(self):
        def wait_unmount(mountpoint):
            while (exec_cmd('mountpoint -q {0}'.format(mountpoint).split()) == 0 and
                    exec_cmd('umount {0}'.format(mountpoint).split()) != 0):
                exec_cmd('lsof {0}'.format(mountpoint).split())
                time.sleep(1)
        for mtp in reversed(self.mnt_points):
            wait_unmount(mtp)
        os.rmdir(self.parts['root_mnt'])
        return 0

    def get_status(self):
        return self.progress_msg

    def stop(self):
        self.stop_thread = 1
