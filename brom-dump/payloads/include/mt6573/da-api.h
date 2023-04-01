// SPDX-License-Identifier: GPL-3.0-only
// SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

#include <stdint.h>

void (*DA_reset_uart_and_log)() =
	( void (*)() )
	(0x90009E64 + 1);

void (*DA_putc_wrapper_uart)(uint8_t) =
	( void (*)(uint8_t) )
	(0x90007AFE + 1);
void (*DA_print_hex_value)(uint32_t, uint32_t) =
	( void (*)(uint32_t, uint32_t) )
	(0x90007B14 + 1);
void (*DA_printf_uart)(uint8_t*, uint32_t, uint32_t, uint32_t) =
	( void (*)(uint8_t*, uint32_t, uint32_t, uint32_t) )
	(0x90007B42 + 1);

void (*DA_io_usb_write)(uint8_t*, uint32_t) =
	( void (*)(uint8_t*, uint32_t) )
	(0x900099FE + 1);
uint32_t (*DA_io_usb_readl)() =
	( uint32_t (*)() )
	(0x90009BB8 + 1);
void (*DA_io_usb_writel)(uint32_t) =
	( void (*)(uint32_t) )
	(0x90009BE4 + 1);
