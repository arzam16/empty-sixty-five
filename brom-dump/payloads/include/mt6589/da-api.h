// SPDX-License-Identifier: GPL-3.0-only
// SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

#include <stdint.h>

void (*DA_reset_uart_and_log)() =
	( void (*)() )
	(0x120093A6 + 1);

void (*DA_putc_wrapper_uart)(uint8_t) =
	( void (*)(uint8_t) )
	(0x12003F3A + 1);
void (*DA_print_hex_value)(uint32_t, uint32_t) =
	( void (*)(uint32_t, uint32_t) )
	(0x12003F50 + 1);
void (*DA_printf_uart)(uint8_t*, uint32_t, uint32_t, uint32_t) =
	( void (*)(uint8_t*, uint32_t, uint32_t, uint32_t) )
	(0x12003F7C + 1);

void (*DA_io_usb_write)(uint8_t*, uint32_t) =
	( void (*)(uint8_t*, uint32_t) )
	(0x12008E60 + 1);
uint32_t (*DA_io_usb_readl)() =
	( uint32_t (*)() )
	(0x12009032 + 1);
void (*DA_io_usb_writel)(uint32_t) =
	( void (*)(uint32_t) )
	(0x12009060 + 1);
