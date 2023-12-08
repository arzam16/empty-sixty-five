import logging
import os
import random
from abc import ABC, abstractmethod

from src.common import as_0x, as_hex, target_config_to_string


class AbstractPlatform(ABC):
    @abstractmethod
    def __init__(self, brom):
        self.brom = brom

    @abstractmethod
    def identify_chip(self):
        pass

    # Initialize power subsystem of a target device. This might include
    # setting up an embedded PMIC (mt6573) or changing some settings
    # related the the 2nd CPU code (mt6577).
    @abstractmethod
    def init_pmic(self):
        pass

    @abstractmethod
    def disable_watchdog(self):
        pass

    # Initialize real-time clock hardware
    @abstractmethod
    def init_rtc(self):
        pass

    # Usually at this stage SP Flash Tool tries to request ME ID and
    # versions of BROM and Preloader. I could not think of any better
    # name for this function.
    @abstractmethod
    def identify_software(self):
        pass

    # Initialize external memory interface
    @abstractmethod
    def init_emi(self):
        pass

    # Push payload bytes to the device
    @abstractmethod
    def send_payload(self, payload):
        pass

    @abstractmethod
    def jump_to_payload(self):
        pass

    # At this point the payload is running. If the payload is a piggyback
    # then the Download Agent it is based on might send some data. We
    # need to receive it order to get everything initialized before it
    # will jump to the piggyback.
    @abstractmethod
    def recv_remaining_data(self):
        pass


