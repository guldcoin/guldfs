import sys
import os
import time
import subprocess
from guldfs import mount
from guldfs.guldfs import GuldFS
from fuse import FUSE
from unittest import TestCase
# import threading
from guldfs.common import ADMIN
MOUNTPOINT = '/home/%s' % ADMIN

def modifyFile(fil):
    f = open(fil, 'r+')
    content = f.read()
    f.write(content + '\n')
    f.close()

def modifyAddCommitPushReset(fil):
    modifyFile(fil)
    subprocess.check_output(["git", "add", fil.replace(MOUNTPOINT + '/ ', '')])
    subprocess.check_output(["git", "commit", "-m", "modified file trivially"])
    subprocess.check_output(["sudo", "gitolite", "push", "origin", ADMIN])
    subprocess.check_output(["git", "reset", "--hard", "HEAD~1"])

class TestMount(TestCase):
    @classmethod
    def setUpClass(cls):
        # TODO swap out for current username or generate test user?
        cls.p = subprocess.Popen(['guldfs', MOUNTPOINT])
        s = 0
        while s < 30:
            if os.path.ismount(MOUNTPOINT):
                break
            if cls.p is not None and cls.p.poll() is not None:
                pytest.fail('file system failed to mount')
                break
            time.sleep(0.1)
            s += 0.1
        os.chdir(MOUNTPOINT)

    @classmethod
    def tearDownClass(cls):
        cls.p.terminate()
        subprocess.Popen(['sudo', 'umount', MOUNTPOINT])

    def test_read_gitignore(self):
        mounted = open('%s/.gitignore' % MOUNTPOINT)
        m = mounted.read()
        source = open('/home/.blocktree/%s/.gitignore' % ADMIN)
        s = source.read()
        assert(len(m) > 1)
        assert('.bashrc' in m)
        assert(s == m)
        mounted.close()
        source.close()

    def test_read_gitignore_modified_in_gitolite(self):
        source = open('/home/.blocktree/%s/.gitignore' % ADMIN)
        s = source.read()
        source.close()
        modifyAddCommitPushReset('%s/.gitignore' % MOUNTPOINT)
        mounted = open('%s/.gitignore' % MOUNTPOINT)
        m = mounted.read()
        mounted.close()
        assert(s != m)
