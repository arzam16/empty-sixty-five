# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

import logging

from src.common import as_hex, from_bytes, target_config_to_string
from src.platform import MT6573, MT6577, MT6589


class DeviceManager:
    def __init__(self, dev):
        self.dev = dev
        self.platform = None
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
        else:
            hw_dict = self.dev.get_hw_sw_ver()
            logging.info(f"HW subcode: {as_hex(hw_dict[0], 2)}")
            logging.info(f"HW version: {as_hex(hw_dict[1], 2)}")
            logging.info(f"SW version: {as_hex(hw_dict[2], 2)}")

        brom_ver = self.dev.get_brom_version()
        logging.info(f"BROM version: {as_hex(brom_ver, size=1)}")

        me_id = self.dev.get_me_id()
        logging.info(f"ME ID: {as_hex(me_id)}")

        config = self.dev.get_target_config()
        for line in target_config_to_string(config):
            logging.info(line)

    # Request chip ID and replay its traffic
    def replay(self, payload):
        self.payload = payload

        hw_code = self.dev.get_hw_code()
        logging.replay(f"HW code: {as_hex(hw_code, 2)}")

        if hw_code == 0x6573:
            self.platform = MT6573(self.dev)
        elif hw_code == 0x6575:
            # There are multiple revisions of mt6575 SoCs
            ver = self.dev.get_hw_sw_ver()
            if ver == (0x8B00, 0xCB00, 0xE201):
                logging.replay("Detected MT6575E2")
                self.platform = MT6577(self.dev)
            else:
                raise Exception(
                    "Unsupported hardware " f"{', '.join(as_hex(x, 2) for x in ver)}"
                )
        elif hw_code == 0x6583:  # The code is 0x6583 but the SoC is 6589
            self.platform = MT6589(self.dev)
        else:
            raise Exception("Unsupported hardware!")

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

        logging.replay("Wait for remaining data")
        self.platform.recv_remaining_data()

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
