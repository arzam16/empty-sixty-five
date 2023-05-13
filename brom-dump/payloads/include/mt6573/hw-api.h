// SPDX-License-Identifier: GPL-3.0-only
// SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

#ifndef H_MT6573_HW_API
#define H_MT6573_HW_API

#define HW_reg_chip_id			0x70026008
#define HW_reg_uart0_base		0x70003000
#define HW_reg_uart1_base		0x70004000
#define HW_reg_uart2_base		0x70005000
#define HW_reg_uart3_base		0x70006000

#define MEM_brom_start			0x48000000
#define MEM_brom_length			0x10000
#define MEM_sram_start			0x40000000
#define MEM_sram_length			0x40000
#define MEM_da_start			0x90005000
#define MEM_da_length			0x1B000

#endif // H_MT6573_HW_API
