// SPDX-License-Identifier: GPL-3.0-only
// SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

#ifndef H_MT6582_DA_API
#define H_MT6582_DA_API

#include <stdint.h>

void DA_init() {
	// reset_uart_and_log
	((void (*)())(0x00200F40 + 1))();
}

void (*DA_putc_wrapper_uart)(uint8_t) =
	( void (*)(uint8_t) )
	(0x00200DF2 + 1);
void (*DA_print_hex_value)(uint32_t, uint32_t) =
	( void (*)(uint32_t, uint32_t) )
	(0x00200E08 + 1);
void (*DA_printf_uart)(uint8_t*, uint32_t, uint32_t, uint32_t) =
	( void (*)(uint8_t*, uint32_t, uint32_t, uint32_t) )
	(0x00200E34 + 1);

void (*DA_io_usb_write)(uint8_t*, uint32_t) =
	( void (*)(uint8_t*, uint32_t) )
	(0x00203D74 + 1);
uint32_t (*DA_io_usb_readl)() =
	( uint32_t (*)() )
	(0x00203F44 + 1);
void (*DA_io_usb_writel)(uint32_t) =
	( void (*)(uint32_t) )
	(0x00203F72 + 1);

#endif // H_MT6582_DA_API
