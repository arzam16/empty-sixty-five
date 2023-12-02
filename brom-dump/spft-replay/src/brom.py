# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2021 Dinolek <https://github.com/Dinolek>
# SPDX-FileContributor: chaosmaster <https://github.com/chaosmaster>
# SPDX-FileContributor: arzamas-16 <https://github.com/arzamas-16>

import logging

from src.common import as_0x, as_hex, from_bytes, to_bytes


class BromProtocol:
    def __init__(self, transport):
        self.transport = transport

    def handshake(self):
        sequence = b"\xA0\x0A\x50\x05"
        i = 0
        while i < len(sequence):
            self.transport.write(sequence[i])
            reply = self.transport.read(1)
            if reply and reply[0] == ~sequence[i] & 0xFF:
                i += 1
            else:
                i = 0
        logging.info("Handshake completed!")

    def read_reg(self, reg_size, addr, amount=1, check_status=True):
        result = []

        # Fall back to 32-bit registers
        read_command = 0xD1
        if reg_size == 16:
            read_command = 0xD0 if check_status else 0xA2
        elif reg_size == 32:
            read_command = 0xD1 if check_status else 0xAF

        self.transport.echo(read_command)
        self.transport.echo(addr, 4)
        self.transport.echo(amount, 4)

        if check_status:
            status = self.transport.read(2)
            if from_bytes(status, 2) > 0xFF:
                raise RuntimeError(f"status is {as_hex(status, 2)}")

        sz = reg_size // 8
        for _ in range(amount):
            data = from_bytes(self.transport.read(sz), sz)
            result.append(data)

        if check_status:
            status = self.transport.read(2)
            if from_bytes(status, 2) > 0xFF:
                raise RuntimeError(f"status is {as_hex(status, 2)}")

        # support scalar
        if len(result) == 1:
            return result[0]
        else:
            return result

    def read16(self, addr, amount=1, check_status=True):
        logging.brom(f"read16({as_0x(addr)})")
        return self.read_reg(16, addr, amount, check_status)

    def read32(self, addr, amount=1, check_status=True):
        logging.brom(f"read32({as_0x(addr)})")
        return self.read_reg(32, addr, amount, check_status)

    # Some SoCs reply with 0x0000 as OK (mt6589), some reply with 0x0001 (mt6580)
    def write_reg(self, reg_size, addr, words, expected_response=0, check_status=True):
        # support scalar
        if not isinstance(words, list):
            words = [words]

        # Fall back to 32-bit registers
        write_command = 0xD4
        if reg_size == 16:
            write_command = 0xD2 if check_status else 0xA1
        elif reg_size == 32:
            write_command = 0xD4 if check_status else 0xAE

        self.transport.echo(write_command)
        self.transport.echo(addr, 4)
        self.transport.echo(len(words), 4)

        if check_status:  # arg check status
            self.transport.check(self.transport.read(2), to_bytes(expected_response, 2))

        for word in words:
            self.transport.echo(word, reg_size // 8)

        if check_status:  # command execution status
            self.transport.check(self.transport.read(2), to_bytes(expected_response, 2))

    def write16(self, addr, words, expected_response=0, check_status=True):
        logging.brom(f"write16({as_hex(addr)}, [{as_hex(words, 2)}])")
        self.write_reg(16, addr, words, expected_response, check_status)

    def write32(self, addr, words, expected_response=0, check_status=True):
        logging.brom(f"write32({as_hex(addr)}, [{as_hex(words)}])")
        self.write_reg(32, addr, words, expected_response, check_status)

    def get_target_config(self):
        logging.brom("Get target config")
        self.transport.echo(0xD8)

        target_config = self.transport.read(4)
        status = self.transport.read(2)

        if from_bytes(status, 2) != 0:
            raise RuntimeError(f"status is {as_hex(status, 2)}")

        return from_bytes(target_config, 4)

    def get_hw_code(self):
        logging.brom("Get HW code")
        self.transport.echo(0xFD)

        hw_code = self.transport.read(2, timeout=200)
        # Very old platforms don't reply this command
        if not hw_code:
            logging.warning("No response to get_hw_code! Is it a legacy device?")
            return 0x0000  # return special value

        status = self.transport.read(2)

        if from_bytes(status, 2) != 0:
            raise RuntimeError(f"status is {as_hex(status, 2)}")
        return from_bytes(hw_code, 2)

    def get_hw_sw_ver(self):
        logging.brom("Get HW/SW version")
        self.transport.echo(0xFC)

        hw_sub_code = self.transport.read(2)
        hw_ver = self.transport.read(2)
        sw_ver = self.transport.read(2)
        status = self.transport.read(2)

        if from_bytes(status, 2) != 0:
            raise RuntimeError(f"status is {as_hex(status, 2)}")

        return from_bytes(hw_sub_code, 2), from_bytes(hw_ver, 2), from_bytes(sw_ver, 2)

    def send_da(self, da_address, da_len, sig_len, da):
        logging.brom(
            f"Send Download Agent to {as_0x(da_address)} "
            f"({da_len} bytes, {sig_len} byte signature)"
        )
        self.transport.echo(0xD7)

        self.transport.echo(da_address, 4)
        self.transport.echo(da_len, 4)
        self.transport.echo(sig_len, 4)

        status = self.transport.read(2)

        if from_bytes(status, 2) != 0:
            raise RuntimeError(f"status is {as_hex(status, 2)}")

        self.transport.write(da)

        checksum = from_bytes(self.transport.read(2), 2)
        status = from_bytes(self.transport.read(2), 2)

        if status != 0:
            raise RuntimeError(f"status is {as_hex(status, 2)}")

        return checksum

    def send_da_legacy(self, da_address, da):
        logging.brom(f"Send Download Agent to {as_0x(da_address)} ({len(da)} bytes)")

        # Legacy SP Flash Tool changes endianness before sending the data.
        da = bytearray(da[: len(da) // 2 * 2])  # remove odd byte if there's any
        for i in range(0, len(da) - 1, 2):
            da[i], da[i + 1] = da[i + 1], da[i]
        da = bytes(da)

        self.transport.echo(0xAD)

        self.transport.echo(da_address, 4)
        self.transport.echo(len(da) // 2, 4)
        self.transport.write(da)

    def checksum_legacy(self, address, size):
        logging.brom(f"Calculating checksum for {size} bytes as {as_0x(address)}")
        self.transport.echo(0xA4)

        self.transport.echo(address, 4)
        self.transport.echo(size // 2, 4)

        checksum = from_bytes(self.transport.read(2), 2)
        return checksum

    def jump_da(self, da_address, check_status=True):
        logging.brom(f"Jump to Download Agent at {as_0x(da_address)}")
        self.transport.echo(0xD5 if check_status else 0xA8)

        self.transport.echo(da_address, 4)

        if not check_status:
            return

        status = self.transport.read(2)

        if from_bytes(status, 2) != 0:
            raise RuntimeError(f"status is {as_hex(status, 2)}")

    def uart1_log_enable(self):
        logging.brom("Enable UART1 logging")
        self.transport.echo(0xDB)

        status = self.transport.read(2)
        if from_bytes(status, 2) != 0:
            raise RuntimeError(f"status is {as_hex(status, 2)}")

    def power_init(self, reg, val):
        logging.brom(f"Init PMIC at {as_0x(reg)} ({as_hex(val)})")
        self.transport.echo(0xC4)

        self.transport.echo(reg, 4)
        self.transport.echo(val, 4)

        status = self.transport.read(2)
        if from_bytes(status, 2) != 0:
            raise RuntimeError(f"status is {as_hex(status, 2)}")

    def power_deinit(self):
        logging.brom("Deinit PMIC")
        self.transport.echo(0xC5)

        status = self.transport.read(2)
        if from_bytes(status, 2) != 0:
            raise RuntimeError(f"status is {as_hex(status, 2)}")

    def power_read16(self, reg):
        logging.brom(f"PMIC read16({as_0x(reg, 2)})")
        self.transport.echo(0xC6)
        self.transport.echo(reg, 2)

        expected = 0
        self.transport.check(self.transport.read(2), to_bytes(expected, 2))  # recv ack
        self.transport.check(
            self.transport.read(2), to_bytes(expected, 2)
        )  # PMIC read status

        result = from_bytes(self.transport.read(2), 2)
        return result

    def power_write16(self, reg, val):
        logging.brom(f"PMIC write16({as_hex(reg)}, {as_hex(val)})")
        self.transport.echo(0xC7)
        self.transport.echo(reg, 2)
        self.transport.echo(val, 2)

        expected = 0
        self.transport.check(self.transport.read(2), to_bytes(expected, 2))  # recv ack
        self.transport.check(
            self.transport.read(2), to_bytes(expected, 2)
        )  # PMIC write status

    def get_me_id(self):
        logging.brom("Get ME ID")
        self.transport.echo(0xE1)

        length = from_bytes(self.transport.read(4), 4)
        if length == 0:
            raise RuntimeError("bad ME ID length")
        me_id = self.transport.read(length)

        status = self.transport.read(2)
        if from_bytes(status, 2) != 0:
            raise RuntimeError(f"status is {as_hex(status, 2)}")

        return me_id

    def get_preloader_version(self):
        logging.brom("Get PRELOADER version")
        self.transport.write(0xFE)

        ver = from_bytes(self.transport.read(1))
        if ver == 0xFE:
            logging.warning("Cannot get PRELOADER version in BROM mode")
        return ver

    def get_brom_version(self):
        logging.brom("Get BROM version")
        self.transport.write(0xFF)

        ver = from_bytes(self.transport.read(1))
        if ver == 0xFF:
            logging.warning("Cannot get BROM version in PRELOADER mode")
        return ver

    def set_power_reg(self, register, new_value, reference_value):
        # Check current value
        # reference_value - a value obtained from the Wireshark dump of my device
        pwr = self.power_read16(register)
        if pwr != reference_value:
            logging.warning("power_read16 returned non-reference value")
        if pwr == new_value:
            logging.debug("power_read16 value is already set, setting anyway")

        # Write even if no change is needed
        pwr = self.power_write16(register, new_value)

        # Check if new value has been set successfully
        pwr = self.power_read16(register)
        if pwr != new_value:
            logging.error(
                f"Could not set PMIC reg {as_0x(register, 2)} "
                f"to {as_hex(new_value, 2)}, "
                f"got {as_hex(pwr, 2)}"
            )

    # Inspired by mt6573 Wireshark dump
    def write16_verify(self, register, new_value, reference_value):
        # reference_value - a value obtained from the Wireshark dump of my device
        old_value = self.read16(register)
        if old_value != reference_value:
            logging.warning(
                f"Read {as_0x(register)}, "
                f"got {as_hex(old_value, size=2)} but "
                f"reference is {as_hex(reference_value, size=2)}"
            )

        self.write16(register, new_value)

        check = self.read16(register)
        if check != new_value:
            logging.warning(
                f"Set {as_0x(register)} "
                f"to {as_hex(new_value, size=2)} but "
                f"it is {as_hex(check, size=2)}"
            )

    # Read bytes from transport without issuing any command.
    # This function proxies the `read` operaion to underlying transport, and
    # it's intended to be used in `platform.py` and `manager.py` because they
    # don't have direct access to transport.
    # Do not call this function from `device.py`.
    def just_read(self, size):
        return self.transport.read(size)

    # Write bytes to transport without issuing any command.
    # This function proxies the `write` operaion to underlying transport, and
    # it's intended to be used in `platform.py` and `manager.py` because they
    # don't have direct access to transport.
    # Do not call this function from `device.py`.
    def just_write(self, data):
        self.transport.write(data)
