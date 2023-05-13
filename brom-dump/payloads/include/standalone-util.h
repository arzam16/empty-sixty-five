// SPDX-License-Identifier: GPL-3.0-only
// SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

#ifndef H_STANDALONE_UTIL
#define H_STANDALONE_UTIL

#include <stdint.h>

#define UART_THR				(0x00)
#define UART_LSR				(0x14)
#define UART_LSR_THRE			(0b00100000)

typedef struct s_hardware {
	volatile uint32_t* uart_thr;
	volatile uint32_t* uart_lsr;
} t_hardware;

void init_standalone(uint32_t uart_base);

void putc_uart(uint8_t chr);
void putc_wrapper_uart(uint8_t chr);
void print_hex_value(uint32_t val, uint8_t width);
void print_uart(uint8_t* str);

#endif // H_STANDALONE_UTIL
