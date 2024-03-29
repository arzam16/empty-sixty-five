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
    * [Figuring out I/O API](#figuring-out-io-api)
    * [The usb-dump payload](#the-usb-dump-payload)
* [Dumping mt6573 BROM](#dumping-mt6573-brom)
    * [SP Flash Tool issues](#sp-flash-tool-issues)
    * [UART issues](#uart-issues)
    * [reset_uart_and_log](#reset_uart_and_log)
* [chaosmaster's generic_dump](#chaosmasters-generic_dump)
    * [Function prologue](#function-prologue)
    * [LDR instruction](#ldr-instruction)
    * [Decoding LDR instruction bytes](#decoding-ldr-instruction-bytes)
    * [Fixing and defining the usbdl_put_data](#fixing-and-defining-the-usbdl_put_data)
    * [Sending the data](#sending-the-data)
* [chaosmaster's generic_uart_dump](#chaosmasters-generic_uart_dump)
* [Dumping mt6575 / mt6577 / mt8317 / mt8377 BROM](#dumping-mt6575--mt6577--mt8317--mt8377-brom)
    * [Replaying whole traffic isn't necessary](#replaying-whole-traffic-isnt-necessary)
    * [Standalone payloads](#standalone-payloads)
* [Dumping mt6580 BROM](#dumping-mt6580-brom)
    * [Bringing the dead smartphone to the minimum working condition](#bringing-the-dead-smartphone-to-the-minimum-working-condition)
    * [UART issues ensue](#uart-issues-ensue)
    * [Implementing a piggyback payload](#implementing-a-piggyback-payload)
    * [Looking for BROM itself](#looking-for-brom-itself)
* [Dumping mt6582 / mt8382 BROM](#dumping-mt6582--mt8382-brom)
    * [It was similar to mt6580](#it-was-similar-to-mt6580)
    * [Madskillz](#madskillz)
* [Dumping mt6252 BROM](#dumping-mt6252-brom)
    * [Figuring out the legacy command protocol](#figuring-out-the-legacy-command-protocol)
    * [RAM size detection](#ram-size-detection)
    * [1st and 2nd-stage Download Agents](#1st-and-2nd-stage-download-agents)
    * [Figuring out the legacy DA APIs](#figuring-out-the-legacy-da-apis)
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

I started by searching the oldest available SP Flash Tool build for Linux that still supported mt6589. By the time first Linux support was added to SPFT its developers already started dropping code for older platforms. For example, mt6575 and mt6577 were among the first to get their support removed from SPFT though their DAs remained in a few later versions of `MTK_AllInOne_DA.bin`. The first search result led me to the [download page at spflashtool.com](https://spflashtool.com/download/) where I got the archive with the Linux variant of SP Flash Tool v5.1648. Worth mentioning the website is tricky because it doesn't want us to access archives via direct links. Instead, it runs a script to add an event listener that appends a special request header on clicking the link. If you access the direct link without this header you will get redirected to the main page. **Update**: the Makefile has been changed to use the archived copy of SP Flash Tool hosted at archive.org.

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

## Figuring out I/O API
*I'm sure there's much better way to do things I'm about to do but I lack experience. If you are experienced in Ghidra get ready to cringe.*

Previously I found some calls in `FUN_12000ccc` for USB I/O operations.  They are referenced to as an offset to an address stored in `DAT_12000ef8`.

The address is `0x00102114`. In *MT6589 HSPA+ Smpartphone Application Processor datasheet / Version: 1.0 / Release date: 2012-12-11* on page 44 we can see the `0x0010_0000 - 0x0010_FFFF` region belongs to On-Chip SRAM.

![DAT_00102114](../images/brom-dump-010.png)

This pointer has only 6 references and jumping to the first one in the list reveals a function (`FUN_12000b4a`, later renamed to `setup_io_ops`) that seems to setup a variety of function pointers depending on the value of `param_1` (renamed to `io_type`). It's clear to me that `io_type` indicates either UART or USB because DA has no other way to communicate with PC.

For me it seems like `puVar1` in the decompiler window means usage of a struct to store said I/O function pointers. I renamed `PTR_DAT_12000ef8` to `ptr_io_ops`. Each branch of `if` statement sets 15 different pointers relative to `ptr_io_iops`.

I created a 60-byte struct called `io_ops_s` but it looks like I made a mistake somewhere because changing the type of `puVar1` from `undefined *` to `io_ops_s *` does nothing but prints some bullshit warning atop of the function in decompiler window:

![WARNING: Unable to use type for symbol puVar1](../images/brom-dump-011.png)

Instead, I created a `0x3c` bytes long uninitialized RW memory region at `0x102114` and set its type to `io_ops_s`. This makes it much easier to inspect usages of each pointer. It took me some time to figure out what each function in `io_ops_s` does, here's a very brief rundown:

1. `(off)` Init transport HW. Is used only in `FUN_12000bdc` (renamed to `init_io`).
2. `(off + 0x4)` Read 1 byte and return it
3. `(off + 0x8)` Read 1 byte into a buffer
4. `(off + 0xC)` Read N bytes `read(char* dst, uint len)`
5. `(off + 0x10)` Write 1 byte
6. `(off + 0x14)` Write N bytes `write(char* data, uint len)`
7. `(off + 0x18)` Write 1 byte but unused..?
8. `(off + 0x1C)` Read 2 bytes
9. `(off + 0x20)` Write 2 bytes
10. `(off + 0x24)` Read 4 bytes
11. `(off + 0x28)` Write 4 bytes
12. `(off + 0x2C)` Read 8 bytes
13. `(off + 0x30)` Write 8 bytes
14. `(off + 0x34)` Activate transport features (ignored for USB)
15. `(off + 0x38)` Set transport baudrate (ignored for USB)

## The usb-dump payload
After pointing out all the I/O functions I took their addresses and implemented a rather simple `usb-dump` payload in assembly that will dump hardcoded set of regions using newly found functions in DA. I chose to dump not only the BootROM but also whole SRAM and the DA itself as it now has many variables initialized. Could be useful for further reverse engineering.

In `spft-replay` I implemented the "receive mode" to save dumped regions to disk. There's also "greedy mode" I made mainly for debugging.

```
[2023-03-25 02:19:01,737] <REPLAY> -> DA: (OK) 5A
[2023-03-25 02:19:01,740] <INFO> Waiting for custom payload response
[2023-03-25 02:19:01,743] <INFO> Received HELLO sequence
[2023-03-25 02:19:01,749] <INFO> Reading 65536 bytes
[2023-03-25 02:19:05,216] <INFO> Saved to dump-1.bin
[2023-03-25 02:19:05,225] <INFO> Reading 65536 bytes
[2023-03-25 02:19:08,704] <INFO> Saved to dump-2.bin
[2023-03-25 02:19:08,715] <INFO> Reading 262144 bytes
[2023-03-25 02:19:22,479] <INFO> Saved to dump-3.bin
[2023-03-25 02:19:22,485] <INFO> Received GOODBYE sequence
[2023-03-25 02:19:22,486] <INFO> Closing device
```

Success! Now I've got the dump of mt6589 BROM, SRAM and DA.

Assembly is cool but when it comes to supporting more SoCs with different core types it gets much harder to maintain code. Considering this I took the following measures:
1. Rewrote 2 existing payloads in C. They will compile in A32 mode without optimizations and GCC will take care of calling DA APIs which are mostly T32.
2. Built init code as A32.
3. Changed DA patch from using `BL` instruction to `BLX`.
4. Bumped piggyback size to 0x800 bytes. This is 4 times more than the original but should be enough for whatever GCC outputs.

# Dumping mt6573 BROM

This SoC has ARM1176JZF-S core and if I wanted to keep writing in assembly I would definitely have had some issues regarding code compatibility. Having stuff written in C makes it GCC's headache, not mine.

My workflow to add mt6573 support will be similar to mt6589:
1. Capture SP Flash Tool traffic
2. Carve out the original DA
3. Teach `spft-replay` the traffic of mt6573
4. Patch original DA to make it jump to my code
5. ...
6. PROFIT!!!

## SP Flash Tool issues
My mt6573 device is old. Its on-board storage is NAND, not EMMC. Same version of SP Flash Tool I used for mt6589 successfully consumed a scatter for NAND but refused to do anything immediately after pushing DA. Looks like this version of software doesn't support NAND.

![NAND complaints from SP Flash Tool](../images/brom-dump-012.png)

I know SP Flash Tool for long enough to understand what kinds of bullshit can it generate. For example, having such an ouroboros is totally possible:

![SP Flash Tool trying to handle mt6573](../images/brom-dump-013.png)

The `MTK_AllInOne_DA.bin` found in the Linux distribution of SP Flash Tool v5.1648 **does** support mt6573:

![mt6573 DA in MTK_AllInOne_DA.bin from SPFT v5.1648](../images/brom-dump-014.png)

Looks like the NAND support depends on host SPFT application, not on DA itself. I started my Windows computer (the only reason for this is there are more archive versions for Windows than for Linux) and began testing SP Flash Tool distributions older than v5.1648 but I shoved them the DA from v5.1648. It took me some time to figure out that the latest version of SP Flash Tool for Windows that supports mt6573 with NAND is v5.1624.

I set up Wireshark and USBPcap and shortly after got the traffic dump I was looking for. The dumped traffic allowed me to carve out the original DA for mt6573 and implement support for this SoC in `spft-replay`.

Adding support for mt6573 in payloads was just a matter of finding some function addresses in its original DA and putting them into header files, as well as adding a new target to Makefile.

Unfortunately, things didn't go as well as expected. Despite USB dump payload working properly the "Hello world" payload doesn't print anything at all. I will fix it next.

## UART issues
When I run the readback flow in the original SP Flash Tool I *do* see the UART logs:

```
Output Log To Uart 4
InitLog: 10:53:14 61440000 [MT6573]
Page size in device is 2048
[RS] (9001B234: 4DC8)
[LIB] Security PreProcess : 16:08:11, Nov  9 2016
[LIB] Flash Detect Results : (0x0, 0xC4D, 0xC4F)
[LIB] Search NAND
[LIB] ROM_INFO not found in NAND
...
(snip)
```

The first line printed after `init_log` is called is `Page size in device is 2048` and it's printed in `FUN_9000b0ee` (renamed to `request_storage_settings`). This function seems to request NAND init parameters (56 bytes) from SPFT in a loop (response is `0x69` to try the next param) until suitable ones are detected (response is `0x5A`). The parent function seems to perform some kind of storage initialization, I renamed this function to `init_storage`.

I returned to the `init_log` function and noticed it has 2 references. I generated a graph:

![init_log call graph](../images/brom-dump-015.png)

Turns out I was really close because `init_storage` calls something that invokes `init_log` just before requesting NAND init params and printing the `Page size in device is 2048` line.

## reset_uart_and_log
After inspecting this function (`FUN_90009e64`, renamed to `reset_uart_and_log`) and its outgoing calls it became clear that on mt6573 the first `init_log` call is kinda ignored and printing stuff to UART won't work until `reset_uart_and_log` is called by `init_storage`.

Now I just need to add this call to my `hello-world-uart` payload and it should work. Aaand...

![mt6573 hello-world-uart payload output](../images/brom-dump-016.png)

... *ta-da!* The introduced call doesn't seem to harm the mt6589 variant of payload so I decided to not guard it with `#ifdef TARGET_MT6573` but kept the appropriate Makefile change for setting a `TARGET_MTxxxx` for future. **Update**: after adding mt6582 support I started referring to this function as to `DA_init` for piggyback payloads. The platforms that don't require any additional initialization will have an empty `DA_init` function in their respective `da-api.h` headers.

# chaosmaster's generic_dump
The `generic_dump` payload found in the [bypass_payloads](https://github.com/chaosmaster/bypass_payloads/blob/master/generic_dump.c) is quite an interesting solution worth explaining.

Not only it's a small and effective payload but it also has on-the-fly disassembly technique implemented.

Actually, *both* DA and BROM have their own I/O function tables. The idea of this payload is to derive a pointer to the table of I/O functions similar to [those described above](#figuring-out-io-api) and use it to call `usbdl_put_data(uint32_t* src, uint32_t len)` providing the base address of the BROM and its size.

To better illustrate what's really going on, I will use the BROM dump from [MT8382V](https://github.com/arzam16/SoC-BootROMs/blob/main/mediatek/mt8382v.bootrom.bin). This SoC shares the same registers with MT**65**82. I loaded this dump into Ghidra and set the base address to 0x0:

![Memory map of mt6582](../images/brom-dump-017.png)

## Function prologue
Various families of Mediatek SoCs have different locations of BROM. This code scans predefined set of supposed addresses ( `uint32_t brom_bases[]` ) for a first address that has specific pattern defined in `uint16_t search_pattern[]`.

```
__attribute__ ((section(".text.main"))) int main() {
	send_word = 0;
	uint32_t i = 0;
	for (i = 0; i < (sizeof(brom_bases) / sizeof(*brom_bases)); ++i) {
		send_word = (void *)searchfunc(brom_bases[i] + 0x100, brom_bases[i] + 0x10000, search_pattern, 4);
		if (send_word) break;
	}
```

This pattern is a *function prologue* - a small routine put by the compiler in the beginning of the function. In our case it saves values of registers to stack.

It's very important to understand the function prologues **do** differ, it's just a really good coincidence this one is found in majority of BROMs. But how do we dump the BROM if we don't know the exact byte pattern? In this case we can dump it over UART. It is not as convenient as USB dump but it should work on all Mediatek devices. More on this in the next chapter.

Since the searched function is supposed to be in Thumb mode, we scan 16-bit sequences instead of 32-bit. The function prologue defined in `search_pattern[]` disassembles to this code:

```
2d e9 f8 4f     push       {r3,r4,r5,r6,r7,r8,r9,r10,r11,lr}
80 46           mov        r8,r0
8a 46           mov        r10,r1
```

Lets search this signature in Ghidra. In the source code the `search_pattern[]` values are big endian, we have to account for that. It's important to separate each 16-bit value with spaces otherwise Ghidra will treat it as a single huge number instead of a set of values.

![Searching a function prologue in Ghidra](../images/brom-dump-018.png)

In case of MT8382 BROM the search yielded 2 results but since the `searchfunc` returns the address of the first result the `send_word` variable is going to take the value of `0xA49E + 1 = 0xA49F`. 1 is added to properly indicate that function as Thumb code:

```
if (++matched == patternsize) return offset | 1;
```

![2 functions found](../images/brom-dump-019.png)

Lets jump to the first search result, too.

## LDR instruction
If we look at the disassembly listing we will see the following:

```
0000a49e 2d e9 f8 4f     push       {r3,r4,r5,r6,r7,r8,r9,r10,r11,lr}
0000a4a2 80 46           mov        r8,r0
0000a4a4 8a 46           mov        r10,r1
0000a4a6 55 48           ldr        r0,[DAT_0000a5fc]
0000a4a8 87 68           ldr        r7,[r0,#0x8]=>DAT_001027c8
0000a4aa c6 68           ldr        r6,[r0,#0xc]=>DAT_001027cc
```

The ARM processor has 12 general-purpose registers for storing data. They are somewhat similar to variables we see in programming languages.

Lets focus on the `ldr` instructions:
1. The first `ldr` instruction puts whatever value is stored at the address `0x0000a5fc` into register `r0`. This value is an address of the table of BROM I/O functions.
2. The second `ldr` instruction takes a value at `r0`, adds `0x8` to it and loads a value from the resulting address into register `r7`.
3. The third `ldr` instruction takes a value at `r0`, adds `0xc` to and and loads a value from the resulting address into register `r6`.

In the decompiler window we can see the C-pseudocode equivalent of said instructions:

```
pcVar2 = *(code **)(DAT_0000a5fc + 8);
pcVar1 = *(code **)(DAT_0000a5fc + 0xc);
```

## Decoding LDR instruction bytes
In `generic_dump` there's following code. I reformatted it for better understanding

```
int (*(*usbdl_ptr))() = (void *)(
	ldr_lit(
		(uint32_t)send_word + 7,
		((uint16_t*)(send_word + 7))[0],
		0
	)
);
```

The `ldr_lit` function returns an absolute address referenced by the `ldr` instruction. It takes the address of an `ldr` instruction and its bytes. In our case the needed `ldr` instruction is stored at `prologue address + 7 = 0xA4A6`, and its bytes are `0x5548` as seen in Ghidra. The Ghidra representation of Hex is big-endian and we have to account for that. In fact the processor is little-endian and first reads `0x48` then `0x55`. The last argument is `0` and is not used.

To understand what the code in `ldr_lit` function actually does we have to understand how said `LDR` instruction is encoded. Here's an excerpt from the [ARM7 TDMI Manual](https://web.archive.org/web/20221211173239/http://bear.ces.cwru.edu/eecs_382/ARM7-TDMI-manual-pt3.pdf), page 16:

![Format of Thumb-encoded LDR instruction](../images/brom-dump-020.png)

The first line in `ldr_lit` extracts the `imm8` part of the instruction. The actual value is 10 bit long but it's able to store it in an 8-bit because 2 bits are always zero as the target address must be aligned by 4 which means 0th and 1st bit are always zero. The `imm8` value in our case is `0x55`.

```
uint8_t imm8 = instr & 0xFF;
```

The next line extracts the ID of a register (0~12) and writes it to a variable. However in our case we don't need to know the exact destination register and this `if` branch is not executed.

```
if (Rt) *Rt = (instr >> 8) & 7;
```

The next line rounds the Program Counter register value *downwards* by 4. The `curpc` variable stores the address of our `ldr` instruction. In Thumb mode instructions can fit into 16-bytes but `ldr` wants 4-bytes alignment.

```
uint32_t pc = (((uint32_t)curpc) / 4 * 4);
```

an alternative way to do this would be:

```
uint32_t pc = curpc & ~0b11; // clear the first 2 bits
```

As result, `pc` value is `0xA4A6 / 4 * 4 = 0xA4A4`.

The next line does the following:
1. First, it extends the `imm8` from 8 to 10 bytes by multiplying it by 4. It is the same thing as shifting it left by 2. The value in brackets is `(0x55 * 4) = (0x154)`.
2. We add 4 because the manual says so: "*The value of the PC will be 4 bytes greater than the address of this instruction*".
3. Everything is added up to form an address where the BROM I/O table pointer is stored at.

```
return (uint32_t *)(pc + (imm8 * 4) + 4);
```

As result, `ldr_lit` returns `(0xA4A4 + 0x154 + 4) = 0xA5FC`.

`0xA5FC` is the address that holds an address (so, a pointer) to the BROM I/O table. We can check in Ghidra our calculations were correct:

![0x0000a5fc address loaded in Ghidra](../images/brom-dump-021.png)

When `ldr_lit` returns an address it is casted to an array of functions:

```
int (*(*usbdl_ptr))() = (void *)(ldr_lit(...));
```

## Fixing and defining the usbdl_put_data
I must admit the MT8382 example is quite bad because the provided dump does not have a SRAM dump where the actual function table is located. In general, it lists pointers to various functions just like the Download Agent [does](#figuring-out-io-api) but just a little bit different. This BROM has the following table:
1. `(off)` some USB function
2. `(off + 0x4)` some USB function
3. `(off + 0x8)` `write(char* data, uint len)`
4. `(off + 0xC)` `flush()`
5. `(off + 0x10)` some USB function
6. `(off + 0x14)` some USB function

The next line of code overwrites the I/O function table once to fix a pointer to the `write` function. It might be not all Mediatek BROMs need that fix, though.

```
//Fix ptr_send
*(volatile uint32_t *)(usbdl_ptr[0] + 8) = (uint32_t)usbdl_ptr[2];
```

The part of code defines a C helper function called `usbdl_put_data` for sending arbitrary data to PC using the I/O functions. First the function calls the `write` function (`usbdl_ptr[2]` takes the 3rd function from the table) and then flushes the USB buffer, completing a transfer (`usbdl_ptr[3]` takes the 4th function from the table).

```
int usbdl_put_data(void* data, uint32_t size) {;
	(usbdl_ptr[2])(data, size);
	return (usbdl_ptr[3])();
}
```

## Sending the data
The following line defines a magic value with forced big-endianness:

```
int ack = __builtin_bswap32(0xC1C2C3C4);
````

If `__buildin_bswap32` wasn't used the PC would have received `0xC4C3C2C1` instead.

The next line sends the magic value. This payload is meant to be used with [bypass_utility](https://github.com/MTK-bypass/bypass_utility) and the program *does* [expect this value](https://github.com/MTK-bypass/bypass_utility/blob/87a2541820ad22e7cc00d0bd51a3a8faff6c21ef/main.py#L110). Once the program receives `0xC1C2C3C4` it starts receiving `0x20000` bytes from USB and saving them to disk. The payload, in its turn, dumps the whole BootROM:

```
usbdl_put_data((void *)brom_bases[i], 0x20000);
```

The payload then attempts to shutdown the device by triggering the hardware watchdog and entering an infinite loop that will be interrupted when watchdog resets the device on timeout.

```
// Reboot device, so we still get feedback in case the above didn't work
wdt[8/4] = 0x1971;
wdt[0/4] = 0x22000014;
wdt[0x14/4] = 0x1209;

while (1) {

}
```

# chaosmaster's generic_uart_dump
Running this payload allows dumping memory without relying on location of I/O functions table in BROM. Mediatek SoCs use the same HW IP for UART and usually only the base register addresses differ. It's easy obtain them by analyzing the kernel source code or reading a datasheet.

`uart_base` should of the UART used by BROM (usually UART1) to avoid using uninitialized ports.

This payload reads the specified memory region byte-by-byte and prints each byte in HEX-encoded form using the `low_uart_put` function.

`uart_reg0` is a status register and the `while` loop is here to wait until the 5th bit (`0x20`) is set which means the FIFO buffer is ready to accept new data.

Once the wait cycle is complete the byte is written to the `uart_reg1` register.

# Dumping mt6575 / mt6577 / mt8317 / mt8377 BROM
## Replaying whole traffic isn't necessary
My previous undocumented experiments showed that on these platforms the BootROM initializes hardware enough to just push a payload without depending on the patched DA and even replaying SP Flash Tool traffic (to some extent).

These SoCs are very similar to each other. The mt8317 which is closer to mt6577 still identifies itself as `0x6575` which is weird. The `MTK_AllInOne_DA.bin` found in the SP Flash Tool v5.1648 distribution contains different DAs for the following platforms:

| HW code | HW subcode            | HW version | SW version |
|---------|-----------------------|------------|------------|
| 0x6575  | (not checked in SPFT) | 0xCA00     | 0xE100     |
| 0x6575  | (not checked in SPFT) | 0xCB00     | 0xE201     |
| 0x6577  | (not checked in SPFT) | 0xCA00     | 0xE100     |

I implemented the `identify` mode in `spft-replay` to conveniently identify my hardware. I've got an mt8317-based tablet and an mt6575-based phone. Both identified as following:

```
<INFO> Waiting for device in BROM mode (0E8D:0003)
<INFO> Found device
<INFO> Handshake completed!
<INFO> HW code: 6575
<INFO> HW subcode: 8B00
<INFO> HW version: CB00
<INFO> SW version: E201
```

So I implemented traffic replay for these specific IDs only (for now). But in general on this SoC family it should be OK to just disable the watchdog and push the payload.

## Standalone payloads
I wrote 2 simple standalone payloads. The first one, `hello-world-uart`, works in the same way as its piggyback counterpart. The second one, `uart-dump`, dumps specified regions as HEX-encoded strings. At least on mt8317 standalone payloads can only output to UART1 that has been initialized by BROM before jumping to the payload. If I ever make piggyback payloads they should work with UART4.

Standalone payloads share some common code so I moved it out to a separate `standalone-util.c` file.

# Dumping mt6580 BROM
## Bringing the dead smartphone to the minimum working condition
I've got a broken smartphone of a forgotten origin that later identified as mt6580. The phone had no back cover and no battery. Main PCB was supposed to be connected with the bottom sub-board using the 32-pin Flat flexible cable. Unfortunately the bottom sub-board has gone too and all I had was a motherboard connected to the display and the cracked touchscreen. There were no useful identifiers on the motherboard except one sticker. Searching the text from sticker on the internet yielded only one sane result leading to some russian-speaking forum where the poster has been asking for firmware for this device saying he was unable to find one, as well as claiming he got scammed because he paid for a Sony Xperia phone but received this fake device.

The phone didn't have USB port because it was supposed to be on sub-board. I did some very crude soldering to connect the battery and the microUSB port. A 10-kOhm resistor was used to fool the PMIC into thinking the battery is connected and is not overheating. Thankfully the board had all the necessary pins exposed as test points. However, unlike other Mediatek devices I have this one exposes only a single UART port for all types of output which brings some inconvenience because the BROM outputs at 115200 baud and everything else is at 921600.

![Poor mt6580 fake phone after my manipulations](../images/brom-dump-022.jpg)

## UART issues ensue
mt6580 is a modern SoC compared to mt6577 and others I had already worked on, and I expected that I could just load the standalone `uart-dump` payload and this is it. Well yes, but actually no. First, the `DA_reset_uart_and_log` call kept halting the program so I had to finally disable this call not only for this SoC but also for mt6589 as I initially planned. Second, I don't know what was the exact culprit but I've been always getting corrupted output via UART that looked like sudden random bit errors. Here's the comparison of the BROM I dumped over UART (on the left) with the dump I later made over USB (on the right).

![BROM dump comparison](../images/brom-dump-023.png)

I tried changing the wires, the ground pad, the USB-UART dongle but I still had bit errors at the rate of 1 per ~30 kB of data.

![🤡](../images/brom-dump-024.png)

I *did* dump the BROM over UART by splitting it in 4 equally-sized sectors and dumping each one 5 times, applying a simple "best of 5" error-correction algorithm. But I wasn't satisfied with the process so I started working on a piggyback payload that would dump the BROM via USB.

## Implementing a piggyback payload
The workflow for implementing a piggyback payload has already been established and tested so I just carve out the mt6580 DA, do some RE to find necessary function addresses, find a place to patch-in a hook instruction and put my payload on top of it.

The original DA produces the following log (bottom half has been cut):

```
Output Log To Uart 1
InitLog: Nov 30 2016 11:02:57 26000000 [tJ��Iɲ��I������@��pG-��GF]
DA build time : Nov 30 2016 11:02:53
DA arg_size=0x8F4, flags=0x0,
DA do releasing DRAM.
[DDR Reserve] ddr reserve mode not be enabled yet
RGU rgu_release_rg_dramc_conf_iso:MTK_WDT_DEBUG_CTL(590200F1)
RGU rgu_release_rg_dramc_iso:MTK_WDT_DEBUG_CTL(590200F1)
RGU rgu_release_rg_dramc_sref:MTK_WDT_DEBUG_CTL(590200F1)
DDR is in self-refresh. 200F1
DDR is in self-refresh. 200F1
DDR is in self-refresh. 200F1
Defalt reg_wdt_mode value is 0x64
After Disable WDT, reg_wdt_mode value is 0x64
Config PLL use DA's setting.
SAL_PLL_Setup(2 211E30 0)
SAL_PLL_Configure_All_Ex(2)
[PWRAP] pwrap_init_DA
[PWRAP] pwrap_init
[PWRAP] _pwrap_init_sistrobe [Read Test of MT6350] pass,index=0 rdata=5AA5
(................ snip ................)
[PWRAP] _pwrap_init_sistrobe [Read Test of MT6350] tuning,index=23 rdata=6A97
[PWRAP] _pwrap_init_reg_clock
[PMIC_WRAP]wrap_init pass,the return value=0.
AP_PLL_CON1= 0x3C3C23C0
(................ snip ................)
DISP_CG_CON1= 0x0,
start power down
i: 3
i: 2
i: 1
power down Done
```

I decide to make a jump to the piggyback before the DA starts powering something down. According to the captured traffic of SP Flash Tool the DA is loaded at `0x200000`. Considering that, the `init` function is at `0x201424`, `init_log` is at `0x201DC0`, `printf_uart` is at `0x201C84` and so on. I couldn't come up with a better name for this function so `init_power_down_something` gets called in `init` at `0x2014E4`. This is the perfect place to cram a jump to piggyback in.

![Perfect place for a jump instruction](../images/brom-dump-025.png)

Judging by the previous SoCs, this piggyback should've worked from kick start. But suddenly it didn't. The last printed log line is `DISP_CG_CON1= 0x0,` meaning the jump **did** happen but there was absolutely no action afterwards. I checked if the function addresses I filled into the `da-api.h` were correct and they indeed were, I checked if I were building for mt6580 with correct CFLAGS and they were also correct.

I was still thinking in wrong direction about some instruction in the piggyback might be not working properly so I came up with the simpliest test pigyback ever: a single `BLX 0x2014C2` instruction that should have printed a single debug message on UART. However it didn't, meaning the jump **to** the piggyback worked and the jump **from** the piggyback did not.

If you are experienced you already know what exactly was wrong. The root of the problem was in front of my eyes in Ghidra all the time however I didn't ever notice it.

At some point I asked my friends for help and [nergzd723](https://github.com/nergzd723) suggested to check if the piggyback actually lands on device. I could indeed see it getting transferred over USB in Wireshark. His next suggestion was to somehow check the actual contents of the piggyback after transferring it to the target device. For this purpose I found a big function in the middle of DA that was unused (or at least not getting called on my device) at `0x209EA0`. I filled it with `nop`s and then implemented a simple loop that iterates through the first bytes of piggyback and prints them on UART using the `print_hex_uart` function at `0x201C52`. I still concatenated the piggyback on top of DA but instead of jumping to it I jumped to the modded debug function at `0x209EA0`. After loading the DA I saw the following:

```
(................ snip ................)
DISP_CG_CON1= 0x0,
00000000E3A03000E3A04000E3A05000E3A06000E3A07000E3A08000E3A09000
```

And I suddenly got it. The DA has been using additional memory right after its body instead of some other SRAM region. This didn't happen with the other SoCs so far. I added a test zero-filled region to see how far does the memory usage go:

![Test zero-filled region](../images/brom-dump-026.png)

After re-analyzing the binary the furthest Label was detected at `0x21575C` which is 17460 bytes further away from DA body. My "fix" was to pad the original DA with zeroes. I went with 17624 additional bytes and the resulting original DA binary is now 88064 bytes long, was 70440. Adding zero bytes takes place in Makefile.

![New mt6580 piggyback structure](../images/brom-dump-027.png)

After padding the DA and concatenating the piggyback on top, it started working!

## Looking for BROM itself
In *MT6580 WCDMA SoC Application Processor Functional Specification / Version: 1.2 / Release date: 2015-08-10* on page 118 we can see the `0x0040_0000 - 0x0040_FFFF` region belongs to "Boot ROM" and `0x0100_0000 - 0x0100_3FFF` belongs to "On-chip SRAM", however dumping these regions yielded the following result:

![The contents of Boot ROM and On-chip SRAM regions whose addresses were taken from the official datashit](../images/brom-dump-028.png)

Further reading the datasheet (*3.2.2 Boot Slave* on page 118) I learned that SoC remaps the boot code, and there should be machine instructions at `0x00000000`. I try to dump from this offset and voi-la, I've got a valid BROM dump!

To find SRAM base I loaded the BROM dump into Ghidra and launched [starfleetcadet75](https://gist.github.com/starfleetcadet75)'s [FindInvalidMemoryReferences.java script](https://gist.github.com/starfleetcadet75/cdc512db77d7f1fb7ef4611c2eda69a5) to list all references to undefined memory addresses. Among many references to hardware registers there were lots of accesses of the region `0x0010_0000 ~ 0x0011_0000`.

![The output of FindInvalidMemoryReferences.java script](../images/brom-dump-029.png)

Looks like in my case this *is* the correct part of SRAM where BROM stores its data. At this point it was just a matter of time to fill the values into `hw-api.h` and run `spft-replay` in dump mode.

Later I verified a trimmed (it dumps more data than needed) BROM dump obtained with chaosmaster's bypass_utility with what I've got with my `spft-replay` and the hashes matched.

# Dumping mt6582 / mt8382 BROM
## It was similar to mt6580
After implementing support for mt6580, adding mt6582 was a breeze. The flow is quite similar between the two SoCs however there are some interesting details:
1. The data exchange between the original SP Flash Tool v5.1648 and the target device was *very* short. Everything boiled down to identifying the SoCs, reading a single EFUSE register and pushing the DA right afterwards.
2. SP Flash Tool didn't bother disabling the watchdog on mt6582. I haven't checked if BROM disables it by itself but I was afraid the standalone `uart-dump` would not have enough time to complete the work and it would be interrupte. **It is the first time I modify the original SP Flash Tool traffic** adding a function to disable the watchdog.
3. Unlike mt6580, the original DA on mt6582 uses the most of its available memory (refered to as "Share SRAM" in the datasheet) and I could not come up with some specific padding offset. I kept increasing padding hoping the DA would stop overwriting the piggyback at some point. Some DA data remains after the piggyback body because of that. This is wrong and most likely will break things if someone plans to use more DA APIs in the future that could have used these memory regions.

## Madskillz
The mt6582 part of the writeup seems to be small, so here's a photo of one of devices I've been working with.

![The remains of the Huawei Y3II phone](../images/brom-dump-030.jpg)

# Dumping mt6252 BROM
## Figuring out the legacy command protocol
My next device was a fake Smasgnu i9100 feature phone based on the MT6252CA SoC. This SoC is not even in the mt65xx family, but I was eager to try my skills.

The first thing I tried was the identification mode of `spft-replay`, and it failed immediately. The target device exposed its 0E8D:0003 USB device and even completed the handshake, but it didn't respond to the `0xFD` (`get_hw_code`) command.

My next logical step was to fire up the SP Flash Tool, but then I realized the device is way too old to be supported by v5.1648 because the more or less modern versions of SP Flash Tool don't even support NAND memory, let alone SPI memory, which was exactly my case.

I ended up in the 4PDA thread about the [Smart Watch Phone DZ09](https://4pda.to/forum/index.php?showtopic=670733), which contains a huge amount of useful info on smartwatches and mt62xx SoCs in general. Luckily, Russian is my native language, so I can understand everything. I downloaded [SP Flash Tool v5.1308](https://4pda.to/forum/index.php?showtopic=615788&view=findpost&p=36244514) and [some scatter file](https://4pda.to/forum/index.php?showtopic=670733&view=findpost&p=49241203) and started experimenting. I found it weird that the SP Flash Tool distribution was labeled as v5 but it looked like an early v3.

I captured the USB traffic for the usual procedure of reading 0x1000 bytes starting from 0x0 and started analyzing it. Running SP Flash Tool in "Runtime Trace Mode" was very useful because it produced tons of verbose logs. It made my job a lot easier, as the logs literally self-documented the old command protocol and a few other important routines. With logs like these, I never had to reverse-engineer the `BROM.DLL` module.

```
BROM_DLL[1564][2888]: BRom_Base::SetBRomCommTimeouts(): SetCommTimeouts() OK! , COMMTIMEOUTS={ 0, 1, 50, 1, 700 }. (brom_base.cpp:220)
BROM_DLL[1564][2888]: BRom_AutoBoot::BRom_StartCmd(0): [0] 0xA0 -> 0x5F     (brom_autoboot.cpp:263)
BROM_DLL[1564][2888]: BRom_AutoBoot::BRom_StartCmd(0): [1] 0x0A -> 0xF5     (brom_autoboot.cpp:263)
BROM_DLL[1564][2888]: BRom_AutoBoot::BRom_StartCmd(0): [2] 0x50 -> 0xAF     (brom_autoboot.cpp:263)
BROM_DLL[1564][2888]: BRom_AutoBoot::BRom_StartCmd(0): [3] 0x05 -> 0xFA     (brom_autoboot.cpp:263)
BROM_DLL[1564][2888]: BRom_Base::BRom_ReadCmd(): 0x80000000[1]={ 0x0001 }     (brom_base.cpp:578)
BROM_DLL[1564][2888]: BRom_Base::BRom_ReadCmd(): 0x80000008[1]={ 0x00C3 }     (brom_base.cpp:578)
BROM_DLL[1564][2888]: BRom_Base::BRom_ReadCmd(): 0x8000000C[1]={ 0x0000 }     (brom_base.cpp:578)
BROM_DLL[1564][2888]: Old chip-recognition flow... (brom_base.cpp:1654)
BROM_DLL[1564][2888]: BRom_Base::BRom_ReadCmd(): 0x80010000[1]={ 0xCF00 }     (brom_base.cpp:578)
BROM_DLL[1564][2888]: BRom_Base::BRom_ReadCmd(): 0x80010008[1]={ 0x6250 }     (brom_base.cpp:578)
BROM_DLL[1564][2888]: BRom_Base::BRom_ReadCmd(): 0x8001000C[1]={ 0x8B00 }     (brom_base.cpp:578)
BROM_DLL[1564][2888]: New chip-recognition flow... (brom_base.cpp:1565)
BROM_DLL[1564][2888]: BRom_Base::BRom_ReadCmd(): 0x80010000[1]={ 0xCF00 }     (brom_base.cpp:578)
BROM_DLL[1564][2888]: BRom_Base::BRom_ReadCmd(): 0x80010004[1]={ 0x0101 }     (brom_base.cpp:578)
BROM_DLL[1564][2888]: MT6252_S0101: Target H/W: DigitalDie={ hw_ver(0xCF00), sw_ver(0x0101), hw_code(0x6250), hw_sub_code(0x8B00) }, AnalogDie={ hw_ver(0x0000), hw_code(0x0000) } (brom_base.cpp:1821)
BROM_DLL[1564][2888]: BRom_AutoBoot::BRom_StartCmd(0): Pass! (brom_autoboot.cpp:289)
BROM_DLL[1564][2888]: BRom_Base::CreateObject(): MT6252(37), EXT_26M(2), p_bootstop(0x005DAF28), ms_boot_timeout(268435455), max_start_cmd_retry_count(1). (brom_base.cpp:1370)
BROM_DLL[1564][2888]: Boot_FlashTool(): DA_HANDLE->rwlock: READ_LOCK ... (rwlock.cpp:291)
```

Reading the logs allowed me to implement the basic identification mode for mt62xx devices. This mode will only read the Chip IDs on this SoC family. Reading ME ID and Target Configuration is not supported on the BROM level.

The most significant difference I saw later in Wireshark was a different set of command codes, and the target device didn't send back the status codes like the mt65xx SoCs do. Fortunately, the commands still worked the same way, so it was just a matter of implementing the `check_status` flag and sending an alternative "legacy" command code in `brom.py`.

## RAM size detection
While I think it's completely unnecessary, I still implemented the RAM size detection algorithm to ensure maximum compatibility with the official workflow. SP Flash Tool writes some set of values at increasing offsets and checks them in descending order. The logic behind this is if the value could not be read back, the memory at this location is unreachable.

I could not figure out exactly how SP Flash Tool generated the values for testing the RAM, so I decided to spice up my code with `import random`. While the test values do differ from the "official" ones, the flow remains the same.

## 1st and 2nd-stage Download Agents
Behind the scenes, usually, I just export payload bytes from the Wireshark dump and push them to the target device as-is to see how far it would let me go without requiring more data from the host PC. The mt62xx, however, seems to be different.

First of all, the `MTK_AllInOne_DA.bin` had **45** Download Agents. Looking at them in Kaitai Web IDE with cyrozap's .ksy loaded reveals each SoC has at least 2 different DA configurations depending on the value of `unk2`.

Each DA configuration has **4 to 6** loadable regions, while it's just **3** on mt65xx (the first and last ones are usually some digital signature crap, and the 2nd one is the DA body itself). At the time of writing, I still haven't figured out the purpose of all these regions. A to-do for the future me: write a script for extracting DAs by a given SoC ID instead of relying on hardcoded file offsets in the `Makefile`.

The multi-stage Download Agents were another interesting aspect. Initially, the SP Flash Tool pushes a small binary to one offset, then the larger DA to another offset, and jumps to the first binary. A quick RE revealed that the 1st-stage DA performs pre-initialization routines and jumps to a hardcoded offset where the primary DA awaits launch.

The way these binaries are pushed is also interesting. On mt65xx, there's the `0xD7` command (`send_da`) that sends a target memory offset, payload size, and signature length followed by the executable binary. For mt62xx, SP Flash Tool seems to send a target memory offset, **half the payload size**, followed by the executable binary **except for the endianness change**. The code is stored in `MTK_AllInOne_DA.bin` as little-endian, is received by the target as little-endian, but pushed as big-endian. For some reason, I didn't pay attention to this detail and spent a day trying to understand why my code wasn't working. Thankfully, everything is sorted out now. The only thing I don't like in the current code is the hardcoded path for the 1st-stage DA for mt6252.

## Figuring out the legacy DA APIs

The 2nd-stage DA loaded fine in Ghidra with the following settings:

| Parameter    | Value                 |
|--------------|-----------------------|
| Language ID  | ARM:LE:32:v5t (1.107) |
| Compiler ID  | default               |
| Processor    | ARM                   |
| Endian       | Little                |
| Address Size | 32                    |
| Base address | 08100000              |

The decompiled code is nice, but sometimes the functions are long or not straightforward. I tried using OpenAI's ChatGPT (the free v3.5 model), asking it to explain the code and suggest how I could rename some variables. I was actually impressed! While not 100% accurate, ChatGPT was *mostly* on point and gave concise explanations. Then I learned these plugins exist:

* [Ghidra: GptHidra](https://github.com/evyatar9/GptHidra) (suggested by [Ristovski](https://github.com/Ristovski))
* [IDA: Gepetto](https://github.com/JusticeRage/Gepetto)

| Function address | How I renamed it | Description                                                                                                                                                        |
|------------------|------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `0x081036a6`       | init             | Initialize peripherals and process incoming commands one by one. Enter infinite loop (halt) upon receiving specific commands                                       |
| `0x081036a6`       | handle_command   | Run routines based on the received command code                                                                                                                    |
| `0x08112898`       | memcmp           | Perform a byte-wise comparison between two memory blocks and return the difference when encountered or  0 if both blocks are identical within the specified length |
| `0x08100116`       | memcpy           | Copy a memory block from one location to another                                                                                                                   |
| `0x0810bd4c`       | memsearch        | Search for a specific pattern within a memory range, returning the location of the pattern if found                                                                |
| `0x08100154`       | detect_ram       | Determine memory boundaries                                                                                                                                        |
| `0x08100028`       | dumb_wait        | Delay loop                                                                                                                                                         |
| `0x08100028`       | init_storage     | Query internal storage settings from the PC                                                                                                                        |
| `0x08112820`       | just_jump        | Jump to far destinations. Few more functions after just_jump do the same except they also allow to carry the arguments                                             |
| `0x0810896c`       | neutered_print   | Neutered debug function to print text. Basically an infinite loop                                                                                                  |
| `0x0810896c`       | setup_io_ops     | Configure io_ops based on selected transport (UART/USB)                                                                                                            |

The I/O API is quite similar to the one described in [Figuring out I/O API](#figuring-out-io-api), except there are no functions for reading and writing 8-byte-long values. However, the `write(char* data, uint len)` function is definitely worth mentioning. I still don't understand why exactly, but it's impossible to use it to write more than 8 bytes at once; otherwise, it spits out damaged data. In `da-api.h` for the mt6252 SoC, I had to implement a small proxy function that will use the DA-provided `write(char* data, uint len)` to write an arbitrary amount of bytes one by one.

Missing `print` functions were also an issue because the `hello-world-uart` payload depends on them. I found out I could output data over UART using the `io_uart_writeb` function at `0x08103930`, so I turned the `DA_uart_putc` function into a simple wrapper for `io_uart_writeb`, making it very similar to what mt65xx DAs actually have. `DA_uart_print_hex` was borrowed from `standalone-util.c`, and `DA_uart_printf` was crudely hacked together just to get any kind of output from it. Ideally, I should've used [mpaland/printf](https://github.com/mpaland/printf) (as suggested by [Mis012](https://github.com/Mis012)), which was designed specifically for embedded environments. But I thought it's not worth spending lots of time figuring out building and linking it.

After filling in the contents of `hw-api.h` and `hw-api.s`, everything left to do was to add some new rules to the Makefile. The fact that the newly introduced SP Flash Tool carries an `MTK_AllInOne_DA.bin` with **45** Download Agents for various mt62xx SoCs means we won't need another SP Flash Tool dependency in the upcoming future.

Working on mt6252 was actually fun, and I liked the idea that I could use ChatGPT for help with basic RE. I wish I had more mt62xx devices to add support for, though!
