# SPDX-License-Identifier: Unlicense
# SPDX-FileContributor: arzamas-16 <https://github.com/arzamas-16>

.NOTPARALLEL:

SRC_DIR			:= $(CURDIR)/src
INCLUDE_DIR		:= $(CURDIR)/include
BUILD_DIR		:= $(CURDIR)/build
AUX_DIR			:= $(BUILD_DIR)/aux
OUT_DIR			:= $(BUILD_DIR)/out
RELEASE_DIR		:= $(BUILD_DIR)/release
CHECKSUM_SPFT_V5_1648_LINUX := "9c9c57405ee35044e41d7958cfbd01232107101ec5cec03539d33438cbe38b4b"

PB_PAYLOADS		:= hello-world-uart \
					usb-dump
PB_SRC_DIR		:= $(SRC_DIR)/piggyback
PB_OUT_DIR		:= $(OUT_DIR)/piggyback
PB_RELEASE_DIR	:= $(RELEASE_DIR)/piggyback
PB_INIT			= $(PB_OUT_DIR)/$(TARGET)-init-piggyback.o
PB_LD_SCRIPT	= $(PB_OUT_DIR)/$(TARGET)-piggyback.ld
PB_SRC			:= $(foreach P, $(PB_PAYLOADS), $(PB_SRC_DIR)/$(P).c)
PB_OBJ			= $(foreach P, $(PB_PAYLOADS), $(PB_OUT_DIR)/$(TARGET)-$(P).o)
PB_ELF			= $(foreach P, $(PB_PAYLOADS), $(PB_OUT_DIR)/$(TARGET)-$(P).elf)
PB_BIN			= $(foreach P, $(PB_PAYLOADS), $(PB_OUT_DIR)/$(TARGET)-$(P)-stripped.bin)
PB_RELEASES		= $(foreach P, $(PB_PAYLOADS), $(PB_RELEASE_DIR)/$(TARGET)-$(P).bin)

SA_PAYLOADS		:= hello-world-uart \
					uart-dump
SA_SRC_DIR		:= $(SRC_DIR)/standalone
SA_OUT_DIR		:= $(OUT_DIR)/standalone
SA_RELEASE_DIR	:= $(RELEASE_DIR)/standalone
SA_INIT			= $(SA_OUT_DIR)/$(TARGET)-init-standalone.o
SA_UTIL			= $(SA_OUT_DIR)/$(TARGET)-standalone-util.o
SA_LD_SCRIPT	= $(INCLUDE_DIR)/$(TARGET)/memory.ld
SA_SRC			:= $(foreach P, $(SA_PAYLOADS), $(SA_SRC_DIR)/$(P).c)
SA_OBJ			= $(foreach P, $(SA_PAYLOADS), $(SA_OUT_DIR)/$(TARGET)-$(P).o)
SA_ELF			= $(foreach P, $(SA_PAYLOADS), $(SA_OUT_DIR)/$(TARGET)-$(P).elf)
SA_RELEASES		= $(foreach P, $(SA_PAYLOADS), $(SA_RELEASE_DIR)/$(TARGET)-$(P).bin)

ALL_RELEASES	= $(SA_RELEASES) $(PB_RELEASES)

AVAILABLE_SOCS		:= mt6573 mt6577 mt6580 mt6582 mt6589
MT6573_RELEASES		:= $(PB_RELEASES)
MT6573_FLAGS		:= -mcpu=arm1176jzf-s
MT6577_RELEASES		:= $(SA_RELEASES)
MT6577_FLAGS		:= -mcpu=cortex-a9
MT6580_RELEASES		:= $(PB_RELEASES) $(SA_RELEASES)
MT6580_FLAGS		:= -mcpu=cortex-a7
MT6582_RELEASES		:= $(PB_RELEASES) $(SA_RELEASES)
MT6582_FLAGS		:= -mcpu=cortex-a7
MT6589_RELEASES		:= $(PB_RELEASES)
MT6589_FLAGS		:= -mcpu=cortex-a7

