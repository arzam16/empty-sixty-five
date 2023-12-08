// SPDX-License-Identifier: GPL-3.0-only
// SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

#include <stdint.h>
#include "common.h"
#include "hw-api.h"
#include "standalone-util.h"

void main() {
	init_standalone(HW_reg_uart0_base);
	
	volatile uint32_t chip_id = *(volatile uint32_t *)HW_reg_chip_id;
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
