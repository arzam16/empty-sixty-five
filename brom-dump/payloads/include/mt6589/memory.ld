/* SPDX-License-Identifier: GPL-3.0-only */
/* SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16> */

MEMORY
{
	DA_RAM (IWX) : ORIGIN = 0x120226d4, LENGTH = 0x800
}

INCLUDE payload.ld
