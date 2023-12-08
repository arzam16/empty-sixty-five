// SPDX-License-Identifier: GPL-3.0-only
// SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

#ifndef H_MT6580_DA_API
#define H_MT6580_DA_API

#include <stdint.h>

void DA_init() {
	// No init required on this platform.
}

void (*DA_putc_wrapper_uart)(uint8_t) =
	( void (*)(uint8_t) )
	(0x00201C14 + 1);
void (*DA_print_hex_value)(uint32_t, uint32_t) =
	( void (*)(uint32_t, uint32_t) )
	(0x00201C52 + 1);
void (*DA_printf_uart)(uint8_t*, uint32_t, uint32_t, uint32_t) =
	( void (*)(uint8_t*, uint32_t, uint32_t, uint32_t) )
	(0x00201C84 + 1);

void (*DA_io_usb_write)(uint8_t*, uint32_t) =
	( void (*)(uint8_t*, uint32_t) )
	(0x0020821C + 1);
uint32_t (*DA_io_usb_readl)() =
	( uint32_t (*)() )
	(0x0020841C + 1);
void (*DA_io_usb_writel)(uint32_t) =
	( void (*)(uint32_t) )
	(0x00208444 + 1);

#endif // H_MT6580_DA_API