class MT6252(AbstractPlatform):
    def __init__(self, brom):
        super().__init__(brom)

        # Try to read the 1st-stage DA as early as possible. If we fail
        # here now, the device won't be stuck waiting for us later.
        self.da_1st_stage = None

        # get path to platform.py
        path = os.path.abspath(__file__)
        # relative paths like this are evil but I had no other ideas :(
        path = os.path.join(path, "../../../payloads/build/aux/mt6252-da-1st-stage.bin")
        logging.info(f"Loading 1st-stage DA from {path}")
        with open(os.path.abspath(path), "rb") as fis:
            self.da_1st_stage = fis.read()

    def identify_chip(self):
        for addr in [0x80000000, 0x80000008, 0x8000000C]:
            val = self.brom.read16(addr, check_status=False)
            logging.replay(f"{as_0x(addr)}: {as_hex(val, 2)}")
        # <BROM_DLL.log> Old chip-recognition flow... (brom_base.cpp:1654)
        hw_ver = self.brom.read16(0x80010000, check_status=False)
        hw_code = self.brom.read16(0x80010008, check_status=False)
        hw_sub_code = self.brom.read16(0x8001000C, check_status=False)
        # <BROM_DLL.log> New chip-recognition flow... (brom_base.cpp:1565)
        hw_ver = self.brom.read16(0x80010000, check_status=False)
        sw_ver = self.brom.read16(0x80010004, check_status=False)
        logging.info(f"HW code: {as_hex(hw_code, 2)}")
        logging.info(f"HW subcode: {as_hex(hw_sub_code, 2)}")
        logging.info(f"HW version: {as_hex(hw_ver, 2)}")
        logging.info(f"SW version: {as_hex(sw_ver, 2)}")

    def init_pmic(self):
        pass

    def disable_watchdog(self):
        self.brom.write16(0x80030000, 0x2200, check_status=False)

    def init_rtc(self):
        for addr in [0x810B0000, 0x810B0000, 0x810B0050]:  # 2 repeating addresses
            val = self.brom.read16(addr, check_status=False)
            logging.replay(f"RTC register {as_0x(addr)} == {as_hex(val, 2)}")

        self.brom.write16(0x810B0010, 0x0000, check_status=False)
        self.brom.write16(0x810B0008, 0x0000, check_status=False)
        self.brom.write16(0x810B000C, 0x0000, check_status=False)
        self.brom.write16(0x810B0074, 0x0001, check_status=False)
        val = self.brom.read16(0x810B0000, check_status=False)  # 0x0008

        self.brom.write16(0x810B0050, 0xA357, check_status=False)
        self.brom.write16(0x810B0054, 0x67D2, check_status=False)
        self.brom.write16(0x810B0074, 0x0001, check_status=False)
        val = self.brom.read16(0x810B0000, check_status=False)  # 0x0008

        val = self.brom.read16(0x810B0000, check_status=False)  # 0x0008

        self.brom.write16(0x810B0068, 0x586A, check_status=False)
        self.brom.write16(0x810B0074, 0x0001, check_status=False)
        val = self.brom.read16(0x810B0000, check_status=False)  # 0x0008

        self.brom.write16(0x810B0068, 0x9136, check_status=False)
        self.brom.write16(0x810B0074, 0x0001, check_status=False)
        val = self.brom.read16(0x810B0000, check_status=False)  # 0x0008

        val = self.brom.read16(0x810B0058, check_status=False)
        logging.replay(f"RTC register 0x810B0058: {as_hex(val, 2)}")
        self.brom.write16(0x810B0058, 0x00F1, check_status=False)
        self.brom.write16(0x810B0000, 0x430E, check_status=False)
        self.brom.write16(0x810B0074, 0x0001, check_status=False)
        val = self.brom.read16(0x810B0000, check_status=False)  # 0x000E

        self.brom.write16(0x810B0068, 0x0000, check_status=False)
        self.brom.write16(0x810B0074, 0x0001, check_status=False)
        val = self.brom.read16(0x810B0000, check_status=False)  # 0x000E

    def identify_software(self):
        val = self.brom.get_brom_version()
        logging.replay(f"BROM version: {as_hex(val, 1)}")
        val = self.brom.get_preloader_version()

    def init_emi(self):
        MT6252_SRAM_START = 0x08004000
        self.brom.write16(0x80030000, 0x2200, check_status=False)  # disable WDT again
        self.brom.write32(0x81000044, 0xFFFFFB80, check_status=False)

        for addr in [0x81000074, 0x81000004]:
            val = self.brom.read32(addr, check_status=False)
            logging.replay(f"EMI register {as_0x(addr)} == {as_hex(val, 2)}")

        self.brom.write32(
            MT6252_SRAM_START,
            [0x523C3C3C, 0x425F4D41, 0x4E494745, 0x003E3E3E],
            check_status=False,
        )

        for addr in range(0x08104000, 0x08804000 + 1, 0x80000):
            val = self.brom.read32(addr, 4, check_status=False)
            logging.replay(f"Memory at {as_0x(addr)}: {as_hex(val)}")

        logging.replay("Detect external SRAM size")
        ext_sram_sz = 0
        for addr in range(
            0x08804000, MT6252_SRAM_START - 1, -0x80000
        ):  # backward check
            val = random.sample(range(0, 0xFFFFFFFF), 4)
            self.brom.write32(addr - 4, val, check_status=False)
            test = self.brom.read32(addr - 4, 4, check_status=False)
            if val == test:
                ext_sram_sz = addr - MT6252_SRAM_START
                break
        if ext_sram_sz:
            logging.replay(
                f"SRAM size: {as_0x(ext_sram_sz)} ({ext_sram_sz // 1024} kB)"
            )
        else:
            logging.warning("Could not detect SRAM size!")

    def send_payload(self, payload):
        logging.replay("Push 1st-stage DA")
        self.brom.send_da_legacy(0x40005000, self.da_1st_stage)
        val = self.brom.checksum_legacy(0x08100000, len(self.da_1st_stage))
        logging.replay(f"Received DA checksum: {as_hex(val, 2)}")

        logging.replay("Push 2nd-stage DA (our payload)")
        self.brom.send_da_legacy(0x08100000, payload)
        val = self.brom.checksum_legacy(0x08100000, len(payload))
        logging.replay(f"Received DA checksum: {as_hex(val, 2)}")

    def jump_to_payload(self):
        self.brom.jump_da(0x40005000, check_status=False)

    def recv_remaining_data(self):
        val = self.brom.just_read(4)
        logging.replay(f"<- DA: (Trailer) {as_hex(val)}")


