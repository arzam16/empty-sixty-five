@ SPDX-License-Identifier: GPL-3.0-only
@ SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

@ void __fastcall putc_uart_wrapper(uint8_t c)
.equ DA_putc_wrapper_uart,	0x12003F3A
@ void __fastcall print_hex_value(uint32_t val, uint32_t width)
.equ DA_print_hex_value,	0x12003F50
@ void __fastcall printf_uart(uint8_t* fmt, uint32_t* arg1, uint32_t arg2, uint32_t arg3)
.equ DA_printf_uart,		0x12003F7C



@ void __fastcall io_usb_write(uint8_t* data, uint32_t len)
.equ DA_io_usb_write,		0x12008E60
@ uint32_t __fastcall io_usb_readl()
.equ DA_io_usb_readl,		0x12009032
@ void __fastcall io_usb_writel(uint32_t val)
.equ DA_io_usb_writel,		0x12009060
