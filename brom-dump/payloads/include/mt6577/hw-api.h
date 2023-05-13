// SPDX-License-Identifier: GPL-3.0-only
// SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

#ifndef H_MT6577_HW_API
#define H_MT6577_HW_API

#define HW_reg_chip_id			0xF8000000
#define HW_reg_uart0_base		0xC1009000
#define HW_reg_uart1_base		0xC100A000
#define HW_reg_uart2_base		0xC100B000
#define HW_reg_uart3_base		0xC100C000

#define MEM_brom_start			0xFFFF0000
#define MEM_brom_length			0x10000
#define MEM_sram_start			0xF0000000
#define MEM_sram_length			0x10000
#define MEM_da_start			0xC2000000
#define MEM_da_length			0x40000

#endif // H_MT6577_HW_API
