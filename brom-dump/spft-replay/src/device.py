# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2021 Dinolek <https://github.com/Dinolek>
# SPDX-FileContributor: chaosmaster <https://github.com/chaosmaster>
# SPDX-FileContributor: arzamas-16 <https://github.com/arzamas-16>

import array
import logging
import time

import usb
import usb.backend.libusb1

from src.common import as_0x, as_hex, from_bytes, report_write_progress, to_bytes

BAUD = 115200
TIMEOUT = 3
VID = 0x0E8D
PID = 0x0003


class Device:
    def __init__(self, port=None):
        self.udev = None
        self.dev = None
        self.rxbuffer = array.array("B")
        self.timeout = TIMEOUT

    def find(self):
        if self.dev:
            raise Exception("Device already found!")

        self.backend = usb.backend.libusb1.get_backend()

        logging.info(
            f"Waiting for device in BROM mode " f"({as_hex(VID, 2)}:{as_hex(PID, 2)})"
        )
        self.udev = None
        while not self.udev:
            self.udev = usb.core.find(idVendor=VID, idProduct=PID, backend=self.backend)
            if self.udev:
                break
            time.sleep(0.25)

        logging.info("Found device")
        self.dev = self

        try:
            if self.udev.is_kernel_driver_active(0):
                self.udev.detach_kernel_driver(0)
            if self.udev.is_kernel_driver_active(1):
                self.udev.detach_kernel_driver(1)
        except:
            logging.exception("USB: Cannot detach kernel driver")
            return None

        try:
            self.configuration = self.udev.get_active_configuration()
        except:
            logging.exception("USB: Cannot request configuration")
            return None

        try:
            self.udev.set_configuration(1)
            usb.util.claim_interface(self.udev, 0)
            usb.util.claim_interface(self.udev, 1)
        except:
            logging.exception("USB: Cannot claim interface")
            return None

        try:
            cdc_if = usb.util.find_descriptor(
                self.udev.get_active_configuration(), bInterfaceClass=0xA
            )
            self.ep_in = usb.util.find_descriptor(
                cdc_if,
                custom_match=lambda x: usb.util.endpoint_direction(x.bEndpointAddress)
                == usb.util.ENDPOINT_IN,
            )
            self.ep_out = usb.util.find_descriptor(
                cdc_if,
                custom_match=lambda x: usb.util.endpoint_direction(x.bEndpointAddress)
                == usb.util.ENDPOINT_OUT,
            )
        except:
            logging.exception("USB: Cannot configure endpoints")
            return None

        try:
            self.udev.ctrl_transfer(
                0x21,
                0x20,
                0,
                0,
                array.array("B", to_bytes(BAUD, 4, "<") + b"\x00\x00\x08"),
            )
        except:
            logging.exception("USB: Cannot set baudrate")
            return None

        return self

    @staticmethod
    def check(test, gold):
        if test != gold:
            test = as_hex(test)
            gold = as_hex(gold)
            raise RuntimeError(f"Unexpected output, expected {gold} got {test}")

    def close(self):
        self.dev = None
        self.rxbuffer = array.array("B")

        try:
            usb.util.release_interface(self.udev, 0)
            usb.util.release_interface(self.udev, 1)
        except Exception:
            logging.debug("USB: Could not release interfaces")

        try:
            self.udev.reset()
        except Exception:
            logging.debug("USB: Could not reset device")

        for i in range(0, 2):
            try:
                self.udev.attach_kernel_driver(i)
            except Exception:
                logging.debug(f"USB: Could not reattach kernel driver on interface {i}")

        try:
            usb.util.dispose_resources(self.udev)
        except Exception:
            logging.debug("USB: Could not dispose resources")

        self.udev = None
        time.sleep(1)

    def handshake(self):
        sequence = b"\xA0\x0A\x50\x05"
        i = 0
        while i < len(sequence):
            self.write(sequence[i])
            reply = self.read(1)
            if reply and reply[0] == ~sequence[i] & 0xFF:
                i += 1
            else:
                i = 0
        logging.info("Handshake completed!")

    def echo(self, words, size=1):
        self.write(words, size)
        self.check(from_bytes(self.read(size), size), words)

    def read(self, size=1):
        while len(self.rxbuffer) < size:
            try:
                self.rxbuffer.extend(
                    self.ep_in.read(self.ep_in.wMaxPacketSize, self.timeout * 1000)
                )
            except usb.core.USBError as e:
                if e.errno == 110:
                    self.udev.reset()
                break
        if size <= len(self.rxbuffer):
            result = self.rxbuffer[:size]
            self.rxbuffer = self.rxbuffer[size:]
        else:
            result = self.rxbuffer
            self.rxbuffer = array.array("B")

        result = bytes(result)
        logging.brom_io(f"<- {as_hex(result)}")
        return result

    def read_reg(self, reg_size, addr, amount=1, check_status=True):
        result = []

        # Fall back to 32-bit registers
        read_command = 0xD1
        if reg_size == 16 and check_status:
            read_command = 0xD0
        elif reg_size == 16 and not check_status:
            read_command = 0xA2

        self.echo(read_command)
        self.echo(addr, 4)
        self.echo(amount, 4)

        if check_status:
            status = self.read(2)
            if from_bytes(status, 2) > 0xFF:
                raise RuntimeError(f"status is {as_hex(status, 2)}")

        sz = reg_size // 8
        for _ in range(amount):
            data = from_bytes(self.read(sz), sz)
            result.append(data)

        if check_status:
            status = self.read(2)
            if from_bytes(status, 2) > 0xFF:
                raise RuntimeError(f"status is {as_hex(status, 2)}")

        # support scalar
        if len(result) == 1:
            return result[0]
        else:
            return result

    def read16(self, addr, amount=1, check_status=True):
        logging.brom(f"read16({as_0x(addr)})")
        return self.read_reg(16, addr, amount=amount, check_status=check_status)

    def read32(self, addr, amount=1):
        logging.brom(f"read32({as_0x(addr)})")
        return self.read_reg(32, addr, amount=amount)

    def write(self, data, size=1):
        if type(data) != bytes:
            data = to_bytes(data, size)

        data_sz = len(data)
        # pkt_sz = self.ep_out.wMaxPacketSize
        pkt_sz = 1024  # SP Flash Tool seems to ignore wMaxPacketSize

        off_start = 0
        while off_start < data_sz:
            remaining = data_sz - off_start
            off_end = off_start + (pkt_sz if remaining > pkt_sz else remaining)
            chunk = data[off_start:off_end]
            logging.brom_io(f"-> {as_hex(chunk)}")
            self.ep_out.write(data[off_start:off_end], self.timeout * 1000)
            report_write_progress(off_start, off_end, data_sz)

            off_start += pkt_sz

    # Some SoCs reply with 0x0000 as OK (mt6589), some reply with 0x0001 (mt6580)
    def write_reg(self, reg_size, addr, words, expected_response=0, check_status=True):
        # support scalar
        if not isinstance(words, list):
            words = [words]

        # Fall back to 32-bit registers
        write_command = 0xD2 if reg_size == 16 else 0xD4
        self.echo(write_command)
        self.echo(addr, 4)
        self.echo(len(words), 4)

        self.check(self.read(2), to_bytes(expected_response, 2))  # arg check

        for word in words:
            self.echo(word, reg_size // 8)

        if check_status:
            self.check(self.read(2), to_bytes(expected_response, 2))  # status

    def write16(self, addr, words, expected_response=0, check_status=True):
        logging.brom(f"write16({as_hex(addr)}, [{as_hex(words, 2)}])")
        self.write_reg(16, addr, words, expected_response, check_status)

    def write32(self, addr, words, expected_response=0, check_status=True):
        logging.brom(f"write32({as_hex(addr)}, [{as_hex(words)}])")
        self.write_reg(32, addr, words, expected_response, check_status)

    def get_target_config(self):
        logging.brom("Get target config")
        self.echo(0xD8)

        target_config = self.read(4)
        status = self.read(2)

        if from_bytes(status, 2) != 0:
            raise RuntimeError(f"status is {as_hex(status, 2)}")

        return from_bytes(target_config, 4)

    def get_hw_code(self):
        logging.brom("Get HW code")
        self.echo(0xFD)

        hw_code = self.read(2)
        status = self.read(2)

        if from_bytes(status, 2) != 0:
            raise RuntimeError(f"status is {as_hex(status, 2)}")
        return from_bytes(hw_code, 2)

    def get_hw_sw_ver(self):
        logging.brom("Get HW/SW version")
        self.echo(0xFC)

        hw_sub_code = self.read(2)
        hw_ver = self.read(2)
        sw_ver = self.read(2)
        status = self.read(2)

        if from_bytes(status, 2) != 0:
            raise RuntimeError(f"status is {as_hex(status, 2)}")

        return from_bytes(hw_sub_code, 2), from_bytes(hw_ver, 2), from_bytes(sw_ver, 2)

    def send_da(self, da_address, da_len, sig_len, da):
        logging.brom(
            f"Send Download Agent to {as_0x(da_address)} "
            f"({da_len} bytes, {sig_len} byte signature)"
        )
        self.echo(0xD7)

        self.echo(da_address, 4)
        self.echo(da_len, 4)
        self.echo(sig_len, 4)

        status = self.read(2)

        if from_bytes(status, 2) != 0:
            raise RuntimeError(f"status is {as_hex(status, 2)}")

        self.write(da)

        checksum = from_bytes(self.read(2), 2)
        status = from_bytes(self.read(2), 2)

        if status != 0:
            raise RuntimeError(f"status is {as_hex(status, 2)}")

        return checksum

    def jump_da(self, da_address):
        logging.brom(f"Jump to Download Agent at {as_0x(da_address)}")
        self.echo(0xD5)

        self.echo(da_address, 4)

        status = self.read(2)

        if from_bytes(status, 2) != 0:
            raise RuntimeError(f"status is {as_hex(status, 2)}")

    def cmd_da(self, direction, offset, length, data=None, check_status=True):
        logging.brom(f"DA: {as_hex([direction, offset, length], 4)}")
        self.echo(0xDA)

        self.echo(direction, 4)
        self.echo(offset, 4)
        self.echo(length, 4)

        status = self.read(2)

        if from_bytes(status, 2) != 0:
            raise RuntimeError(f"status is {as_hex(status, 2)}")

        if (direction & 1) == 1:
            self.write(data)
        else:
            data = self.read(length)

        if check_status:
            status = self.read(2)
            if from_bytes(status, 2) != 0:
                raise RuntimeError(f"status is {as_hex(status, 2)}")

        return data

    def uart1_log_enable(self):
        logging.brom("Enable UART1 logging")
        self.echo(0xDB)

        status = self.read(2)
        if from_bytes(status, 2) != 0:
            raise RuntimeError(f"status is {as_hex(status, 2)}")

    def power_init(self, reg, val):
        logging.brom(f"Init PMIC at {as_0x(reg)} ({as_hex(val)})")
        self.echo(0xC4)

        self.echo(reg, 4)
        self.echo(val, 4)

        status = self.read(2)
        if from_bytes(status, 2) != 0:
            raise RuntimeError(f"status is {as_hex(status, 2)}")

    def power_deinit(self):
        logging.brom("Deinit PMIC")
        self.echo(0xC5)

        status = self.read(2)
        if from_bytes(status, 2) != 0:
            raise RuntimeError(f"status is {as_hex(status, 2)}")

    def power_read16(self, reg):
        logging.brom(f"PMIC read16({as_0x(reg, 2)})")
        self.echo(0xC6)
        self.echo(reg, 2)

        expected = 0
        self.check(self.read(2), to_bytes(expected, 2))  # recv ack
        self.check(self.read(2), to_bytes(expected, 2))  # PMIC read status

        result = from_bytes(self.read(2), 2)
        return result

    def power_write16(self, reg, val):
        logging.brom(f"PMIC write16({as_hex(reg)}, {as_hex(val)})")
        self.echo(0xC7)
        self.echo(reg, 2)
        self.echo(val, 2)

        expected = 0
        self.check(self.read(2), to_bytes(expected, 2))  # recv ack
        self.check(self.read(2), to_bytes(expected, 2))  # PMIC write status

    def get_me_id(self):
        logging.brom("Get ME ID")
        self.echo(0xE1)

        length = from_bytes(self.read(4), 4)
        if length == 0:
            raise RuntimeError("bad ME ID length")
        me_id = self.read(length)

        status = self.read(2)
        if from_bytes(status, 2) != 0:
            raise RuntimeError(f"status is {as_hex(status, 2)}")

        return me_id

    def get_preloader_version(self):
        logging.brom("Get PRELOADER version")
        self.write(0xFE)

        ver = from_bytes(self.read(1))
        if ver == 0xFE:
            logging.warning("Cannot get PRELOADER version in BROM mode")
        return ver

    def get_brom_version(self):
        logging.brom("Get BROM version")
        self.write(0xFF)

        ver = from_bytes(self.read(1))
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
