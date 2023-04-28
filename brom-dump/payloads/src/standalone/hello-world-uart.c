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
	uint32_t chip_id = *(uint32_t*)HW_reg_chip_id;
	print_uart("\nHello from mt");
	print_hex_value(chip_id, 4);
	print_uart("!\n");

	print_hex_value(0x12, 2);
	putc_wrapper_uart('\n');

	print_hex_value(0x3456, 4);
	putc_wrapper_uart('\n');

	print_hex_value(0x789ABCDE, 8);
	putc_wrapper_uart('\n');

	for (int i = 0; i < 0x10; i++) {
		print_hex_value(i, 2);
		putc_wrapper_uart(' ');
	}
	putc_wrapper_uart('\n');

	putc_wrapper_uart(':');
	putc_wrapper_uart(')');
	putc_wrapper_uart('\n');

	while (1) {
		do_nothing();
	}
}
