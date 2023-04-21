/* SPDX-License-Identifier: GPL-3.0-only */
/* SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16> */

/*
* This LD script imitates an initialized .bss section by filling the
* unused space with zeroes.
*/

ENTRY(_init)

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
