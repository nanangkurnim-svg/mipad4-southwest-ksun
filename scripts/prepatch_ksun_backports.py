#!/usr/bin/env python3
"""Pre-apply the source backports that KernelSU-Next's Kbuild would otherwise
inject with `sed -i` in the middle of a build.

Those mid-build edits race with parallel compilation: fs/namespace.o and
users of struct seccomp can be built before the edit lands. That leaves a
missing path_umount, or worse, objects that disagree on the struct seccomp
layout. Applying the edits up front, before `make`, makes KernelSU-Next's
grep checks pass so it skips the sed entirely.

Run from the kernel source root. Exits non-zero if an anchor is not found.
"""
import pathlib
import sys

CAN_UMOUNT = '''static int can_umount(const struct path *path, int flags)
{
	struct mount *mnt = real_mount(path->mnt);

	if (flags & ~(MNT_FORCE | MNT_DETACH | MNT_EXPIRE | UMOUNT_NOFOLLOW))
		return -EINVAL;
	if (!may_mount())
		return -EPERM;
	if (path->dentry != path->mnt->mnt_root)
		return -EINVAL;
	if (!check_mnt(mnt))
		return -EINVAL;
	if (mnt->mnt.mnt_flags & MNT_LOCKED) /* Check optimistically */
		return -EINVAL;
	if (flags & MNT_FORCE && !capable(CAP_SYS_ADMIN))
		return -EPERM;
	return 0;
}

/* Backported from v5.9 (41525f56e256) for KernelSU-Next */
int path_umount(struct path *path, int flags)
{
	struct mount *mnt = real_mount(path->mnt);
	int ret;

	ret = can_umount(path, flags);
	if (!ret)
		ret = do_umount(mnt, flags);

	/* we mustn't call path_put() as that would clear mnt_expiry_mark */
	dput(path->dentry);
	mntput_no_expire(mnt);
	return ret;
}

'''


def edit(path, anchor, insert, *, before=True, marker):
    p = pathlib.Path(path)
    s = p.read_text()
    if marker in s:
        print(f'{path}: already has {marker!r}, skipping')
        return
    if s.count(anchor) != 1:
        sys.exit(f'{path}: anchor {anchor!r} found {s.count(anchor)} times, expected 1')
    s = s.replace(anchor, insert + anchor if before else anchor + insert)
    p.write_text(s)
    print(f'{path}: added {marker!r}')


# 1. can_umount + path_umount, after may_mount() and before ksys_umount(),
#    which keeps every helper they need (do_umount, check_mnt, ...) in scope.
edit('fs/namespace.c', 'int ksys_umount(char __user *name, int flags)\n',
     CAN_UMOUNT, marker='int path_umount(')

# 2. Declaration for KernelSU-Next's extern use.
edit('fs/internal.h', 'extern void __init mnt_init(void);\n',
     'int path_umount(struct path *path, int flags);\n', before=False,
     marker='int path_umount(')

# 3. struct seccomp.filter_count. KernelSU-Next only touches it on >=5.9
#    paths, but its grep check edits the header unless the field is present,
#    so add it before anything compiles to keep the layout consistent.
edit('include/linux/seccomp.h', '#include <linux/thread_info.h>\n',
     '#include <linux/atomic.h>\n', before=False, marker='#include <linux/atomic.h>')
edit('include/linux/seccomp.h', 'struct seccomp {\n\tint mode;\n',
     '\tatomic_t filter_count;\n', before=False, marker='atomic_t filter_count;')
