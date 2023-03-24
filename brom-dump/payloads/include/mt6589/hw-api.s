@ SPDX-License-Identifier: GPL-3.0-only
@ SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

.equ HW_reg_chip_id,		0x08000000

@ derived from the original mt6589 DA, see 0x120000A0
.equ MEM_stack_base,		0x10FFF0

.equ MEM_brom_start,		0x0
.equ MEM_brom_length,		0x10000
.equ MEM_sram_start,		0x100000
.equ MEM_sram_length,		0x10000
.equ MEM_da_start,			0x12000000
.equ MEM_da_length,			0x40000
