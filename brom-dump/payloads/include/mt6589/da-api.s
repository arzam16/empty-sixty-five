@ SPDX-License-Identifier: GPL-3.0-only
@ SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

.equ DA_print_hex_value,	0x12003F50	@ void print_hex_value(uint value, uint width)
.equ DA_putc_wrapper_uart,	0x12003F3A	@ void putc_uart_wrapper(uint chr)
.equ DA_printf_uart,		0x12003F7C  @ void printf_uart(char* fmt, uint* val1, uint val2, uint val3)