class MT6573(AbstractPlatform):
    def __init__(self, brom):
        super().__init__(brom)

    def identify_chip(self):
        self.brom.get_hw_code()
        hw_ver = self.brom.read16(0x70026000, check_status=False)
        sw_ver = self.brom.read16(0x70026004, check_status=False)
        logging.replay(f"HW version: {as_hex(hw_ver, 2)}")
        logging.replay(f"SW version: {as_hex(sw_ver, 2)}")

    def init_pmic(self):
        self.brom.write16_verify(0x7002FE84, 0xFF04, 0xFF00)  # KPLED_CON1
        self.brom.write16_verify(0x7002FA0C, 0x2079, 0x3079)  # CHR_CON3
        self.brom.write16_verify(0x7002FA0C, 0x20F9, 0x2079)  # CHR_CON3
        self.brom.write16_verify(0x7002FA08, 0x5200, 0x4700)  # CHR_CON2
        self.brom.write16_verify(0x7002FA18, 0x0000, 0x0010)  # CHR_CON6
        self.brom.write16_verify(0x7002FA00, 0x7AB2, 0x62B2)  # CHR_CON0
        self.brom.write16_verify(0x7002FA20, 0x0800, 0x0000)  # CHR_CON8
        self.brom.write16_verify(0x7002FA28, 0x0100, 0x0000)  # CHR_CON10
        self.brom.write16_verify(0x7002FA24, 0x0180, 0x0080)  # CHR_CON9

    def disable_watchdog(self):
        self.brom.write16(0x70025000, 0x2200)
        self.brom.get_preloader_version()

    def init_rtc(self):
        for addr in [0x70014000, 0x70014050, 0x70014054]:
            val = self.brom.read16(addr)
            logging.replay(f"RTC register {as_0x(addr)} == {as_hex(val, 2)}")

        self.brom.write16(0x70014010, 0x0000)  # Enable all alarm IRQs
        self.brom.write16(0x70014008, 0x0000)  # Disable all IRQ generations
        self.brom.write16(0x7001400C, 0x0000)  # Disable all counter IRQs
        self.brom.write16(0x70014074, 0x0001)  # Commit changes
        val = self.brom.read16(0x70014000)  # 0x0008

        self.brom.write16(0x70014050, 0xA357)  # Write reference value
        self.brom.write16(0x70014054, 0x67D2)  # Write reference value
        self.brom.write16(0x70014074, 0x0001)  # Commit changes
        val = self.brom.read16(0x70014000)  # 0x0008

        self.brom.write16(0x70014068, 0x586A)  # Unlock RTC protection (part 1)
        self.brom.write16(0x70014074, 0x0001)  # Commit changes
        val = self.brom.read16(0x70014000)  # 0x0008

        self.brom.write16(0x70014068, 0x9136)  # Unlock RTC protection (part 2)
        self.brom.write16(0x70014074, 0x0001)  # Commit changes
        val = self.brom.read16(0x70014000)  # 0x0008

        self.brom.write16(
            0x70014000, 0x430E
        )  # Enable bus writes + PMIC RTC + auto mode
        self.brom.write16(0x70014074, 0x0001)  # Commit changes
        val = self.brom.read16(0x70014000)  # 0x000E

    def identify_software(self):
        val = self.brom.get_me_id()
        logging.replay(f"ME ID: {as_hex(val)}")
        val = self.brom.get_me_id()

        val = self.brom.get_target_config()
        for line in target_config_to_string(val):
            logging.replay(line)
        val = self.brom.get_target_config()

        val = self.brom.get_brom_version()
        logging.replay(f"BROM version: {as_hex(val, 1)}")
        val = self.brom.get_preloader_version()

    def init_emi(self):
        MT6573_EMI_GENA = 0x70000000
        val = self.brom.read32(MT6573_EMI_GENA)
        self.brom.write32(MT6573_EMI_GENA, 0x00000002)
        logging.replay(
            f"EMI_GENA ({as_0x(MT6573_EMI_GENA)}) "
            f"set to {as_hex(0x2)}, was {as_hex(val)}"
        )

    def send_payload(self, payload):
        val = self.brom.send_da(0x90005000, len(payload), 0, payload)
        logging.replay(f"Received DA checksum: {as_hex(val, 2)}")

    def jump_to_payload(self):
        self.brom.jump_da(0x90005000)

    def recv_remaining_data(self):
        logging.replay("Waiting for device to send remaining data")
        logging.replay(f"<- DA: (unknown) {as_hex(self.brom.just_read(1))}")  # C0
        logging.replay(f"<- DA: (unknown) {as_hex(self.brom.just_read(1))}")  # 03
        logging.replay(f"<- DA: (unknown) {as_hex(self.brom.just_read(1))}")  # 02
        logging.replay(f"<- DA: (unknown) {as_hex(self.brom.just_read(1))}")  # 83


