// SPDX-License-Identifier: GPL-3.0-only
// SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

#ifndef H_MT6580_HW_API
#define H_MT6580_HW_API

#define HW_reg_chip_id			0x08000000
#define HW_reg_uart0_base		0x11005000
#define HW_reg_uart1_base		0x11006000
// mt6580 has only 2 UARTs, lets fall back to the first one to avoid
// breaking define statements which could become a nasty surprise
#define HW_reg_uart2_base		0x11005000
#define HW_reg_uart3_base		0x11005000

#define MEM_brom_start			0x00000000
#define MEM_brom_length			0x10000
#define MEM_sram_start			0x100000
#define MEM_sram_length			0x12000
#define MEM_da_start			0x200000
#define MEM_da_length			0x20000

#endif // H_MT6580_HW_API