TARGET				?= undefined
TARGET_CFLAGS		= $($(subst mt,MT,$(TARGET))_FLAGS) -I $(INCLUDE_DIR)/$(TARGET)
TARGET_ASFLAGS		= $(TARGET_CFLAGS)
TARGET_HEADERS		= $(wildcard $(INCLUDE_DIR)/$(TARGET)/*)
TARGET_MEMORY		= $(INCLUDE_DIR)/$(TARGET)/memory.ld
TARGET_RELEASES		= $($(subst mt,MT,$(TARGET))_RELEASES)
# only used for piggyback payloads
TARGET_DA_PATCHED	= $(OUT_DIR)/$(TARGET)-da-patched.bin
TARGET_DA_ORIGINAL	= $(AUX_DIR)/$(TARGET)-da-original.bin

CROSS_COMPILE	?= arm-none-eabi-
CC				:= $(CROSS_COMPILE)gcc
AS				:= $(CROSS_COMPILE)as
LD				:= $(CROSS_COMPILE)ld
OBJCOPY			:= $(CROSS_COMPILE)objcopy

CFLAGS			= $(TARGET_CFLAGS) -c -O0 -nodefaultlibs -nostdlib -marm -I $(INCLUDE_DIR)
ASFLAGS			= $(TARGET_ASFLAGS)
LDFLAGS			= -L $(INCLUDE_DIR)

.PHONY: all target-check clean \
		pb-ld pb-obj pb-elf pb-bin piggybacks

# If `make` is launched without TARGET set, build for all available SoCs
ifeq ($(TARGET),undefined)
AVAILABLE_TARGETS := $(foreach SOC, $(AVAILABLE_SOCS), target-$(SOC))
all: $(AVAILABLE_TARGETS)
target-%:
	@echo "Building for $*"
	@$(MAKE) -f $(lastword $(MAKEFILE_LIST)) TARGET=$*
else
# If TARGET is set then check its validity and build payloads for it
all: target-check $(TARGET_RELEASES)
endif

target-check:
ifeq (,$(findstring $(TARGET),$(AVAILABLE_SOCS)))
	$(error "Unknown TARGET! Supported targets: $(AVAILABLE_SOCS)")
endif

clean:
	@find $(BUILD_DIR) -type f \( \
		-name "*.bin" -o \
		-name "*.ld" -o \
		-name "*.o" -o \
		-name "*.elf" \) | \
	xargs -d "\n" rm -vf

pb-ld: target-check $(PB_LD)
pb-obj: target-check $(PB_OBJ)
pb-elf: target-check $(PB_ELF)
pb-bin: target-check $(PB_BIN)
piggybacks: target-check $(PB_RELEASES)

sa-obj: target-check $(SA_OBJ)
sa-elf: target-check $(SA_ELF)
standalones: target-check $(SA_RELEASES)

# init for piggyback payloads
$(PB_INIT): $(SRC_DIR)/init.s | $(PB_OUT_DIR)
	$(AS) $(ASFLAGS) --defsym PAYLOAD_PIGGYBACK=1 -o "$@" "$<"

# Build each PB_OBJ
$(PB_OUT_DIR)/$(TARGET)-%.o: $(PB_SRC_DIR)/%.c $(TARGET_HEADERS) | $(PB_OUT_DIR)
	$(CC) $(CFLAGS) -o "$@" "$<"

# Link .o with init
$(PB_OUT_DIR)/%.elf: $(PB_OUT_DIR)/%.o $(PB_INIT) $(PB_LD_SCRIPT) | $(PB_OUT_DIR)
	$(LD) $(LDFLAGS) -T $(PB_LD_SCRIPT) -o "$@" "$<" $(PB_INIT)

# PB_BIN: PB_ELF
%-stripped.bin: %.elf | $(OUT_DIR)
	$(OBJCOPY) -O binary -S -g "$<" "$@"

# PB_RELEASES: PB_BIN
$(PB_RELEASE_DIR)/$(TARGET)-%.bin: $(TARGET_DA_PATCHED) $(PB_OUT_DIR)/$(TARGET)-%-stripped.bin | $(PB_RELEASE_DIR)
	cat $^ > "$@"

# LD script for piggyback payloads
$(PB_LD_SCRIPT): $(TARGET_MEMORY) $(TARGET_DA_PATCHED)
	python3 scripts/piggyback-ld.py $^ "$@"

# TARGET_DA_ORIGINAL for mt6573
$(AUX_DIR)/mt6573-da-original.bin: $(AUX_DIR)/SP_Flash_Tool_v5.1648_Linux.zip | $(AUX_DIR)
	7z x -so "$<" "SP_Flash_Tool_v5.1648_Linux/MTK_AllInOne_DA.bin" |\
		tail -c +14813 | head -c 90676 \
		> "$@"

# TARGET_DA_PATCHED for mt6573
# Patch the internal memory initialization routine to jump to our payload
# before Download Agent starts waiting for more data from SP Flash Tool.
#
# Before patch:
# ======================================================================
# 90005bd4 00 78           ldrb       r0,[r0,#0x0]
# 90005bd6 88 47           blx        r1
# 90005bd8 e8 68           ldr        r0,[r5,#0xc]=>DAT_40007edc
# 90005bda 00 78           ldrb       r0,[r0,#0x0]
#
#
# After patch:
# ======================================================================
# 90005bd4 00 78           ldrb       r0,[r0,#0x0]
# 90005bd6 88 47           blx        r1
# 90005bd8 XX XX XX XX     blx        PAYLOAD_ENTRY_POINT
$(OUT_DIR)/mt6573-da-patched.bin: $(TARGET_DA_ORIGINAL) $(TARGET_MEMORY) | $(OUT_DIR)
	python3 scripts/patch-da.py \
		"$<" $(TARGET_MEMORY) 0x90005bd8 "$@"

# TARGET_DA_ORIGINAL for mt6580
# Add extra zero padding for DA memory allocations
$(AUX_DIR)/mt6580-da-original.bin: $(AUX_DIR)/SP_Flash_Tool_v5.1648_Linux.zip | $(AUX_DIR)
	7z x -so "$<" "SP_Flash_Tool_v5.1648_Linux/MTK_AllInOne_DA.bin" |\
		tail -c +3959277 | head -c 70440 |\
		cat - /dev/zero | head -c 88064 \
		> "$@"

# TARGET_DA_PATCHED for mt6580
# Patch the internal memory initialization routine to jump to our payload
# before Download Agent starts waiting for more data from SP Flash Tool.
#
# Before patch:
# ======================================================================
# 002014da 00 f0 d3 fb     bl         printf_uart
#                    LAB_002014de
# 002014de 02 f0 9b fc     bl         init_print_pll_state
#                    LAB_002014e2
# 002014e2 81 4d           ldr        r5,[PTR_DAT_002016e8]
# 002014e4 03 f0 74 fa     bl         init_power_down_something
#
#
# After patch:
# ======================================================================
# 002014da 00 f0 d3 fb     bl         printf_uart
#                    LAB_002014de
# 002014de 02 f0 9b fc     bl         init_print_pll_state
#                    LAB_002014e2
# 002014e2 81 4d           ldr        r5,[PTR_DAT_002016e8]
# 002014e4 XX XX XX XX     blx        PAYLOAD_ENTRY_POINT
$(OUT_DIR)/mt6580-da-patched.bin: $(TARGET_DA_ORIGINAL) $(TARGET_MEMORY) | $(OUT_DIR)
	python3 scripts/patch-da.py \
		"$<" $(TARGET_MEMORY) 0x002014e4 "$@"

# TARGET_DA_ORIGINAL for mt6582
$(AUX_DIR)/mt6582-da-original.bin: $(AUX_DIR)/SP_Flash_Tool_v5.1648_Linux.zip | $(AUX_DIR)
	7z x -so "$<" "SP_Flash_Tool_v5.1648_Linux/MTK_AllInOne_DA.bin" |\
		tail -c +923301 | head -c 52316 |\
		cat - /dev/zero | head -c 65536 \
		> "$@"

# TARGET_DA_PATCHED for mt6582
# Patch the internal memory initialization routine to jump to our payload
# before Download Agent starts waiting for more data from SP Flash Tool.
#
# Before patch:
# ======================================================================
# 002005d8 03 f0 d2 fe     bl         init_disable_wdt
# 002005dc 0b f0 28 fa     bl         init_setup_config
# 002005e0 00 f0 f2 f9     bl         setup_io_transport
# 002005e4 04 f0 22 f9     bl         FUN_0020482c
#
#
# After patch:
# ======================================================================
# 002005d8 03 f0 d2 fe     bl         init_disable_wdt
# 002005dc 0b f0 28 fa     bl         init_setup_config
# 002005e0 00 f0 f2 f9     bl         setup_io_transport
# 002005e4 XX XX XX XX     blx        PAYLOAD_ENTRY_POINT
$(OUT_DIR)/mt6582-da-patched.bin: $(TARGET_DA_ORIGINAL) $(TARGET_MEMORY) | $(OUT_DIR)
	python3 scripts/patch-da.py \
		"$<" $(TARGET_MEMORY) 0x002005e4 "$@"

# TARGET_DA_ORIGINAL for mt6589
$(AUX_DIR)/mt6589-da-original.bin: $(AUX_DIR)/SP_Flash_Tool_v5.1648_Linux.zip | $(AUX_DIR)
	7z x -so "$<" "SP_Flash_Tool_v5.1648_Linux/MTK_AllInOne_DA.bin" |\
		tail -c +767137 | head -c 140756 \
		> "$@"

# TARGET_DA_PATCHED for mt6589
# Before patch:
# ======================================================================
# 12000cd6 ff f7 cc ff     bl         FUN_12000c72
# 12000cda 60 68           ldr        r0,[r4,#0x4]=>DAT_00102118
# 12000cdc 80 47           blx        r0
#
#
# After patch:
# ======================================================================
# 12000cd6 ff f7 cc ff     bl         FUN_12000c72
# 12000cda XX XX XX XX     blx        PAYLOAD_ENTRY_POINT
$(OUT_DIR)/mt6589-da-patched.bin: $(AUX_DIR)/mt6589-da-original.bin | $(OUT_DIR) $(AUX_DIR)
	python3 scripts/patch-da.py \
		"$<" $(TARGET_MEMORY) 0x12000cda "$@"

$(AUX_DIR)/SP_Flash_Tool_v5.1648_Linux.zip: | $(AUX_DIR)
	wget \
		--quiet \
		-O "temp-v5.1648-linux.zip" \
		"https://web.archive.org/web/20230308164639/https://spflashtool.com/download/SP_Flash_Tool_v5.1648_Linux.zip"
	@echo "Checking file integrity"
	sha256sum "temp-v5.1648-linux.zip" | grep -q -F $(CHECKSUM_SPFT_V5_1648_LINUX)
	mv "temp-v5.1648-linux.zip" "$@"

# init for standalone payloads
$(SA_INIT): $(SRC_DIR)/init.s | $(SA_OUT_DIR)
	$(AS) $(ASFLAGS) --defsym PAYLOAD_STANDALONE=1 -o "$@" "$<"

# utilities for standalone payloads
$(SA_UTIL): $(SA_SRC_DIR)/standalone-util.c | $(SA_OUT_DIR)
	$(CC) $(CFLAGS) -o "$@" "$<"

# Build each SA_OBJ
$(SA_OUT_DIR)/$(TARGET)-%.o: $(SA_SRC_DIR)/%.c $(TARGET_HEADERS) | $(SA_OUT_DIR)
	$(CC) $(CFLAGS) -o "$@" "$<"

# Link .o with init and utilities
$(SA_OUT_DIR)/%.elf: $(SA_OUT_DIR)/%.o $(SA_INIT) $(SA_UTIL) $(SA_LD_SCRIPT) | $(SA_OUT_DIR)
	$(LD) $(LDFLAGS) -T $(SA_LD_SCRIPT) -o "$@" "$<" $(SA_INIT) $(SA_UTIL)

# SA_RELEASES: SA_ELF
$(SA_RELEASE_DIR)/$(TARGET)-%.bin: $(SA_OUT_DIR)/$(TARGET)-%.elf | $(SA_RELEASE_DIR)
	$(OBJCOPY) -O binary -S -g "$<" "$@"

# Create directories
$(AUX_DIR) $(OUT_DIR) $(PB_OUT_DIR) $(PB_RELEASE_DIR) $(SA_OUT_DIR) $(SA_RELEASE_DIR):
	mkdir -p "$@"
