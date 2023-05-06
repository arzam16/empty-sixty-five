import logging

from src.common import as_0x, as_hex, target_config_to_string


class AbstractPlatform:
    def __init__(self, dev):
        self.dev = dev

    def identify_chip(self):
        pass

    # Initialize power subsystem of a target device. This might include
    # setting up an embedded PMIC (mt6573) or changing some settings
    # related the the 2nd CPU code (mt6577).
    def init_pmic(self):
        pass

    def disable_watchdog(self):
        pass

    # Initialize real-time clock hardware
    def init_rtc(self):
        pass

    # Usually at this stage SP Flash Tool tries to request ME ID and
    # versions of BROM and Preloader. I could not think of any better
    # name for this function.
    def identify_software(self):
        pass

    # Initialize external memory interface
    def init_emi(self):
        pass

    # Push payload bytes to the device
    def send_payload(self, payload):
        pass

    def jump_to_payload(self):
        pass

    # At this point the payload is running. If the payload is a piggyback
    # then the Download Agent it is based on might send some data. We
    # need to receive it order to get everything initialized before it
    # will jump to the piggyback.
    def recv_remaining_data(self):
        pass


class MT6573(AbstractPlatform):
    def __init__(self, dev):
        super().__init__(dev)

    def identify_chip(self):
        self.dev.get_hw_code()
        hw_ver = self.dev.read16(0x70026000, check_status=False)
        sw_ver = self.dev.read16(0x70026004, check_status=False)
        logging.replay(f"HW version: {as_hex(hw_ver, size=2)}")
        logging.replay(f"SW version: {as_hex(sw_ver, size=2)}")

    def init_pmic(self):
        self.dev.write16_verify(0x7002FE84, 0xFF04, 0xFF00)  # KPLED_CON1
        self.dev.write16_verify(0x7002FA0C, 0x2079, 0x3079)  # CHR_CON3
        self.dev.write16_verify(0x7002FA0C, 0x20F9, 0x2079)  # CHR_CON3
        self.dev.write16_verify(0x7002FA08, 0x5200, 0x4700)  # CHR_CON2
        self.dev.write16_verify(0x7002FA18, 0x0000, 0x0010)  # CHR_CON6
        self.dev.write16_verify(0x7002FA00, 0x7AB2, 0x62B2)  # CHR_CON0
        self.dev.write16_verify(0x7002FA20, 0x0800, 0x0000)  # CHR_CON8
        self.dev.write16_verify(0x7002FA28, 0x0100, 0x0000)  # CHR_CON10
        self.dev.write16_verify(0x7002FA24, 0x0180, 0x0080)  # CHR_CON9

    def disable_watchdog(self):
        self.dev.write16(0x70025000, 0x2200)
        self.dev.get_preloader_version()

    def init_rtc(self):
        for addr in [0x70014000, 0x70014050, 0x70014054]:
            val = self.dev.read16(addr)
            logging.replay(f"RTC register {as_0x(addr)} == {as_hex(val, 2)}")

        self.dev.write16(0x70014010, 0x0000)  # Enable all alarm IRQs
        self.dev.write16(0x70014008, 0x0000)  # Disable all IRQ generations
        self.dev.write16(0x7001400C, 0x0000)  # Disable all counter IRQs
        self.dev.write16(0x70014074, 0x0001)  # Commit changes
        val = self.dev.read16(0x70014000)  # 0x0008

        self.dev.write16(0x70014050, 0xA357)  # Write reference value
        self.dev.write16(0x70014054, 0x67D2)  # Write reference value
        self.dev.write16(0x70014074, 0x0001)  # Commit changes
        val = self.dev.read16(0x70014000)  # 0x0008

        self.dev.write16(0x70014068, 0x586A)  # Unlock RTC protection (part 1)
        self.dev.write16(0x70014074, 0x0001)  # Commit changes
        val = self.dev.read16(0x70014000)  # 0x0008

        self.dev.write16(0x70014068, 0x9136)  # Unlock RTC protection (part 2)
        self.dev.write16(0x70014074, 0x0001)  # Commit changes
        val = self.dev.read16(0x70014000)  # 0x0008

        self.dev.write16(0x70014000, 0x430E)  # Enable bus writes + PMIC RTC + auto mode
        self.dev.write16(0x70014074, 0x0001)  # Commit changes
        val = self.dev.read16(0x70014000)  # 0x000E

    def identify_software(self):
        val = self.dev.get_me_id()
        logging.replay(f"ME ID: {as_hex(val)}")
        val = self.dev.get_me_id()

        val = self.dev.get_target_config()
        for line in target_config_to_string(val):
            logging.replay(line)
        val = self.dev.get_target_config()

        val = self.dev.get_brom_version()
        logging.replay(f"BROM version: {as_hex(val, 1)}")
        val = self.dev.get_preloader_version()

    def init_emi(self):
        MT6573_EMI_GENA = 0x70000000
        val = self.dev.read32(MT6573_EMI_GENA)
        self.dev.write32(MT6573_EMI_GENA, 0x00000002)
        logging.replay(
            f"EMI_GENA ({as_0x(MT6573_EMI_GENA)}) "
            f"set to {as_hex(0x2)}, was {as_hex(val)}"
        )

    def send_payload(self, payload):
        val = self.dev.send_da(0x90005000, len(payload), 0, payload)
        logging.replay(f"Received DA checksum: {as_hex(val, 2)}")

    def jump_to_payload(self):
        self.dev.jump_da(0x90005000)

    def recv_remaining_data(self):
        logging.replay("Waiting for device to send remaining data")
        logging.replay(f"<- DA: (unknown) {as_hex(self.dev.read(1))}")  # C0
        logging.replay(f"<- DA: (unknown) {as_hex(self.dev.read(1))}")  # 03
        logging.replay(f"<- DA: (unknown) {as_hex(self.dev.read(1))}")  # 02
        logging.replay(f"<- DA: (unknown) {as_hex(self.dev.read(1))}")  # 83


