#!/usr/bin/env python3
from __future__ import print_function, absolute_import, division

from fuse import FUSE, Operations, FuseOSError
import argparse
from sys import argv, exit
import os
import time
#from guldns import cfg.admin, cfg.rawpath, mountpath
from guldcfg import mkdirp, BLOCKTREE, GuldConfig
from guldpass import get_pass
import threading
import zmq
from subprocess import check_output, check_call
cfg = GuldConfig()


class GuldFS(Operations):
    '''
    A signed and distributed filesystem using git and PGP. Requires both of
    those to be locally installed and configured for power use.

    Python implementation of:

    https://guld.io/guldFS-Specification.pdf.
    '''

    def __init__(self, mountpoint, user):
        self.root = os.path.abspath(mountpoint)
        if not os.path.exists(self.root):
            raise FuseOSError(os.errno.ENOENT)
        self.user = user
        self.context = zmq.Context()
        self.publisher = self.context.socket(zmq.PUB)
        self.publisher.bind("ipc:///tmp/guldfs0.ipc")
        # TODO how to know how long to wait?
        time.sleep(0.5)

    # gai thread lifecycle
    def init(self, path):
        '''
        Called on filesystem initialization. (Path is always /)
        Use it instead of __init__ if you start threads on initialization.
        '''
        self.publisher.send_multipart([b"guldfs",
            str.encode("mount:%s:%s" % (self.root,
                                        self.user))])

    def destroy(self, path):
        'Called on filesystem destruction. Path is always /'
        self.publisher.send_multipart([b"guldfs",
            str.encode("destroy")])
        # self.t.join(timeout=1)

    # fuse Operations implementation

    def access(self, path, mode):
        if not os.access(cfg.rawpath(path, self.user), mode):
            raise FuseOSError(os.errno.EACCES)

    def chmod(self, path, mode):
        self.publisher.send_multipart([b"guldfs", str.encode("chmod:%s:%s" % (path, mode))])
        return os.chmod(cfg.rawpath(path, self.user), mode)

    def chown(self, path, uid, gid):
        # TODO move file between user branches
        self.publisher.send_multipart([b"guldfs",
            str.encode("chmod:%s:%s:%s" % (path, uid, gid))])
        return os.chown(cfg.rawpath(path, self.user), uid, gid)

    def create(self, path, mode, fi=None):
        self.publisher.send_multipart([b"guldfs",
            str.encode("create:%s:%s:%s" % (path, mode, fi))])
        try:
            check_call(['install', '-b', '-m', str(oct(mode))[-3:], '-o', cfg.admin, '-g', cfg.admin, '/dev/null', cfg.rawpath(path, self.user)])
            return os.open(cfg.rawpath(path, self.user), os.O_WRONLY | os.O_CREAT, mode)
        except:
            raise FuseOSError(os.errno.EIO)

    def flush(self, path, fh):
        self.publisher.send_multipart([b"guldfs",
            str.encode("fsync:%s" % path)])
        return os.fsync(fh)

    def fsync(self, path, datasync, fh):
        return self.flush(path, fh)

    def fsyncdir(self, path, datasync, fh):
        self.publisher.send_multipart([b"guldfs",
            str.encode("fsyncdir:%s" % path)])
        return 0

    def getattr(self, path, fh=None):
        '''
        Returns a dictionary with keys identical to the stat C structure of
        stat(2).
        st_atime, st_mtime and st_ctime should be floats.
        NOTE: There is an incombatibility between Linux and Mac OS X
        concerning st_nlink of directories. Mac OS X counts all files inside
        the directory, while Linux counts only the subdirectories.
        '''
        st = os.lstat(cfg.rawpath(path, self.user))
        return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
                     'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))

    def getxattr(self, path, name, position=0):
        raise FuseOSError(os.errno.ENOTSUP)

    def link(self, target, source):
        self.publisher.send_multipart([b"guldfs",
            str.encode("link:%s:%s" % (target, source))])
        return os.link(cfg.rawpath(source, self.user), cfg.rawpath(target, self.user))

    def listxattr(self, path):
        return []

    def mkdir(self, path, mode):
        self.publisher.send_multipart([b"guldfs",
            str.encode("mkdir:%s:%s" % (path, mode))])
        return check_output(['mkdir', '-m', str(oct(mode))[-3:], cfg.rawpath(path, self.user)])
        #return os.mkdir(cfg.rawpath(path, self.user), mode)

    def mknod(self, path, mode, dev):
        # Probably unused by guldFS, since it loads after block devices
        # self.publisher.send_multipart([b"guldfs",
        #     str.encode("mknod:%s:%s:%s" % (path, mode, dev))])
        return os.mknod(cfg.rawpath(path, self.user), mode, dev)

    def open(self, path, flags):
        self.publisher.send_multipart([b"guldfs",
            str.encode("open:%s:%s" % (path, flags))])
        return os.open(cfg.rawpath(path, self.user), flags)

    def read(self, path, size, offset, fh):
        os.lseek(fh, offset, os.SEEK_SET)
        return os.read(fh, size)

    def readdir(self, path, fh):
        self.publisher.send_multipart([b"guldfs",
            str.encode("readdir:%s" % path)])
        path = cfg.rawpath(path, self.user)
        dirents = ['.', '..']
        if os.path.isdir(path):
            dirents.extend(os.listdir(path))
        for r in dirents:
            yield r

    def readlink(self, path):
        self.publisher.send_multipart([b"guldfs",
            str.encode("readlink:%s" % path)])
        pathname = os.readlink(cfg.rawpath(path, self.user))
        if pathname.startswith("/"):
            # Path name is absolute, sanitize it.
            return os.path.relpath(pathname, self.root)
        else:
            return pathname

    def release(self, path, fh):
        self.publisher.send_multipart([b"guldfs",
            str.encode("release:%s:%s" % (path, fh))])
        return os.close(fh)

    def releasedir(self, path, fh):
        self.publisher.send_multipart([b"guldfs",
            str.encode("releasedir:%s:%s" % (path, fh))])
        #fhs[fh] = None
        return 0

    def removexattr(self, path, name):
        raise FuseOSError(ENOTSUP)

    def rename(self, old, new):
        self.publisher.send_multipart([b"guldfs",
            str.encode("rename:%s:%s" % (old, new))])
        return os.rename(cfg.rawpath(old, self.user), cfg.rawpath(new, self.user))

    def rmdir(self, path):
        self.publisher.send_multipart([b"guldfs",
            str.encode("rmdir:%s" % path)])
        return os.rmdir(cfg.rawpath(path, self.user))

    def setxattr(self, path, name, value, options, position=0):
        raise FuseOSError(ENOTSUP)

    def statfs(self, path):
        stv = os.statvfs(cfg.rawpath(path, self.user))
        return dict((key, getattr(stv, key)) for key in ('f_bavail', 'f_bfree',
            'f_blocks', 'f_bsize', 'f_favail', 'f_ffree', 'f_files', 'f_flag',
            'f_frsize', 'f_namemax'))

    def symlink(self, target, source):
        self.publisher.send_multipart([b"guldfs",
            str.encode("symlink:%s:%s" % (target, source))])
        return os.symlink(target, cfg.rawpath(source, self.user))

    def truncate(self, path, length, fh=None):
        self.publisher.send_multipart([b"guldfs",
            str.encode("truncate:%s:%s:%s" % (path, length, fh))])
        full_path = cfg.rawpath(path, self.user)
        with open(full_path, 'r+') as f:
            f.truncate(length)

    def unlink(self, path):
        self.publisher.send_multipart([b"guldfs",
            str.encode("unlink:%s" % path)])
        return os.unlink(cfg.rawpath(path, self.user))

    def utimens(self, path, times=None):
        return os.utime(cfg.rawpath(path, self.user), times)

    def write(self, path, data, offset, fh):
        self.publisher.send_multipart([b"guldfs",
            str.encode("write:%s" % path)])
        os.lseek(fh, offset, os.SEEK_SET)
        return os.write(fh, data)


def cli():
    parser = argparse.ArgumentParser('GuldFS')
    parser.add_argument("--mountpoint", type=str, default="/home", help="The path to mount.")
    #parser.add_argument("--verbosity", help="increase output verbosity")
    args = parser.parse_args()
    mountpoint = os.path.abspath(args.mountpoint)
    FUSE(GuldFS(mountpoint, cfg.admin), mountpoint, nonempty=False, allow_other=True, nothreads=True, foreground=True)


if __name__ == "__main__":
    cli()
