# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

import logging

from src.common import as_hex, from_bytes, target_config_to_string
from src.platform import MT6252, MT6573, MT6577, MT6580, MT6582, MT6589


class DeviceManager:
    def __init__(self, brom):
        self.brom = brom
        self.platform = None
        self.payload = None

    # Print chip IDs
    def identify(self):
        hw_code = self.brom.get_hw_code()

        is_legacy = hw_code == 0x0000
        if not is_legacy:  # print HW code straight away
            logging.info(f"HW code: {as_hex(hw_code, 2)}")

        if is_legacy:  # request HW code in a legacy way
            logging.info("Trying to query legacy device info")
            hw_code = self.brom.read16(0x80010008, check_status=False)
            hw_sub_code = self.brom.read16(0x8001000C, check_status=False)
            hw_ver = self.brom.read16(0x80010000, check_status=False)
            sw_ver = self.brom.read16(0x80010004, check_status=False)
            logging.info(f"HW code: {as_hex(hw_code, 2)}")
            logging.info(f"HW subcode: {as_hex(hw_sub_code, 2)}")
            logging.info(f"HW version: {as_hex(hw_ver, 2)}")
            logging.info(f"SW version: {as_hex(sw_ver, 2)}")
        elif hw_code == 0x6573:  # mt6573 is a bit different ableit not legacy
            hw_ver = self.brom.read16(0x70026000, check_status=False)
            sw_ver = self.brom.read16(0x70026004, check_status=False)
            logging.info(f"HW version: {as_hex(hw_ver, 2)}")
            logging.info(f"SW version: {as_hex(sw_ver, 2)}")
        else:
            hw_dict = self.brom.get_hw_sw_ver()
            logging.info(f"HW subcode: {as_hex(hw_dict[0], 2)}")
            logging.info(f"HW version: {as_hex(hw_dict[1], 2)}")
            logging.info(f"SW version: {as_hex(hw_dict[2], 2)}")

        brom_ver = self.brom.get_brom_version()
        logging.info(f"BROM version: {as_hex(brom_ver, 1)}")

        if is_legacy:
            return  # Legacy devices don't support ME ID and Target Config

        me_id = self.brom.get_me_id()
        logging.info(f"ME ID: {as_hex(me_id)}")

        config = self.brom.get_target_config()
        for line in target_config_to_string(config):
            logging.info(line)

    # Request chip ID and replay its traffic
    def replay(self, payload, simple_mode, skip_remaining_data):
        self.payload = payload

        hw_code = self.brom.get_hw_code()

        is_legacy = hw_code == 0x0000
        if is_legacy:
            logging.info("Trying to query legacy device info")
            hw_code = self.brom.read16(0x80010008, check_status=False)

        logging.replay(f"HW code: {as_hex(hw_code, 2)}")

        if hw_code == 0x6250:
            ver = tuple(
                [
                    self.brom.read16(0x80010000 + x, check_status=False)
                    for x in [0xC, 0x0, 0x4]
                ]
            )
            if ver == (0x8B00, 0xCF00, 0x0101):
                logging.replay("Detected MT6252CA")
                self.platform = MT6252(self.brom)
            else:
                raise Exception(
                    "Unsupported hardware " f"{', '.join(as_hex(x, 2) for x in ver)}"
                )
        elif hw_code == 0x6573:
            self.platform = MT6573(self.brom)
        elif hw_code == 0x6575:
            # There are multiple revisions of mt6575 SoCs
            ver = self.brom.get_hw_sw_ver()
            if ver == (0x8B00, 0xCB00, 0xE201):
                logging.replay("Detected MT6575E2")
                self.platform = MT6577(self.brom)
            else:
                raise Exception(
                    "Unsupported hardware " f"{', '.join(as_hex(x, 2) for x in ver)}"
                )
        elif hw_code == 0x6580:
            self.platform = MT6580(self.brom)
        elif hw_code == 0x6582:
            self.platform = MT6582(self.brom)
        elif hw_code == 0x6583:  # The code is 0x6583 but the SoC is 6589
            self.platform = MT6589(self.brom)
        else:
            raise Exception("Unsupported hardware!")

        if simple_mode:
            logging.replay("Disable watchdog")
            self.platform.disable_watchdog()
        else:
            logging.replay("Identify")
            self.platform.identify_chip()

            logging.replay("Initialize PMIC")
            self.platform.init_pmic()

            logging.replay("Disable watchdog")
            self.platform.disable_watchdog()

            logging.replay("Initialize RTC")
            self.platform.init_rtc()

            logging.replay("Identify software components")
            self.platform.identify_software()

            logging.replay("Initialize external memory interface")
            self.platform.init_emi()

        logging.replay("Send payload")
        self.platform.send_payload(self.payload)

        logging.replay("Jump to payload")
        self.platform.jump_to_payload()

        if skip_remaining_data:
            logging.replay("Do not handle remaining data")
        else:
            logging.replay("Wait for remaining data")
            self.platform.recv_remaining_data()

    def receive_data(self):
        logging.info("Waiting for custom payload response")

        # This function is prone to errors.
        # TODO: add more try-except!

        seq = from_bytes(self.brom.just_read(4), 4)
        if seq == 0x3E4D746B:  # >Mtk
            logging.info("Received HELLO sequence")
        else:
            logging.warning(
                f"Received invalid data {as_hex(seq)}, " "expected HELLO sequence"
            )

        idx = 1
        size = from_bytes(self.brom.just_read(4), 4)
        while size != 0x4D746B3C:  # <Mtk
            logging.info(f"Reading {size} bytes")
            data = self.brom.just_read(size)
            filename = f"dump-{idx}.bin"
            with open(filename, "wb") as fos:
                fos.write(data)
            logging.info(f"Saved to {filename}")

            idx += 1
            size = from_bytes(self.brom.just_read(4), 4)

        logging.info("Received GOODBYE sequence")

    def receive_greedy(self):
        logging.info("Greedy mode! Waiting for incoming data... :)")
        logging.info("Hit Ctrl+C to stop waiting")
        try:
            data = None
            while True:
                data = self.brom.just_read(4)
                if not data:
                    logging.error("Cannot receive data!")
                    break
                logging.info(f"<- DA: {as_hex(data)}")
        except KeyboardInterrupt:
            logging.info("Stopped reading")
