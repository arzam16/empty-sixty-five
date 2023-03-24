# Dumping BootROM
*Some assembly required.*

# Table of contents
<!--ts-->
* [Dumping mt6589 BROM](#dumping-mt6589-brom)
   * [Obtaining SP Flash Tool](#obtaining-sp-flash-tool)
   * [Capturing USB traffic of SP Flash Tool and UART output](#capturing-usb-traffic-of-sp-flash-tool-and-uart-output)
   * [Reverse engineering the Download Agent](#reverse-engineering-the-download-agent)
   * [Patching Download Agent](#patching-download-agent)
   * [Hello, world!](#hello-world)
<!--te-->

# Dumping mt6589 BROM
Initially this part was meant to be more of a blog post than a clear and concise guide. I will eventually publish everything I used but please do not expect any common sense to be present here especially if you are actually experienced in reverse engineering and baremetal programming.

Dumping BootROM on modern Mediatek family (mt67xx) SoCs is quite a trivial task because we have [mtkclient](https://github.com/bkerler/mtkclient) that works in nearly automatic mode.

For slightly older devices we can always rely on modified generic payloads from the [bypass_payloads](https://github.com/chaosmaster/bypass_payloads) repository. 

However, for some reason even properly coded generic UART dump payload has never worked for me on mt6589. It felt like some hardware was either not initialized at all or initialized in some wrong way. Judging by Github commits no one has publicly shared mt6589 BROM dump at the time I started working on it so I decided to take a deeper look into what could I do.

## Obtaining SP Flash Tool
As we know, Mediatek developed their proprietary flashing software called SP Flash Tool. Its workflow could be approximated to something like the following:
1. Establish a connection with a target device (either via UART or USB). Connection can be made with devices booted into BROM and Preloader modes.
2. Identify the device and perform some very basic hardware setup procedure that depends on the target SoC using a small set of commands.
3. Extract a Download Agent for target SoC from `MTK_AllInOne_DA.bin`. Download Agent is a program compiled for specific SoC that provides rich set of commands and allows SP Flash Tool to perform ROM/RAM init, flashing etc.
4. Push Download Agent to target's SRAM at specific offset.
5. Jump to Download Agent.
6. Wait till DA performs HW initialization and sends first data back to SP Flash Tool (DRAM info, partition table etc.).
7. Execute commands to performs user-defined tasks (Formatting / Flashing / Memory test etc.)

My idea is to obtain the original DA for my SoC and make it execute my code right after initializing the on-board hardware.

I started by searching the oldest available SP Flash Tool build for Linux that still supported mt6589. By the time first Linux support was added to SPFT its developers already started dropping code for older platforms. For example, mt6575 and mt6577 were among the first to get their support removed from SPFT though their DAs remained in a few later versions of `MTK_AllInOne_DA.bin`. The first search result led me to the [download page at spflashtool.com](https://spflashtool.com/download/) where I got the archive with the Linux variant of SP Flash Tool v5.1648. Worth mentioning the website is tricky because it doesn't want us to access archives via direct links. Instead, it runs a script to add an event listener that appends a special request header on clicking the link. If you access the direct link without this header you will get redirected to the main page.

By the way, the Linux version is more useful than the Windows one because the `libflashtoolEx.so` has debug symbols unlike its Windows counterpart :) 

```
libflashtoolEx.so: ELF 64-bit LSB shared object, x86-64, version 1 (SYSV), dynamically linked, BuildID[sha1]=b570d3c0871606769140884647696f12d864c9b7, with debug_info, not stripped
```

## Capturing USB traffic of SP Flash Tool and UART output
After spending a few minutes on libpng-12 and udev errors I got SP Flash Tool to work on my computer. My next goal was to capture its USB traffic to be able to replay it later. In SPFT I loaded a scatter file for my device and added one Readback entry starting from 0x0 with length of 0x1000. *Here I omit the part about killing the PRELOADER partition on my device to get into the BROM mode*, though at this point it *should* work even with Preloader mode. I initialized usbmon with `modprobe usbmon` and fired up Wireshark. I also connected my device to UART to capture output on this bus, too.

The captured data can be split into a few parts for better understanding:
1. USB endpoint configuration.
2. BROM handshake.
3. SoC identification.
4. Basic HW setup.
5. DA push and execution.
6. Readback flow.

BROM commands are very well documented already by other folks so I won't describe them in detail and for steps 1-3 I will re-use code from [bypass_utility](https://github.com/MTK-bypass/bypass_utility). For step 4 I will analyze captured traffic and replay it programmatically verbatim *even if some commands make no sense* just to ensure absolute compatibility with SP Flash Tool flow.

For step 5 I needed to carve out the mt6589 DA first. Looking at the traffic capture made it trivial to find same bytes in `MTK_AllInOne_DA.bin` and extract the needed binary.

![mt6589 DA push in Wireshark](../images/brom-dump-001.png)

```
7z x -so "SP_Flash_Tool_v5.1648_Linux.zip" "SP_Flash_Tool_v5.1648_Linux/MTK_AllInOne_DA.bin" |\
    tail -c +767137 | head -c 141012 \
    > "mt6589-da-original.bin"
```

Of course I could have used [cyrozap's kaitai struct](https://github.com/cyrozap/mediatek-lte-baseband-re/blob/master/SoC/mediatek_download_agent.ksy) but:
1. I could not be arsed to fix Kaitai Web IDE issues in Firefox (it didn't open big files at the time of writing)
2. Back when I worked on mt6577 I remember `MTK_AllInOne_DA.bin` having older format that this kaitai struct did not support. As it turned out this struct should work with mt6589 but I didn't test it because see point 1.

With the original DA for mt6589 I can now try replaying the traffic and pushing it myself. For this matter I came up with what later became the `spft-replay` program. I based it on [bypass_utility](https://github.com/MTK-bypass/bypass_utility) by Dinolek and chaosmaster and repurposed it to suit my needs. The first thing I removed was Windows support and its DLLs :P The next thing to go was Preloader mode handling as I am working only with BROM. I also took an attempt at refactoring and reformatting the code. I doubt I succeeded at this because I don't use any IDE and rely solely on `isort`, `ruff` and `black`.

I decided to go the path of least resistance and did not implement traffic replay past the point after the device jumps to DA and sends some initial data (this part is highlighted on the picture below).

![mt6589 DA init data exchange in Wireshark](../images/brom-dump-002.png)

With UART hooked up to my device I pushed the original DA I carved out from Wireshark dump and watched for console output. Surprisingly it worked and printed the following lines:

```
Output Log To Uart 4
InitLog: 10:54:54 26000000 [MT6589]
GetNandID(), m_nand_acccon=0, m_chip_select=0
[SD0] Bus Width: 1
[SD0] SET_CLK(260kHz): SCLK(259kHz) MODE(0) DDR(0) DIV(193) DS(0) RS(0)
1501004D, 38473157, 41022557, 1844608F,
```

In other words, before the DA requests more data from SP Flash Tool it successfully prints those lines. Now I need to find a place where I can patch in a jump to my code.

## Reverse engineering the Download Agent
I loaded the original DA into Ghidra:

![Original mt6589 DA info in Ghidra](../images/brom-dump-003.png)

I searched for the usages of the string `Output Log To Uart 4` and Ghidra jumped to `FUN_12004088` which I renamed to `init_log` for conveniece. Then I jumped to `FUN_12003f7c` because it clearly is some `print` function. Looking at its contents in decompiler leaves no doubt it's `printf`. I renamed `FUN_12003f7c` to `printf_uart`.

Analyzing outgoing call tree of `printf_uart` revealed a few useful functions. I mapped them on the picture below after giving them normal names.

![Illustrated outgoing call tree of printf_uart](../images/brom-dump-004.png)

Lets get back to `init_log`. The first XREF of this function seems to be a goldmine - it looks like a global init function (`FUN_12001be8` renamed to `init`) that runs many initialization routines before jumping into the command loop (`FUN_120016d6` renamed to `command_loop`). This could be super useful in the future.

![init function in Ghidra](../images/brom-dump-005.png)

The last line printed on UART console looks like it was a printf format string. Large amount of parentheses makes me think so and I confirmed it by looking at `FUN_12013426` which I renamed to `set_sd_clk`. I did not understand how to configure the Function Call Graph tool to show all possible call trees between `init` and `set_sd_clk` so I opened the "Incoming Calls" pane of the Function Call Trees tool and entered `init` in the filter field:

![set_sd_clk incoming calls tree](../images/brom-dump-006.png)

All `set_sd_clk` invokations stemming from `command_loop` execute way too late, and DA does not reach such code after receiving just the initial data after jumping to DA.

Now there are just 4 different call trees originating from `init` left. I need to find the function after `init` that gets executed first. I opened `init` in disasm and looked at functions listed in the Incoming Calls tree:

![Functions in init that eventually call set_sd_clk](../images/brom-dump-007.png)

Looking at the addresses of the `BL` instructions it is obvious `FUN_12000ccc` is executed first and at some point this function causes the `[SD0] SET_CLK(260kHz): ...` line to be printed on UART. I opened `FUN_12000ccc` in decompiler and instantly noticed values similar to those in Wireshark.

![DA data exchange - Ghidra and Wireshark](../images/brom-dump-008.png)

At this point it's obvious that `FUN_12000c72` generates 5 separate transfers highlighted in green color. I will keep the `FUN_12000c72` call and patch the next one to jump to custom payload. The payload will be appended to the end of the original DA and it should be small enough to fit into SRAM. The original mt6589 DA is 141012 (0x226D4) bytes long and since we count bytes from 0 the last byte is 141011 (0x226D3) so our payload will start at 141012th byte.

## Patching Download Agent
Ghidra's "Patch Instruction" is quite inconvenient to use so I fired up [Online ARM to HEX converter](https://armconverter.com/). Of course I could have used tools like r2 and others but why should I when I have the online converter...

The instruction that jumps to custom payload will be located at `0x12000cda` and I pasted this value into the "Offset (hex)" field on webpage. The assembly code is trivial: `BL 0x120226d4`. I copied THUMB bytes (`12f0fbfc`) because the parent function is in Thumb mode.

Right now I'm planning to compile my first custom payload completely in Thumb mode because I plan to use some functions from DA that are Thumb and they also return to Thumb mode.

To not patch same instructions in other places (there are many byte sequences of `60688047` in the binary) I will extend to search pattern to include the previous instruction that will remain untouched. I don't really know how do professionals patch binary files and went with simple `xxd` and `sed` workflow:

```
xxd -c 256 -p "mt6589-da-original.bin" |\
    sed -e "s/fff7ccff60688047/fff7ccff21f0fbfc/" |\
    xxd -p -r \
    > "mt6589-da-patched.bin"
```

## Hello, world!
For starters, I decided to write a small payload that will use DA functions I found to print a few test values. There's nothing outstanding about it and you can check the source in the `payloads/hello-world-uart-da-api.s` . However there are few interesting points worth noting.

First, right after jumping we must reset all registers and stack pointer to guarantee proper execution flow. This is done in `payloads/init.s` - this file is compiled in such a way that the code is put into a separate `.text.init` section. Later I will tell `ld` to always put this section at start of the custom payload. After registers are cleared the init routine jumps to the main code.

Second is the `ld` script I wrote. My binary targets bare metal target and I use the `arm-none-eabi` toolchain [v11.2-2022.02 from ARM Developer](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads) to build it. At the beginning of script I define the only available memory sector that starts at ( (DA memory offset)+(custom payload offset) ). This way `ld` understands there is no read-only memory. Since I'm building for bare-metal there is no crt0 to perform common basic initialization such as copying sections from RO memory to RWX memory and zero-filling the `.bss` section. In fact, DA has already initialized not only its own sections but also set up essential hardware. As there is no RO memory everything left to do is to initialize the `.bss` section with zeroes. Of course I could implement some algorithm in `.text.init` section but as I'm going the path of least resistance I limited the max payload size to `0x200` bytes and made `ld` fill unused space with zeroes thus imitating already initialized `.bss` section. Resulting piggyback binaries will always be `0x200` bytes long but it's always possible to adjust the size.

The piggyback then is appended to patched DA file resulting in ready-to-use payload for `spft-replay`.

```
cat "mt6589-da-patched.bin" "mt6589-hello-world-uart-da-api-piggyback.bin" \
    > "mt6589-hello-world-uart-da-api-payload.bin"
```

I connected my device to UART console and pushed the payload:

```
spft-replay.py "mt6589-hello-world-uart-da-api-payload.bin"
```

![Hello world payload output](../images/brom-dump-009.png)

Success! My next step is to implement proper code for dumping BROM.