class MT6577(AbstractPlatform):
    def __init__(self, brom):
        super().__init__(brom)

    def identify_chip(self):
        self.brom.get_hw_code()
        hw_dict = self.brom.get_hw_sw_ver()
        logging.replay(f"HW subcode: {as_hex(hw_dict[0], 2)}")
        logging.replay(f"HW version: {as_hex(hw_dict[1], 2)}")
        logging.replay(f"SW version: {as_hex(hw_dict[2], 2)}")

    def init_pmic(self):
        val = self.brom.read32(0xC0009024)  # PWR_CTL1
        val = self.brom.read32(0xC0009010)  # RST_CTL0
        self.brom.write32(0xC0009010, 0x03000002)
        self.brom.write32(0xC0009010, 0x03000000)
        val = self.brom.read32(0xC0009010)

    def disable_watchdog(self):
        val = self.brom.read16(0xC0000000)
        self.brom.write16(0xC0000000, 0x2264)

        val = self.brom.get_preloader_version()

        for addr in range(0xC0000000, 0xC0000018 + 1, 4):
            val = self.brom.read16(addr)
            logging.replay(f"TOPRGU register {as_0x(addr)} == {as_hex(val)}")

    def init_rtc(self):
        val = self.brom.read16(0xC1003000)  # 0008
        val = self.brom.read16(0xC1003050)  # 0000
        val = self.brom.read16(0xC1003054)  # 0000

        self.brom.write16(0xC1003010, 0x0000)  # RTC_AL_MASK
        self.brom.write16(0xC1003008, 0x0000)  # RTC_IRQ_EN
        self.brom.write16(0xC100300C, 0x0000)  # RTC_CII_EN
        self.brom.write16(0xC1003074, 0x0001)  # Commit changes
        val = self.brom.read16(0xC1003000)  # 0008

        self.brom.write16(0xC1003050, 0xA357)  # Write reference value
        self.brom.write16(0xC1003054, 0x67D2)  # Write reference value
        self.brom.write16(0xC1003074, 0x0001)  # Commit changes
        val = self.brom.read16(0xC1003000)  # 0008

        self.brom.write16(0xC1003068, 0x586A)  # Unlock RTC protection (part 1)
        self.brom.write16(0xC1003074, 0x0001)  # Commit changes
        val = self.brom.read16(0xC1003000)  # 0008

        self.brom.write16(0xC1003068, 0x9136)  # Unlock RTC protection (part 2)
        self.brom.write16(0xC1003074, 0x0001)  # Commit changes
        val = self.brom.read16(0xC1003000)  # 0008

        self.brom.write16(
            0xC1003000, 0x430E
        )  # Enable bus writes + PMIC RTC + auto mode
        self.brom.write16(0xC1003074, 0x0001)  # Commit changes
        val = self.brom.read16(0xC1003000)  # 000E

    def identify_software(self):
        val = self.brom.get_me_id()
        logging.replay(f"ME ID: {as_hex(val)}")
        val = self.brom.get_me_id()  # Again

        val = self.brom.get_target_config()
        for line in target_config_to_string(val):
            logging.replay(line)
        val = self.brom.get_target_config()

        val = self.brom.get_brom_version()
        logging.replay(f"BROM version: {as_hex(val, 1)}")
        val = self.brom.get_preloader_version()

    def init_emi(self):
        MT6577_EMI_GENA = 0xC0003070
        val = self.brom.read32(MT6577_EMI_GENA)  # 00000000 on my device
        self.brom.write32(MT6577_EMI_GENA, 0x00000002)
        logging.replay(
            f"EMI_GENA ({as_0x(MT6577_EMI_GENA)}) "
            f"set to {as_hex(0x2)}, was {as_hex(val)}"
        )

    def send_payload(self, payload):
        val = self.brom.send_da(0xC2000000, len(payload), 0, payload)
        logging.replay(f"Received DA checksum: {as_hex(val, 2)}")

    def jump_to_payload(self):
        self.brom.jump_da(0xC2000000)

    def recv_remaining_data(self):
        pass


