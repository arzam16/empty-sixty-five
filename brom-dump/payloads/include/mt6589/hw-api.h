// SPDX-License-Identifier: GPL-3.0-only
// SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

#ifndef H_MT6589_HW_API
#define H_MT6589_HW_API

#define HW_reg_chip_id			0x08000000
#define HW_reg_uart0_base		0x11006000
#define HW_reg_uart1_base		0x11007000
#define HW_reg_uart2_base		0x11008000
#define HW_reg_uart3_base		0x11009000

#define MEM_brom_start			0x0
#define MEM_brom_length			0x10000
#define MEM_sram_start			0x100000
#define MEM_sram_length			0x10000
#define MEM_da_start			0x12000000
#define MEM_da_length			0x40000

#endif // H_MT6589_HW_API
