/* SPDX-License-Identifier: GPL-3.0-only */
/* SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16> */

ENTRY(_init)

MEMORY
{
	DA_RAM (IWX) : ORIGIN = 0x120226d4, LENGTH = 0x200
}

SECTIONS
{
	.text :
	{
		*(.text.init);
		*(.text*);
	}
	
	.rodata :
	{
		*(.rodata);
		*(.rodata.*);
		*(.gnu.linkonce.r.*);
	}
	
	.data : 
	{
		*(.data);
		*(.data.*);
		*(.gnu.linkonce.d.*);
	}
	
	.bss :
	{
		
		*(.bss);
		*(.bss.*);
		*(.gnu.linkonce.b.*);
		
		*(COMMON);
	}
	
	.fill :
	{
		FILL(0);
		. = ORIGIN(DA_RAM) + LENGTH(DA_RAM) - 1;
		BYTE(0);
	}
}
