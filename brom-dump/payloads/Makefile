# SPDX-License-Identifier: Unlicense

CROSS_COMPILE ?= arm-none-eabi-
CC				= $(CROSS_COMPILE)gcc
AS				= $(CROSS_COMPILE)as
LD				= $(CROSS_COMPILE)ld
OBJCOPY			= $(CROSS_COMPILE)objcopy
CFLAGS			= -c -O0 -nodefaultlibs -nostdlib -marm $(TARGET_FLAGS) -I include/
ASFLAGS			= $(TARGET_FLAGS)
LDFLAGS			= -T $(TARGET_LD_SCRIPT)

# Root directory for build files
BUILD_DIR = $(CURDIR)/build
# Directory for storing auxiliry file such as SP Flash Tool distributions
AUX_DIR = $(BUILD_DIR)/aux
# Directory for temp build files
OUT_DIR = $(BUILD_DIR)/out

# Supported devices
ALL_TARGETS = mt6589
# This has to be set manually
TARGET ?= unsupported
TARGET_LD_SCRIPT = include/$(TARGET)/payload.ld
TARGET_INIT = $(OUT_DIR)/$(TARGET)-init.o

# Flags for individual targets
TARGET_FLAGS = $($(TARGET)_FLAGS) -I include/$(TARGET)
mt6589_FLAGS = -mcpu=cortex-a7

# Available payloads
PAYLOADS = hello-world-uart usb-dump

PAYLOAD_BINS = $(patsubst %,$(BUILD_DIR)/$(TARGET)-%-payload.bin,$(PAYLOADS))
TARGET_DA_PATCHED = $(OUT_DIR)/$(TARGET)-da-patched.bin

CHECKSUM_SPFT_V5_1648_LINUX := "9c9c57405ee35044e41d7958cfbd01232107101ec5cec03539d33438cbe38b4b"

.PHONY: all target clean

all: target $(PAYLOAD_BINS)

target:
ifeq ($(TARGET),unsupported)
	$(error "TARGET is not defined, supported values: $(ALL_TARGETS)")
endif

clean:
	rm -vf $(AUX_DIR)/*-da-original.bin
	rm -vf $(OUT_DIR)/*-da-patched.bin
	rm -vf $(OUT_DIR)/*.o
	rm -vf $(BUILD_DIR)/*-payload.bin


$(TARGET_INIT): init.s
	$(AS) $(ASFLAGS) -o "$@" "$<"

$(OUT_DIR)/$(TARGET)-hello-world-uart-piggyback.o: hello-world-uart.c | $(OUT_DIR)
	$(CC) $(CFLAGS) -o "$@" "$<"

$(OUT_DIR)/$(TARGET)-usb-dump-piggyback.o: usb-dump.c | $(OUT_DIR)
	$(CC) $(CFLAGS) -o "$@" "$<"

%-piggyback.elf: %-piggyback.o $(TARGET_INIT) | $(OUT_DIR)
	$(LD) $(LDFLAGS) -o "$@" $^

%-piggyback.bin: %-piggyback.elf | $(OUT_DIR)
	$(OBJCOPY) -O binary -S -g "$<" "$@"

$(BUILD_DIR)/$(TARGET)-%-payload.bin: $(TARGET_DA_PATCHED) $(OUT_DIR)/$(TARGET)-%-piggyback.bin | $(BUILD_DIR) $(OUT_DIR)
	cat $^ > "$@"

$(AUX_DIR)/mt6573-da-original.bin: $(AUX_DIR)/SP_Flash_Tool_v5.1648_Linux.zip | $(AUX_DIR)
	7z x -so "$<" "SP_Flash_Tool_v5.1648_Linux/MTK_AllInOne_DA.bin" |\
		tail -c +14813 | head -c 90932 \
		> "$@"

$(AUX_DIR)/mt6589-da-original.bin: $(AUX_DIR)/SP_Flash_Tool_v5.1648_Linux.zip | $(AUX_DIR)
	7z x -so "$<" "SP_Flash_Tool_v5.1648_Linux/MTK_AllInOne_DA.bin" |\
		tail -c +767137 | head -c 141012 \
		> "$@"

# Patch the internal memory initialization routine to jump to our payload
# before Download Agent starts waiting for more data from SP Flash Tool.
#
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
# 12000cda 21 f0 fc ec     blx        FUN_120226d4
$(OUT_DIR)/mt6589-da-patched.bin: $(AUX_DIR)/mt6589-da-original.bin | $(OUT_DIR) $(AUX_DIR)
	xxd -c 256 -p "$<" |\
		sed -e "s/fff7ccff60688047/fff7ccff21f0fcec/" |\
		xxd -p -r > "$@"

$(AUX_DIR)/SP_Flash_Tool_v5.1648_Linux.zip: | $(AUX_DIR)
	wget \
		--quiet \
		--header "referer: https://spflashtool.com/download/" \
		-O "temp-v5.1468-linux.zip" \
		"https://spflashtool.com/download/SP_Flash_Tool_v5.1648_Linux.zip"
	@echo "Checking file integrity"
	sha256sum "temp-v5.1468-linux.zip" | grep -q -F $(CHECKSUM_SPFT_V5_1648_LINUX)
	mv "temp-v5.1468-linux.zip" "$@"

$(BUILD_DIR) $(AUX_DIR) $(OUT_DIR):
	mkdir -p "$@"
