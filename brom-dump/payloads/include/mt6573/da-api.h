// SPDX-License-Identifier: GPL-3.0-only
// SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

#ifndef H_MT6573_DA_API
#define H_MT6573_DA_API

#include <stdint.h>

void DA_init() {
	// reset_uart_and_log
	((void (*)())(0x90009E64 + 1))();
}

void (*DA_uart_putc)(uint8_t) =
	( void (*)(uint8_t) )
	(0x90007AFE + 1);
void (*DA_uart_print_hex)(uint32_t, uint32_t) =
	( void (*)(uint32_t, uint32_t) )
	(0x90007B14 + 1);
void (*DA_uart_printf)(uint8_t*, uint32_t, uint32_t, uint32_t) =
	( void (*)(uint8_t*, uint32_t, uint32_t, uint32_t) )
	(0x90007B42 + 1);

void (*DA_usb_write)(uint8_t*, uint32_t) =
	( void (*)(uint8_t*, uint32_t) )
	(0x900099FE + 1);
uint32_t (*DA_usb_readl)() =
	( uint32_t (*)() )
	(0x90009BB8 + 1);
void (*DA_usb_writel)(uint32_t) =
	( void (*)(uint32_t) )
	(0x90009BE4 + 1);

#endif // H_MT6573_DA_API
