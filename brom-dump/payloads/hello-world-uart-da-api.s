@ SPDX-License-Identifier: GPL-3.0-only
@ SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

    .include "da-api.s"
	.include "hw-api.s"


	.syntax unified
	.global _main
_main:
	LDR R0, =str_hello_world
	LDR R1, =HW_reg_chip_id
	LDR R1, [R1]
	MOV R2, #0
	MOV R3, #0
	BL DA_printf_uart
	
	MOV R0, #0x12
	MOV R1, #2
	BL DA_print_hex_value
	MOV R0, #'\n'
	BL DA_putc_wrapper_uart
	
	LDR R0, =val_1
	LDR R0, [R0]
	MOV R1, #4
	BL DA_print_hex_value
	MOV R0, #'\n'
	BL DA_putc_wrapper_uart
	
	LDR R0, =val_2
	LDR R0, [R0]
	MOV R1, #8
	BL DA_print_hex_value
	MOV R0, #'\n'
	BL DA_putc_wrapper_uart
	
	MOV R4, #0
sequence_test_loop:
	MOV R0, R4
	MOV R1, #2
	BL DA_print_hex_value
	MOV R0, #' '
	BL DA_putc_wrapper_uart
	ADD R4, R4, #1
	CMP R4, #0x10
	BLT sequence_test_loop
sequence_test_loop_end:
	MOV R0, #'\n'
	BL DA_putc_wrapper_uart
	
	MOV R0, #':'
	BL DA_putc_wrapper_uart
	MOV R0, #')'
	BL DA_putc_wrapper_uart
	MOV R0, #'\n'
	BL DA_putc_wrapper_uart
busy_wait:
	NOP
	B busy_wait					@ do not go any further, must reset manually!



.data
str_hello_world:
	.asciz "\n\n\nHello from mt%x!\n"
	.align 4
val_1:
	.word 0x3456
val_2:
	.word 0x789ABCDE
