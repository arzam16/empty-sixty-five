.include "da-api.s"
.include "hw-api.s"


    .syntax unified
    .global _main
_main:
    LDR R1, =usb_seq_hello
    LDR R0, [R1]
    BL DA_io_usb_writel

    LDR R0, =dump_task_brom     @ dump BootROM
    BL usb_dump
    LDR R0, =dump_task_sram     @ dump SRAM
    BL usb_dump
    LDR R0, =dump_task_da       @ dump Download Agent
    BL usb_dump

    LDR R1, =usb_seq_goodbye
    LDR R0, [R1]
    BL DA_io_usb_writel
busy_wait:
    NOP
    B busy_wait                 @ do not go any further, must reset manually!



.func usb_dump
usb_dump:
    PUSH {R5, LR}
    PUSH {R0}                   @ save dump_task pointer on stack

    MOV R5, R0
    LDMIA R5!, {R0, R1}         @ offset -> R0, length -> R1
    MOV R0, R1                  @ length -> R0
    BL DA_io_usb_writel         @ DA_io_usb_writel(length)

    POP {R5}                    @ load dump_task pointer from task
    LDMIA R5!, {R0, R1}         @ offset -> R0, length -> R1
    BL DA_io_usb_write          @ DA_io_usb_write(offset, length)

    POP {R5, PC}
.endfunc



.data
usb_seq_hello:
    .word 0x3E4D746B
usb_seq_goodbye:
    .word 0x4D746B3C
dump_task_brom:
    .word MEM_brom_start        @ offset
    .word MEM_brom_length       @ length
dump_task_sram:
    .word MEM_sram_start        @ offset
    .word MEM_sram_length       @ length
dump_task_da:
    .word MEM_da_start          @ offset
    .word MEM_da_length         @ length
