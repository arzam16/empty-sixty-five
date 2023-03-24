// SPDX-License-Identifier: GPL-3.0-only
// SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

#include <stdint.h>
#include "common.h"
#include "da-api.h"
#include "hw-api.h"

void main() {
	uint32_t chip_id = *(uint32_t*)HW_reg_chip_id;
	DA_printf_uart("\n\n\nHello from mt%x!\n", chip_id, 0, 0);

	DA_print_hex_value(0x12, 2);
	DA_putc_wrapper_uart('\n');

	DA_print_hex_value(0x3456, 4);
	DA_putc_wrapper_uart('\n');

	DA_print_hex_value(0x789ABCDE, 8);
	DA_putc_wrapper_uart('\n');

	for (int i = 0; i < 0x10; i++) {
		DA_print_hex_value(i, 2);
		DA_putc_wrapper_uart(' ');
	}
	DA_putc_wrapper_uart('\n');

	DA_putc_wrapper_uart(':');
	DA_putc_wrapper_uart(')');
	DA_putc_wrapper_uart('\n');

	while (1) {
		do_nothing();
	}
}