class MT6580(AbstractPlatform):
    def __init__(self, brom):
        super().__init__(brom)

    def identify_chip(self):
        hw_dict = self.brom.get_hw_sw_ver()
        logging.replay(f"HW subcode: {as_hex(hw_dict[0], 2)}")
        logging.replay(f"HW version: {as_hex(hw_dict[1], 2)}")
        logging.replay(f"SW version: {as_hex(hw_dict[2], 2)}")
        # The 0x10009000~0x1000A000 region is allocated to EFUSE controller.
        # It is barely documented even in datasheets but the specified offset
        # should contain some sort of additional SoC revision codes.
        val = self.brom.read32(0x10009040)
        logging.replay(f"0x10009040: {as_hex(val)}")

    def init_pmic(self):
        pass

    def disable_watchdog(self):
        self.brom.write32(
            0x10007000, 0x22000064, expected_response=0x0001
        )  # TOPRGU_WDT_MODE

    def init_rtc(self):
        pass

    def identify_software(self):
        val = self.brom.get_preloader_version()
        val = self.brom.get_me_id()
        val = self.brom.get_me_id()  # repeated twice
        logging.replay(f"ME ID: {as_hex(val)}")
        val = self.brom.get_target_config()
        val = self.brom.get_target_config()  # repeated twice
        logging.replay(f"Target config: {as_hex(val)}")
        val = self.brom.get_brom_version()
        logging.replay(f"BROM version: {as_hex(val, 1)}")
        val = self.brom.get_preloader_version()

    def init_emi(self):
        pass

    def send_payload(self, payload):
        val = self.brom.send_da(0x200000, len(payload), 0, payload)
        logging.replay(f"Received DA checksum: {as_hex(val, 2)}")

    def jump_to_payload(self):
        self.brom.jump_da(0x200000)

    def recv_remaining_data(self):
        pass


class MT6582(AbstractPlatform):
    def __init__(self, brom):
        super().__init__(brom)

    def identify_chip(self):
        hw_dict = self.brom.get_hw_sw_ver()
        logging.replay(f"HW subcode: {as_hex(hw_dict[0], 2)}")
        logging.replay(f"HW version: {as_hex(hw_dict[1], 2)}")
        logging.replay(f"SW version: {as_hex(hw_dict[2], 2)}")
        # The 0x10206000~0x10207000 region is allocated to EFUSE controller.
        # It is barely documented even in datasheets but the specified offset
        # should contain some sort of additional SoC revision codes.
        val = self.brom.read32(0x10206044)
        logging.replay(f"0x10206044: {as_hex(val)}")

    def init_pmic(self):
        pass

    def disable_watchdog(self):
        self.brom.write32(
            0x10007000, 0x22000064, expected_response=0x0001
        )  # TOPRGU_WDT_MOD

    def init_rtc(self):
        pass

    def identify_software(self):
        val = self.brom.get_preloader_version()
        val = self.brom.get_me_id()
        logging.replay(f"ME ID: {as_hex(val)}")
        val = self.brom.get_preloader_version()  # repeated twice
        pass

    def init_emi(self):
        pass

    def send_payload(self, payload):
        val = self.brom.send_da(0x200000, len(payload), 0, payload)
        logging.replay(f"Received DA checksum: {as_hex(val, 2)}")

    def jump_to_payload(self):
        self.brom.jump_da(0x200000)

    def recv_remaining_data(self):
        pass


