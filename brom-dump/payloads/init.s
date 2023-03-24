@ SPDX-License-Identifier: GPL-3.0-only
@ SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

    .include "hw-api.s"


    .syntax unified
    .section .text.init
    .global _init
_init:
    LDR R0, =MEM_stack_base
    CPY SP, R0                  @ reset stack pointer

    MOVS R0, #0
    MOV R1, #0
    MOV R2, #0
    MOV R3, #0
    MOV R4, #0
    MOV R5, #0
    MOV R6, #0
    MOV R7, #0
    MOV R8, #0
    MOV R9, #0
    MOV R10, #0
    MOV R11, #0
    MOV R12, #0
    MOV R14, #0                 @ reset link register
    B _main