class MT6577(AbstractPlatform):
    def __init__(self, dev):
        super().__init__(dev)

    def identify_chip(self):
        self.dev.get_hw_code()
        hw_dict = self.dev.get_hw_sw_ver()
        logging.replay(f"HW subcode: {as_hex(hw_dict[0], 2)}")
        logging.replay(f"HW version: {as_hex(hw_dict[1], 2)}")
        logging.replay(f"SW version: {as_hex(hw_dict[2], 2)}")

    def init_pmic(self):
        val = self.dev.read32(0xC0009024)  # PWR_CTL1
        val = self.dev.read32(0xC0009010)  # RST_CTL0
        self.dev.write32(0xC0009010, 0x03000002)
        self.dev.write32(0xC0009010, 0x03000000)
        val = self.dev.read32(0xC0009010)

    def disable_watchdog(self):
        val = self.dev.read16(0xC0000000)
        self.dev.write16(0xC0000000, 0x2264)

        val = self.dev.get_preloader_version()

        for addr in range(0xC0000000, 0xC0000018 + 1, 4):
            val = self.dev.read16(addr)
            logging.replay(f"TOPRGU register {as_0x(addr)} == {as_hex(val)}")

    def init_rtc(self):
        val = self.dev.read16(0xC1003000)  # 0008
        val = self.dev.read16(0xC1003050)  # 0000
        val = self.dev.read16(0xC1003054)  # 0000

        self.dev.write16(0xC1003010, 0x0000)  # RTC_AL_MASK
        self.dev.write16(0xC1003008, 0x0000)  # RTC_IRQ_EN
        self.dev.write16(0xC100300C, 0x0000)  # RTC_CII_EN
        self.dev.write16(0xC1003074, 0x0001)  # Commit changes
        val = self.dev.read16(0xC1003000)  # 0008

        self.dev.write16(0xC1003050, 0xA357)  # Write reference value
        self.dev.write16(0xC1003054, 0x67D2)  # Write reference value
        self.dev.write16(0xC1003074, 0x0001)  # Commit changes
        val = self.dev.read16(0xC1003000)  # 0008

        self.dev.write16(0xC1003068, 0x586A)  # Unlock RTC protection (part 1)
        self.dev.write16(0xC1003074, 0x0001)  # Commit changes
        val = self.dev.read16(0xC1003000)  # 0008

        self.dev.write16(0xC1003068, 0x9136)  # Unlock RTC protection (part 2)
        self.dev.write16(0xC1003074, 0x0001)  # Commit changes
        val = self.dev.read16(0xC1003000)  # 0008

        self.dev.write16(0xC1003000, 0x430E)  # Enable bus writes + PMIC RTC + auto mode
        self.dev.write16(0xC1003074, 0x0001)  # Commit changes
        val = self.dev.read16(0xC1003000)  # 000E

    def identify_software(self):
        val = self.dev.get_me_id()
        logging.replay(f"ME ID: {as_hex(val)}")
        val = self.dev.get_me_id()  # Again

        val = self.dev.get_target_config()
        for line in target_config_to_string(val):
            logging.replay(line)
        val = self.dev.get_target_config()

        val = self.dev.get_brom_version()
        logging.replay(f"BROM version: {as_hex(val, 1)}")
        val = self.dev.get_preloader_version()

    def init_emi(self):
        MT6577_EMI_GENA = 0xC0003070
        val = self.dev.read32(MT6577_EMI_GENA)  # 00000000 on my device
        self.dev.write32(MT6577_EMI_GENA, 0x00000002)
        logging.replay(
            f"EMI_GENA ({as_0x(MT6577_EMI_GENA)}) "
            f"set to {as_hex(0x2)}, was {as_hex(val)}"
        )

    def send_payload(self, payload):
        val = self.dev.send_da(0xC2000000, len(payload), 0, payload)
        logging.replay(f"Received DA checksum: {as_hex(val, 2)}")

    def jump_to_payload(self):
        self.dev.jump_da(0xC2000000)

    def recv_remaining_data(self):
        logging.replay("Waiting for device to send remaining data")
        logging.replay(f"<- DA: (unknown) {as_hex(self.dev.read(1))}")  # C0
        logging.replay(f"<- DA: (unknown) {as_hex(self.dev.read(1))}")  # 03
        logging.replay(f"<- DA: (unknown) {as_hex(self.dev.read(1))}")  # 02
        logging.replay(f"<- DA: (unknown) {as_hex(self.dev.read(1))}")  # 83


