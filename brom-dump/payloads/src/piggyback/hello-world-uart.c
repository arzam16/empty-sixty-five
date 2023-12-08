// SPDX-License-Identifier: GPL-3.0-only
// SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

#include <stdint.h>
#include "common.h"
#include "da-api.h"
#include "hw-api.h"

void main() {
	DA_init();

	uint32_t chip_id = *(uint32_t*)HW_reg_chip_id;
	DA_uart_printf("\n\n\nHello from mt%x!\n", chip_id, 0, 0);

	DA_uart_print_hex(0x12, 2);
	DA_uart_putc('\n');

	DA_uart_print_hex(0x3456, 4);
	DA_uart_putc('\n');

	DA_uart_print_hex(0x789ABCDE, 8);
	DA_uart_putc('\n');

	for (int i = 0; i < 0x10; i++) {
		DA_uart_print_hex(i, 2);
		DA_uart_putc(' ');
	}
	DA_uart_putc('\n');

	DA_uart_putc(':');
	DA_uart_putc(')');
	DA_uart_putc('\n');

	while (1) {
		do_nothing();
	}
}