class MT6589(AbstractPlatform):
    def __init__(self, brom):
        super().__init__(brom)

    def identify_chip(self):
        hw_dict = self.brom.get_hw_sw_ver()
        logging.replay(f"HW subcode: {as_hex(hw_dict[0], 2)}")
        logging.replay(f"HW version: {as_hex(hw_dict[1], 2)}")
        logging.replay(f"SW version: {as_hex(hw_dict[2], 2)}")
        self.brom.uart1_log_enable()

    def init_pmic(self):
        self.brom.power_init(0x80000000, 0)
        val = self.brom.power_read16(0x000E)  # CHR_CON7
        self.brom.set_power_reg(0x000E, 0x1001, 0x1001)  # CHR_CON7
        self.brom.set_power_reg(0x000C, 0x0049, 0x0041)  # CHR_CON6
        self.brom.set_power_reg(0x0008, 0x000C, 0x000F)  # CHR_CON4
        self.brom.set_power_reg(0x001A, 0x0000, 0x0010)  # CHR_CON13
        self.brom.set_power_reg(0x0000, 0x007B, 0x0063)  # CHR_CON0
        self.brom.set_power_reg(0x0020, 0x0009, 0x0001)  # CHR_CON16
        self.brom.power_deinit()

    def disable_watchdog(self):
        self.brom.write32(0x10000000, 0x22002224)

        val = self.brom.get_preloader_version()
        for addr in range(0x10000000, 0x10000018 + 1, 4):
            val = self.brom.read32(addr)
            logging.replay(f"TOPRGU register {as_0x(addr)} == {as_hex(val)}")

    def init_rtc(self):
        pass

    def identify_software(self):
        val = self.brom.get_brom_version()
        logging.replay(f"BROM version: {as_hex(val, 1)}")
        val = self.brom.get_preloader_version()  # Again..?

    def init_emi(self):
        MT6589_EMI_GENA = 0x10203070
        val = self.brom.read32(MT6589_EMI_GENA)  # 00000000 on my device
        self.brom.write32(MT6589_EMI_GENA, 0x00000002)
        logging.replay(
            f"EMI_GENA ({as_0x(MT6589_EMI_GENA)}) "
            f"set to {as_hex(0x2)}, was {as_hex(val)}"
        )

    def send_payload(self, payload):
        val = self.brom.send_da(0x12000000, len(payload), 0, payload)
        logging.replay(f"Received DA checksum: {as_hex(val, 2)}")

    def jump_to_payload(self):
        self.brom.uart1_log_enable()
        self.brom.jump_da(0x12000000)

    def recv_remaining_data(self):
        logging.replay(f"<- DA: (unknown) {as_hex(self.brom.just_read(1))}")
        logging.replay(f"<- DA: (unknown) {as_hex(self.brom.just_read(4))}")
        logging.replay(f"<- DA: (unknown) {as_hex(self.brom.just_read(2))}")
        logging.replay(f"<- DA: (unknown) {as_hex(self.brom.just_read(10))}")
        logging.replay(f"<- DA: (unknown) {as_hex(self.brom.just_read(4))}")
        logging.replay(f"<- DA: (EMMC CID) {as_hex(self.brom.just_read(16))}")

        val = 0x5A
        logging.replay(f"-> DA: (OK) {as_hex(val, 1)}")
        self.brom.just_write(val)