class MT6589(AbstractPlatform):
    def __init__(self, dev):
        super().__init__(dev)

    def identify_chip(self):
        hw_dict = self.dev.get_hw_sw_ver()
        logging.replay(f"HW subcode: {as_hex(hw_dict[0], 2)}")
        logging.replay(f"HW version: {as_hex(hw_dict[1], 2)}")
        logging.replay(f"SW version: {as_hex(hw_dict[2], 2)}")
        self.dev.uart1_log_enable()

    def init_pmic(self):
        self.dev.power_init(0x80000000, 0)
        val = self.dev.power_read16(0x000E)  # CHR_CON7
        self.dev.set_power_reg(0x000E, 0x1001, 0x1001)  # CHR_CON7
        self.dev.set_power_reg(0x000C, 0x0049, 0x0041)  # CHR_CON6
        self.dev.set_power_reg(0x0008, 0x000C, 0x000F)  # CHR_CON4
        self.dev.set_power_reg(0x001A, 0x0000, 0x0010)  # CHR_CON13
        self.dev.set_power_reg(0x0000, 0x007B, 0x0063)  # CHR_CON0
        self.dev.set_power_reg(0x0020, 0x0009, 0x0001)  # CHR_CON16
        self.dev.power_deinit()

    def disable_watchdog(self):
        self.dev.write32(0x10000000, 0x22002224)

        val = self.dev.get_preloader_version()
        for addr in range(0x10000000, 0x10000018 + 1, 4):
            val = self.dev.read32(addr)
            logging.replay(f"TOPRGU register {as_0x(addr)} == {as_hex(val)}")

    def identify_software(self):
        val = self.dev.get_brom_version()
        logging.replay(f"BROM version: {as_hex(val, 1)}")
        val = self.dev.get_preloader_version()  # Again..?

    def init_emi(self):
        MT6589_EMI_GENA = 0x10203070
        val = self.dev.read32(MT6589_EMI_GENA)  # 00000000 on my device
        self.dev.write32(MT6589_EMI_GENA, 0x00000002)
        logging.replay(
            f"EMI_GENA ({as_0x(MT6589_EMI_GENA)}) "
            f"set to {as_hex(0x2)}, was {as_hex(val)}"
        )

    def send_payload(self, payload):
        val = self.dev.send_da(0x12000000, len(payload), 0, payload)
        logging.replay(f"Received DA checksum: {as_hex(val, 2)}")

    def jump_to_payload(self):
        self.dev.uart1_log_enable()
        self.dev.jump_da(0x12000000)

    def recv_remaining_data(self):
        logging.replay(f"<- DA: (unknown) {as_hex(self.dev.read(1))}")
        logging.replay(f"<- DA: (unknown) {as_hex(self.dev.read(4))}")
        logging.replay(f"<- DA: (unknown) {as_hex(self.dev.read(2))}")
        logging.replay(f"<- DA: (unknown) {as_hex(self.dev.read(10))}")
        logging.replay(f"<- DA: (unknown) {as_hex(self.dev.read(4))}")
        logging.replay(f"<- DA: (EMMC CID) {as_hex(self.dev.read(16))}")

        val = 0x5A
        logging.replay(f"-> DA: (OK) {as_hex(val, 1)}")
        self.dev.write(val)
