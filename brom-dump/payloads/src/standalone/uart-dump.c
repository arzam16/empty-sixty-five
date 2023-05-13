// SPDX-License-Identifier: GPL-3.0-only
// SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

#include <stdint.h>
#include "common.h"
#include "hw-api.h"
#include "standalone-util.h"

static const uint32_t dump_regions[2][2] = {
	{ MEM_brom_start, MEM_brom_length },
	{ MEM_sram_start, MEM_sram_length },
	// the whole DA is our code, no need to dump it here
};

void main() {
	uint32_t i, j, offset;
	uint32_t value;

	init_standalone(HW_reg_uart0_base);
	print_uart("\n\n");

	for (i = 0; i < ARRAY_SIZE(dump_regions); i++) {
		print_uart("dump:");
		for (j = 0; j < dump_regions[i][1]; j += sizeof(uint32_t)) {
			offset = dump_regions[i][0] + j;
			value = __builtin_bswap32(
				*(uint32_t*)offset
			);
			print_hex_value(value, 8);
		}
		print_uart("\n");
	}

	print_uart("done :)");

	while (1) {
		do_nothing();
	}
}
