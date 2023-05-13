// SPDX-License-Identifier: GPL-3.0-only
// SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

#include <stdint.h>
#include "standalone-util.h"
#include "common.h"

t_hardware hardware;

void init_standalone(uint32_t uart_base) {
	hardware.uart_thr = (volatile uint32_t*)(uart_base + UART_THR);
	hardware.uart_lsr = (volatile uint32_t*)(uart_base + UART_LSR);
}

void putc_uart(uint8_t chr) {
	while (! ((*hardware.uart_lsr) & UART_LSR_THRE) ) {
		do_nothing(); // won't it slow down way too much, will it?
	}

	*hardware.uart_thr = (uint32_t)chr;
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
