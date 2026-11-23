# SouthWest-NG + KernelSU-Next for Mi Pad 4 (clover)

A personal build of [pix106's SouthWest-NG](https://github.com/pix106/android_kernel_xiaomi_sdm660_southwest-ng) 4.19 kernel (`main-legacy`, for non-dynamic Android 16 ROMs such as pix106's LineageOS 23.2), with [KernelSU-Next](https://github.com/KernelSU-Next/KernelSU-Next) (`legacy` branch) built in.

## What it changes
- The base config is the one pulled from the running 0.23.0-legacy kernel (`/proc/config.gz`).
- `config/ksun.fragment` adds:
  - KernelSU-Next with the syscall-table hook (no kprobes on this kernel)
  - TCP BBR and fq_codel
  - a `-KSUN` suffix on the local version
- It builds with the same AOSP clang (`r563880c`) that pix106 used.

## Output
The Actions artifact holds:
- `boot-ksun.img`: the stock LineageOS 23.2 (20261112) boot image with only the kernel swapped; the ramdisk is untouched
- `Image.gz-dtb`
- the final `.config`
- the build log and SHA256 sums

Flash it only on the matching ROM build. Keep the stock `boot.img` so you can roll back.

All kernel code belongs to its upstream authors (GPL-2.0).
