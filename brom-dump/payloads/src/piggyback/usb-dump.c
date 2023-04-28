// SPDX-License-Identifier: GPL-3.0-only
// SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

#include <stdint.h>
#include "common.h"
#include "da-api.h"
#include "hw-api.h"

#define MAGIC_HELLO			0x3E4D746B
#define MAGIC_GOODBYE		0x4D746B3C

static const uint32_t dump_regions[3][2] = {
	{ MEM_brom_start, MEM_brom_length },
	{ MEM_sram_start, MEM_sram_length },
	{ MEM_da_start, MEM_da_length },
};

void main() {
	DA_io_usb_writel(MAGIC_HELLO);
	
	for (int i = 0; i < ARRAY_SIZE(dump_regions); i++) {
		DA_io_usb_writel(dump_regions[i][1]);
		DA_io_usb_write(dump_regions[i][0], dump_regions[i][1]);
	}
	
	DA_io_usb_writel(MAGIC_GOODBYE);
	
	while (1) {
		do_nothing();
	}
}
