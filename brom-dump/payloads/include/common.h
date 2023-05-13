// SPDX-License-Identifier: GPL-3.0-only
// SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

#ifndef H_COMMON
#define H_COMMON

#define ARRAY_SIZE(array) ( sizeof(array) / sizeof((array)[0]) )
#define do_nothing() __asm__("NOP; NOP; NOP; NOP;")

#endif // H_COMMON
