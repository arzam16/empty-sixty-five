# mt65xx
When I tried to mainline MT6577, I've read tons of forum posts, chat rooms and a lot of guides on the internet. This repository contains my notes, tips and other thoughts which could be useful for bringing support for old Mediatek devices into mainline Linux kernel and relevant development in general. The infomation should be appliable for mt65xx _32-bit_ CPUs running linux kernel v3.4. I have never worked worked on 3.10 and 3.18 kernels. If you have something to add please open a pull request or leave a comment.

## Table of contents
<!--ts-->
    * [Extracting information from the running device](#extracting-information-from-the-running-device)
        * [GPIO Pins](#gpio-pins)
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
