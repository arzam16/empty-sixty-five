# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

import logging

from src.common import as_0x, as_hex, from_bytes


class DeviceManager:
    def __init__(self, dev):
        self.dev = dev
        self.payload = None

    # Print chip IDs
    def identify(self):
        hw_code = self.dev.get_hw_code()
        logging.info(f"HW code: {as_hex(hw_code, 2)}")

        # mt6573 is a bit different
        if hw_code == 0x6573:
            hw_ver = self.dev.read16(0x70026000, check_status=False)
            sw_ver = self.dev.read16(0x70026004, check_status=False)
            logging.info(f"HW version: {as_hex(hw_ver, size=2)}")
            logging.info(f"SW version: {as_hex(sw_ver, size=2)}")
            return (hw_code, hw_ver, sw_ver)

        hw_dict = self.dev.get_hw_sw_ver()
        logging.info(f"HW subcode: {as_hex(hw_dict[0], 2)}")
        logging.info(f"HW version: {as_hex(hw_dict[1], 2)}")
        logging.info(f"SW version: {as_hex(hw_dict[2], 2)}")
        return (hw_code, *hw_dict)

    # Request chip ID and replay its traffic
    def replay(self, payload):
        self.payload = payload

        hw_code = self.dev.get_hw_code()
        logging.replay(f"HW code: {as_hex(hw_code, 2)}")

        if hw_code == 0x6573:
            self.replay_mt6573()
        elif hw_code == 0x6583:  # The code is 0x6583 but the SoC is 6589
            self.replay_mt6589()
        else:
            logging.critical("Unsupported hardware!")
            exit(1)

    def replay_mt6573(self):
        # use local variable to avoid lots of `self.dev`
        dev = self.dev

        dev.get_hw_code()  # Yes, SP Flash Tool requests it twice

        hw_ver = dev.read16(0x70026000, check_status=False)
        sw_ver = dev.read16(0x70026004, check_status=False)
        logging.replay(f"HW version: {as_hex(hw_ver, size=2)}")
        logging.replay(f"SW version: {as_hex(sw_ver, size=2)}")

        logging.replay("Setting up PMIC")
        dev.write16_verify(0x7002FE84, 0xFF04, 0xFF00)  # KPLED_CON1
        dev.write16_verify(0x7002FA0C, 0x2079, 0x3079)  # CHR_CON3
        dev.write16_verify(0x7002FA0C, 0x20F9, 0x2079)  # CHR_CON3
        dev.write16_verify(0x7002FA08, 0x5200, 0x4700)  # CHR_CON2
        dev.write16_verify(0x7002FA18, 0x0000, 0x0010)  # CHR_CON6
        dev.write16_verify(0x7002FA00, 0x7AB2, 0x62B2)  # CHR_CON0
        dev.write16_verify(0x7002FA20, 0x0800, 0x0000)  # CHR_CON8
        dev.write16_verify(0x7002FA28, 0x0100, 0x0000)  # CHR_CON10
        dev.write16_verify(0x7002FA24, 0x0180, 0x0080)  # CHR_CON9

        logging.replay("Disabling watchdog")
        dev.write16(0x70025000, 0x2200)

        # SP Flash Tool already knows the device is in BROM mode but still
        # requests the preloader version
        val = dev.get_preloader_version()

        logging.replay("Setup RTC")
        for addr in [0x70014000, 0x70014050, 0x70014054]:
            val = dev.read16(addr)
            logging.replay(f"RTC register {as_0x(addr)} == {as_hex(val, 2)}")

        dev.write16(0x70014010, 0x0000)  # Enable all alarm IRQs
        dev.write16(0x70014008, 0x0000)  # Disable all IRQ generations
        dev.write16(0x7001400C, 0x0000)  # Disable all counter IRQs
        dev.write16(0x70014074, 0x0001)  # Commit changes
        val = dev.read16(0x70014000)  # 0x0008

        dev.write16(0x70014050, 0xA357)  # Write reference value
        dev.write16(0x70014054, 0x67D2)  # Write reference value
        dev.write16(0x70014074, 0x0001)  # Commit changes
        val = dev.read16(0x70014000)  # 0x0008

        dev.write16(0x70014068, 0x586A)  # Unlock RTC protection (part 1)
        dev.write16(0x70014074, 0x0001)  # Commit changes
        val = dev.read16(0x70014000)  # 0x0008

        dev.write16(0x70014068, 0x9136)  # Unlock RTC protection (part 2)
        dev.write16(0x70014074, 0x0001)  # Commit changes
        val = dev.read16(0x70014000)  # 0x0008

        dev.write16(0x70014000, 0x430E)  # Enable bus writes + PMIC RTC + auto mode
        dev.write16(0x70014074, 0x0001)  # Commit changes
        val = dev.read16(0x70014000)  # 0x000E

        val = dev.get_me_id()
        logging.replay(f"ME ID: {as_hex(val)}")
        val = dev.get_me_id()  # Again

        val = dev.get_target_config()
        logging.replay(f"Target config: {val}")
        val = dev.get_target_config()

        val = dev.get_brom_version()
        logging.replay(f"BROM version: {as_hex(val, 1)}")
        val = dev.get_preloader_version()

        # External memory interface
        MT6573_EMI_GENA = 0x70000000
        val = dev.read32(MT6573_EMI_GENA)  # 00000000 on my device
        dev.write32(MT6573_EMI_GENA, 0x00000002)
        logging.replay(
            f"EMI_GENA ({as_0x(MT6573_EMI_GENA)}) "
            f"set to {as_hex(0x2)}, was {as_hex(val)}"
        )

        val = dev.send_da(0x90005000, len(self.payload), 0, self.payload)
        logging.replay(f"Received DA checksum: {as_hex(val, 2)}")

        dev.jump_da(0x90005000)

        # Download Agent is running and sends some data we have to receive
        # and ACK in order to get everything initialized before it will
        # jump to custom payload.
        logging.replay("Waiting for device to send remaining data")
        logging.replay(f"<- DA: (unknown) {as_hex(dev.read(1))}")  # C0
        logging.replay(f"<- DA: (unknown) {as_hex(dev.read(1))}")  # 03
        logging.replay(f"<- DA: (unknown) {as_hex(dev.read(1))}")  # 02
        logging.replay(f"<- DA: (unknown) {as_hex(dev.read(1))}")  # 83

    def replay_mt6589(self):
        # use local variable to avoid lots of `self.dev`
        dev = self.dev

        hw_dict = dev.get_hw_sw_ver()
        logging.replay(f"HW subcode: {as_hex(hw_dict[0], 2)}")
        logging.replay(f"HW version: {as_hex(hw_dict[1], 2)}")
        logging.replay(f"SW version: {as_hex(hw_dict[2], 2)}")

        dev.uart1_log_enable()

        logging.replay("Setting up PMIC")
        dev.power_init(0x80000000, 0)
        val = dev.power_read16(0x000E)  # CHR_CON7
        dev.set_power_reg(0x000E, 0x1001, 0x1001)  # CHR_CON7
        dev.set_power_reg(0x000C, 0x0049, 0x0041)  # CHR_CON6
        dev.set_power_reg(0x0008, 0x000C, 0x000F)  # CHR_CON4
        dev.set_power_reg(0x001A, 0x0000, 0x0010)  # CHR_CON13
        dev.set_power_reg(0x0000, 0x007B, 0x0063)  # CHR_CON0
        dev.set_power_reg(0x0020, 0x0009, 0x0001)  # CHR_CON16
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

        val = dev.send_da(0x12000000, len(self.payload), 0, self.payload)
        logging.replay(f"Received DA checksum: {as_hex(val, 2)}")

        dev.uart1_log_enable()

        dev.jump_da(0x12000000)

        # Download Agent is running and sends some data we have to receive
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

    def receive_data(self):
        logging.info("Waiting for custom payload response")

        # This function is prone to errors.
        # TODO: add more try-except!

        seq = from_bytes(self.dev.read(4), 4)
        if seq == 0x3E4D746B:  # >Mtk
            logging.info("Received HELLO sequence")
        else:
            logging.warning(
                f"Received invalid data {as_hex(seq)}, " "expected HELLO sequence"
            )

        idx = 1
        size = from_bytes(self.dev.read(4), 4)
        while size != 0x4D746B3C:  # <Mtk
            logging.info(f"Reading {size} bytes")
            data = self.dev.read(size)
            filename = f"dump-{idx}.bin"
            with open(filename, "wb") as fos:
                fos.write(data)
            logging.info(f"Saved to {filename}")

            idx += 1
            size = from_bytes(self.dev.read(4), 4)

        logging.info("Received GOODBYE sequence")

    def receive_greedy(self):
        logging.info("Greedy mode! Waiting for incoming data... :)")
        logging.info("Hit Ctrl+C to stop waiting")
        try:
            data = None
            while True:
                data = self.dev.read(4)
                if not data:
                    logging.error("Cannot receive data!")
                    break
                logging.info(f"<- DA: {as_hex(data)}")
        except KeyboardInterrupt:
            logging.info("Stopped reading")

    def finish(self):
        self.dev.close()
