// SPDX-License-Identifier: GPL-3.0-only
// SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

#include <stdint.h>
#include "common.h"
#include "hw-api.h"

// define your UART port in ACTIVE_UART
#define ACTIVE_UART				(HW_reg_uart0_base)
#define UART_THR				(ACTIVE_UART + 0x00)
#define UART_LSR				(ACTIVE_UART + 0x14)

#define UART_LSR_THRE			(0b00100000)

static const uint32_t dump_regions[2][2] = {
	{ MEM_brom_start, MEM_brom_length },
	{ MEM_sram_start, MEM_sram_length },
	// the whole DA is our code, no need to dump it here
};

volatile uint32_t* uart_thr = (volatile uint32_t*)UART_THR;
volatile uint32_t* uart_lsr = (volatile uint32_t*)UART_LSR;

void putc_uart(uint8_t chr) {
	while (! ((*uart_lsr) & UART_LSR_THRE) ) {
		do_nothing(); // won't it slow down way too much, will it?
	}

	*uart_thr = (uint32_t)chr;
}

void putc_wrapper_uart(uint8_t chr) {
	if (chr == '\n')
		putc_uart('\r');
	putc_uart(chr);
}

void print_hex_value(uint32_t val, uint8_t width) {
	uint8_t c;

	if (width != 0)
		width--;

	if (val & 0xFFFFFFF0 | width) {
		print_hex_value(val >> 4, width);
		val = val & 0xF;
	}

	c = val + (val < 10? '0' : '7');
	putc_wrapper_uart(c);
}

void print_uart(uint8_t* str) {
	do {
		putc_wrapper_uart(*str);
	} while (*(++str) != '\0');
}

void main() {
	uint32_t i, j, offset;
	uint32_t value;

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
