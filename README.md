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
- `ksun`: KernelSU-Next with the syscall-table hook (this kernel has no kprobes)
- `cfi-permissive`: `CONFIG_CFI_PERMISSIVE=y`

## Patches
- `patches/ksun/0001`: pix106's tree backports `copy_to_kernel_nofault()` from 5.8. KernelSU-Next's pre-5.8 compat macro then clashes with that declaration. The patch adds a Kbuild check for the backport, the same way KernelSU-Next already handles `strncpy_from_user_nofault`.

## Output
The Actions artifact holds:
- `boot-ksun.img`: the stock LineageOS 23.2 (20261112) boot image with only the kernel swapped; the ramdisk is untouched
- `Image.gz-dtb`
- the final `.config`
- the build log and SHA256 sums

Flash it only on the matching ROM build. Keep the stock `boot.img` so you can roll back.

All kernel code belongs to its upstream authors (GPL-2.0).
- `patches/ksun/0002`: this config has no `CONFIG_KALLSYMS_ALL` (it depends on `DEBUG_KERNEL`), so kallsyms can't resolve the data symbol `sys_call_table` and the table hook switched itself off (`sth: sys_call_table not found`). Built in, KernelSU-Next now takes the address from `<asm/syscall.h>` instead.

## Findings
- Run 5 (upstream clang 21.1.8): bootloops before ramoops. Its KSU table hook was already disabled by the lookup failure above, so the toolchain was the cause.
- Run 6 (AOSP r563880c), `ksu-cfiperm`: boots. KernelSU-Next 33327 core (LSM hooks, supercalls) initialises, no CFI reports, but the table hook stays off (fixed by 0002).
