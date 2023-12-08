// SPDX-License-Identifier: GPL-3.0-only
// SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

#ifndef H_MT6252_DA_API
#define H_MT6252_DA_API

#include <stdint.h>

void DA_init() {
	// No init required on this platform
}

void DA_uart_putc(uint8_t val) {
	// Not originally supported by DA but we can work it around by using one
	// of the low-level functions used for communicating with PC
	void (*DA_uart_putc_inner)(uint8_t) = (void (*)(uint8_t))(0x08103930 + 1);
	if (val == '\n') {
		DA_uart_putc_inner('\r');
	}
	DA_uart_putc_inner(val);
}

void DA_uart_print_hex(uint32_t val, uint32_t width) {
	// Not originally supported by DA
	uint8_t c;

	if (width != 0)
		width--;

	if (val & 0xFFFFFFF0 | width) {
		DA_uart_print_hex(val >> 4, width);
		val = val & 0xF;
	}

	c = val + (val < 10? '0' : '7');
	DA_uart_putc(c);
}

void DA_uart_printf(uint8_t* str, uint32_t arg1, uint32_t arg2, uint32_t arg3) {
	// Not originally supported by DA.
	// Lets come up with a tiny barely working implementation.
	uint32_t args[3] = { arg1, arg2, arg3 };
	uint8_t arg_idx = 0;

	while (*str != '\0') {
		if (*str == '%' && arg_idx < 3) {
			str++;
			switch (*str) {
				case 's': {
					uint8_t* str_arg = (uint8_t*)args[arg_idx++];
					while (*str_arg != '\0') {
						DA_uart_putc(*str_arg++);
					}
					break;
				}
				case 'x': {
					DA_uart_print_hex(arg1, 8);
					break;
				}
			}
		} else {
			DA_uart_putc(*str);
		}
		str++;
	}
}

void DA_usb_write(uint8_t* data, uint32_t len) {
	// The mt6252 DA has a usb_write function but for some reason we cannot
	// use it to write more than 8 bytes at once because it *seems* to play
	// with USB packet length and call some weird nested functions.
	// Lets write bytes one by one using one of these functions.
	while (len--) {
		((void (*)(uint8_t*, uint32_t, uint32_t, uint32_t))(0x081092f6 + 1))(data++, 1, 0, 0);
	}
}
uint32_t (*DA_usb_readl)() =
	( uint32_t (*)() )
	(0x0810946c + 1);
void (*DA_usb_writel)(uint32_t) =
	( void (*)(uint32_t) )
	(0x081094a0 + 1);

#endif // H_MT6252_DA_API
