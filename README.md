# SouthWest-NG + KernelSU-Next for Mi Pad 4 (clover)

A personal build of [pix106's SouthWest-NG](https://github.com/pix106/android_kernel_xiaomi_sdm660_southwest-ng) 4.19 kernel (`main-legacy`, for non-dynamic Android 16 ROMs such as pix106's LineageOS 23.2), with [KernelSU-Next](https://github.com/KernelSU-Next/KernelSU-Next) (`legacy` branch) built in.

## What it changes
- The base config is the one pulled from the running 0.23.0-legacy kernel (`/proc/config.gz`).
- It builds with AOSP `clang-r563880c`, the compiler pix106 used, sparse-cloned from the `android16-qpr2-release` branch of AOSP's `prebuilts/clang/host/linux-x86`.
- Three variants are built as a matrix:

| Variant | Fragments | Purpose |
|---|---|---|
| `noksu` | common | Baseline: same toolchain and config, no KernelSU |
| `ksu-cfiperm` | common + ksun + cfi-permissive | KernelSU-Next with CFI violations logged instead of panicking |
| `ksu` | common + ksun | KernelSU-Next with strict CFI |

The fragments:
- `common`: TCP BBR (behind `TCP_CONG_ADVANCED`) and fq_codel
- `ksun`: KernelSU-Next with manual hooks (`CONFIG_KSU_MANUAL_HOOK`)
- `cfi-permissive`: `CONFIG_CFI_PERMISSIVE=y`

## Patches
- `patches/kernel/0001`: the KernelSU-Next manual hooks: `__do_execve_file`, `do_faccessat`, `vfs_statx`, `newfstat`, `vfs_read`, `input_handle_event` and `reboot`. Each is under `#ifdef CONFIG_KSU`. The `vfs_read` and input hooks are gated on flags that KernelSU-Next clears after boot.
- `patches/ksun/0001`: pix106's tree backports `copy_to_kernel_nofault()` from 5.8. KernelSU-Next's pre-5.8 compat macro then clashes with that declaration. The patch adds a Kbuild check for the backport, the same way KernelSU-Next already handles `strncpy_from_user_nofault`.
- `patches/ksun/0002`: this config has no `CONFIG_KALLSYMS_ALL` (it depends on `DEBUG_KERNEL`), so kallsyms can't resolve the data symbol `sys_call_table` and the table hook switched itself off (`sth: sys_call_table not found`). Built in, KernelSU-Next now takes the address from `<asm/syscall.h>` instead.
- `patches/ksun/0003`: `pmd_leaf()`/`pud_leaf()` arrived in 5.7. On arm64 4.19, `sys_call_table` sits in a 2M section mapping. `pmd_bad()` is true for section entries, so KernelSU-Next's page walk failed (`failed to find phy addr for patch dst addr`) and hooked 0/4 syscalls. The patch maps them to `pmd_sect()`/`pud_sect()`.
- `patches/kernel/0002`: Venus (vidc_3x) low-latency mode. `/sys/module/msm_vidc_debug/parameters/low_latency` pins the Venus core clock at the top DT rate (518.4 MHz) and skips decoder DCVS. The stock driver sizes the clock to throughput (SVS 269.33 MHz for 1080p60, i.e. ~12 ms per HEVC frame at 400 cycles/MB). It also never honoured VIDC_POWER_TURBO in the cycles-per-MB path, and DCVS overrode the turbo load. `fw_low_power_mode` and `sys_idle_indicator` are exposed too (applied at the next Venus cold start).
- `scripts/prepatch_ksun_backports.py`: KernelSU-Next's Kbuild `sed`-edits `fs/namespace.c`, `fs/internal.h` and `include/linux/seccomp.h` during the build. Under `-j`, objects compiled before the edit miss `path_umount` or disagree on the `struct seccomp` layout. The script applies the same backports before `make`, and the build fails if KernelSU-Next edits sources anyway.

## Findings
- Run 5 (upstream clang 21.1.8): bootloops before ramoops. Its KSU table hook was already disabled by the lookup failure 0002 fixes, so the toolchain was the cause.
- Run 6 (AOSP r563880c), `ksu-cfiperm`: boots. KernelSU-Next 33327 core (LSM hooks, supercalls) initialises with no CFI reports, but the table hook stays off (fixed by 0002).
- Run 8, `ksu-cfiperm` with 0002: boots and finds `sys_call_table`. All 4 patches fail in the page walk (fixed by 0003). No CFI reports, no oops.
- Run 9, `ksu-cfiperm` with 0003: `sth: 4/4 syscalls hooked`, no CFI reports. The manager still says "Unsupported | Not integrated": on the legacy branch, table mode only covers those 4 syscalls. ksud bootstrap (post-fs-data, init.rc, safe mode) and the reboot supercall are wired only for kprobes or manual hooks, so the manager is never recognised and ksud never gets installed. Switched to manual hooks; 0002/0003 stay for anyone who uses table mode.
- Run 10, manual hooks: `Hook mode: Manual`, post-fs-data, init.rc proxy, safe-mode check and manager crowning all work, and ksud installs from the manager. The v3.4.2 release manager speaks UAPI 5 while legacy is UAPI 6, so it needs a newer manager build (`dev` CI >= 896f45a, v3.4.2-291, 33646). Final `ksu` (strict CFI) boots clean: no CFI reports, no oops. Status: **Working (built-in), v3.4.0-legacy (33327)**.

## Upstream tracking
The build also runs daily (02:23 UTC). A small `upstream` job checks pix106's `main-legacy` and KernelSU-Next's `legacy` heads, and only builds when that pair hasn't been built before. When pix106 merges a new CIP tag, the kernel is rebuilt with all patches here on top.

A trial merge of CIP `v4.19.325-cip137` straight into `main-legacy` (`cip-merge.yml`) auto-merged 817/831 files, with 19 conflict regions in 14 files. Most of them are pix106 already carrying the newer 5.x backport of the same fix (BPF prog_array owner, sock_ops, lwt_bpf, glink `strscpy`, `mmap_read_unlock`). `cpufreq_schedutil.c`, `mmc/core/bus.c` and `swapfile.c` need hand merging. cip137 has no performance changes, so this repo waits for pix106's own merge rather than carrying a hand resolution in sched/mm/storage code.

## Output
Each variant's Actions artifact holds:
- `boot-<variant>.img`: the stock LineageOS 23.2 (20261112) boot image with only the kernel swapped; the ramdisk is untouched
- `Image.gz-dtb`
- the final `.config`
- `System.map`
- the build log and SHA256 sums

Flash it only on the matching ROM build. Keep the stock `boot.img` so you can roll back.

All kernel code belongs to its upstream authors (GPL-2.0).
