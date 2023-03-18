# mt65xx
When I tried to mainline MT6577, I've read tons of forum posts, chat rooms and a lot of guides on the internet. This repository contains my notes, tips and other thoughts which could be useful for bringing support for old Mediatek devices into mainline Linux kernel and relevant development in general. The infomation should be appliable for mt65xx _32-bit_ CPUs running linux kernel v3.4. I have never worked worked on 3.10 and 3.18 kernels. If you have something to add please open a pull request or leave a comment.

## Table of contents
<!--ts-->
    * [Extracting information from the running device](#extracting-information-from-the-running-device)
        * [GPIO Pins](#gpio-pins)
        * [I2C](#i2c)
        * [LCM (LCD panel / controller model)](#lcm-lcd-panel--controller-model)
        * [PMIC](#pmic)
    * [Searching in the source code](#searching-in-the-source-code)
        * [Register addresses](#register-addresses)
<!--te-->

## Extracting information from the running device
_It's implied your device has root and busybox, and is connected to your PC via ADB, and the shell is running_

### GPIO Pins
_The output seems to be always stripped_
```
cat /sys/devices/virtual/misc/mtgpio/pin
```
Example output:
```
206: 0 0 0 0 1 1 0
207: 1 0 0 0 1 0 0
208: 1 0 0 0 1 0 0
209: 1 0 0 0 1 0 0
210: 1 0 0 0 1 0 0
211: 1 0 1 0 1 0 0
212: 1 0 1 0 1 0 0
213: 1 0 1 0 1 0 0
214: 1 0 1 0 1 0 0
215: 1 0 11|shell@android:/ $
```
Output description ([source](https://4pda.ru/forum/index.php?showtopic=535287&st=2860#entry37284242)):
```
1 [MODE 0 - GPIO]
2 [PULL_SEL (Pullup)]
3 [DIN]
4 [DOUT (output voltage) / 1 - high voltage (1.8V/2.8V..) ,0 - low voltage]
5 [PULL EN (Pull-up enabled)]
6 [DIR (Input on the next direction)(3,4 decision is valid]
7 [INV]
8 [IES]
```

### I2C
The command should list all attached I2C devices on all busses of your device:
```
find /sys/devices/platform/mt*i2c.* -mindepth 2 -name 'driver' -print -exec realpath '{}' \; -exec echo \;
```
Example output:
```
/sys/devices/platform/mt-i2c.0/i2c-0/0-0036/driver
/sys/bus/i2c/drivers/ncp1851

/sys/devices/platform/mt-i2c.0/i2c-0/0-004c/driver
/sys/bus/i2c/drivers/MC32X0
```
Output of this command contains 2 lines for each attached device:
* /sys/devices/platform/mt-i2c.0/i2c-0/0-**0036**/driver ← I2C address (hex)
* /sys/bus/i2c/drivers/**ncp1851** ← Driver name which could hint the actual hardware

### LCM (LCD panel / controller model)
```
cat /proc/cmdline
```
Example outputs:
```
console=ttyMT3,921600n1 vmalloc=320M lcm=1-lg4573b fps=5965 pl_t=582 lk_t=5249
console=ttyMT3,921600n1 vmalloc=506M slub_max_order=0 lcm=1-hx8379a_dsi_vdo_bidirectional fps=5300 pl_t=3466 lk_t=3184
```
See the `lcm=` parameter, remove leading digit and dash. LCM names from example outputs are `lg4573b` and `hx8379a_dsi_vdo_bidirectional` respectively.

### PMIC
This command prints known voltage values in millivolts (mV):
```
busybox find /sys/devices/platform/mt-pmic/ -iname '*volt*' -print -exec cat '{}' \; -exec echo \;
```
Example output:
```
/sys/devices/platform/mt-pmic/LDO_VCAM_AF_VOLTAGE
2800

/sys/devices/platform/mt-pmic/BUCK_VCORE_VOLTAGE
800
```

## Searching in the source code
_It's great if there is a public kernel source code for your SoC. If you have a kernel source code for your exact device model, you can do a bit more. Usually old mediatek kernels have directory structure like [this](https://github.com/rex-xxx/mt6572_x201/tree/f87ef7407576b4fd190c76287e92b2e9886ca484), or [this](https://github.com/arzam16/mt6577_kernel_Acer_B1_A71). Newer kernels have [this](https://github.com/WikoGeek-Unofficial/android_kernel_wiko_mt6577) directory structure. Anyway, the `mediatek/platforrm/mt65xx` directory is what we need._

### Register addresses
Mainlining a device involves writing a Device Tree Source file which requires you to know exact register addresses. Mediatek source code uses _virtual_ register addresses, but DTS needs _physical_ addresses. To solve this, you need to look in `mediatek/platform/mt65xx/kernel/core/include/mach/memory.h` and search for `IO_VIRT_TO_PHYS` macro there.

Example ([source](https://github.com/arzam16/mt6577_kernel_Acer_B1_A71/blob/67a47ce448ed2dad6004f1d5244d5fc26a0907ef/mediatek/platform/mt6577/kernel/core/include/mach/memory.h#L20)):
```
#define IO_VIRT_TO_PHYS(v) (0xC0000000 | ((v) & 0x0fffffff))
```
What this function does is simply replacing the first hexadecimal digit with 'C'. So, if downstream kernel source code lists some register address as `0xF0001234`, then its physical address is just `0xC0001234`. Though there might be more complicated functions.
After virtual to physical address conversion is sorted out, it's safe to continue working on registers. Below are major sources of register addresses:
1. `mediatek/platform/mt65xx/kernel/core/include/mach/mt_reg_base.h` - should list registers for big SoC subsystems
2. `mediatek/platform/mt65xx/kernel/core/include/mach/mt_clock_manager.h` - should contain most of the clock-related registers
3. `mediatek/platform/mt65xx/kernel/core/include/mach/mt_device_apc.h` - DEVAPC (DEVice Automatic Power Control)
4. `mediatek/platform/mt65xx/kernel/core/include/mach/mt_dcm.h`
5. `mediatek/platform/mt65xx/kernel/core/include/mach/mt_cpe.h`
6. `mediatek/platform/mt65xx/kernel/core/include/mach/mt_emi_bm.h`
7. `mediatek/platform/mt65xx/kernel/core/include/mach/mt_emi_bwl.h`
8. `mediatek/platform/mt65xx/kernel/core/include/mach/mt_emi_mpu.h`

Data gathered from the first 2 files is usually enough to boot basic mainline kernel.
