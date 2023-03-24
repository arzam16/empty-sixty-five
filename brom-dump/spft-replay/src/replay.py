# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

import logging

from src.common import as_0x, as_hex


# Request chip ID and replay its traffic
def replay(dev, payload):
    hw_code = dev.get_hw_code()
    logging.replay(f"HW code: {as_hex(hw_code, 2)}")

    if hw_code == 0x6583:
        replay_mt6589(dev, payload)  # The code is 0x6583 but the SoC is 6589
    else:
        logging.critical("Unsupported hardware!")
        exit(1)


def replay_mt6589(dev, payload):
    hw_dict = dev.get_hw_sw_ver()
    logging.replay(f"HW subcode: {as_hex(hw_dict[0], 2)}")
    logging.replay(f"HW version: {as_hex(hw_dict[1], 2)}")
    logging.replay(f"SW version: {as_hex(hw_dict[2], 2)}")

    dev.uart1_log_enable()

    logging.replay("Setting up PMIC")
    dev.power_init(0x80000000, 0)
    val = dev.power_read16(0x000E)
    dev.set_power_reg(0x000E, 0x1001, 0x1001)
    dev.set_power_reg(0x000C, 0x0049, 0x0041)
    dev.set_power_reg(0x0008, 0x000C, 0x000F)
    dev.set_power_reg(0x001A, 0x0000, 0x0010)
    dev.set_power_reg(0x0000, 0x007B, 0x0063)
    dev.set_power_reg(0x0020, 0x0009, 0x0001)
    dev.power_deinit()

    # Disable watchdog timer and dump Reset Generator Unit registers
    logging.replay("Disabling watchdog")
    dev.write32(0x10000000, 0x22002224)

    # SP Flash Tool already knows the device is in BROM mode but still
    # requests the preloader version
    val = dev.get_preloader_version()

    for addr in range(0x10000000, 0x10000018 + 1, 4):
        val = dev.read32(addr)
        logging.replay(f"TOPRGU register {as_0x(addr)} == {as_hex(val)}")

    val = dev.get_brom_version()
    logging.replay(f"BROM version: {as_hex(val, 1)}")
    val = dev.get_preloader_version()  # Again..?

    # External memory interface
    MT6589_EMI_GENA = 0x10203070
    val = dev.read32(MT6589_EMI_GENA)  # 00000000 on my device
    dev.write32(MT6589_EMI_GENA, 0x00000002)
    logging.replay(
        f"EMI_GENA ({as_0x(MT6589_EMI_GENA)}) "
        f"set to {as_hex(0x2)}, was {as_hex(val)}"
    )

    val = dev.send_da(0x12000000, len(payload), 0x100, payload)
    logging.replay(f"Received DA checksum: {as_hex(val, 2)}")

    dev.uart1_log_enable()

    dev.jump_da(0x12000000)

    # Download agent is running and sends some data we have to receive
    # and ACK in order to get everything initialized before it will
    # jump to custom payload.
    logging.replay("Waiting for device to send remaining data")
    logging.replay(f"<- DA: (unknown) {as_hex(dev.read(1))}")
    logging.replay(f"<- DA: (unknown) {as_hex(dev.read(4))}")
    logging.replay(f"<- DA: (unknown) {as_hex(dev.read(2))}")
    logging.replay(f"<- DA: (unknown) {as_hex(dev.read(10))}")
    logging.replay(f"<- DA: (unknown) {as_hex(dev.read(4))}")
    logging.replay(f"<- DA: (EMMC ID) {as_hex(dev.read(16))}")

    val = 0x5A
    logging.replay(f"-> DA: (OK) {as_hex(val, 1)}")
    dev.write(val)
