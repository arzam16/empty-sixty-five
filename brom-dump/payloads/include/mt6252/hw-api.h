// SPDX-License-Identifier: GPL-3.0-only
// SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

#ifndef H_MT6252_HW_API
#define H_MT6252_HW_API

#define HW_reg_chip_id			0x80010008
#define HW_reg_uart0_base		0x81030000
#define HW_reg_uart1_base		0x81040000
#define HW_reg_uart2_base		0x81050000
#define HW_reg_uart3_base		0x81060000

#define MEM_brom_start			0x48000000
#define MEM_brom_length			0x8000
#define MEM_sram_start			0x40000000 // SRAM + 1st-stage DA (starts at 0x40005000)
#define MEM_sram_length			0xC000
#define MEM_da_start			0x08100000
#define MEM_da_length			0x20000

#endif // H_MT6252_HW_API
