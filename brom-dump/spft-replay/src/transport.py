# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

import array
import logging
import time
from abc import ABC, abstractmethod

import usb
import usb.backend.libusb1

from src.common import as_hex, from_bytes, report_write_progress, to_bytes


class Transport(ABC):
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def read(self, size=1, timeout=-1):
        pass

    @abstractmethod
    def write(self, data, size=1, timeout=-1):
        pass

    def check(self, test, gold):
        if test != gold:
            test = as_hex(test)
            gold = as_hex(gold)
            raise RuntimeError(f"Unexpected output, expected {gold} got {test}")

    def echo(self, words, size=1):
        self.write(words, size)
        self.check(from_bytes(self.read(size), size), words)


class UsbTransport(Transport):
    BROM_VID = 0x0E8D
    BROM_PID = 0x0003
    BROM_BAUDRATE = 115200
    BROM_TIMEOUT = 3 * 1000  # ms

    def __init__(self):
        self.backend = None
        self.device = None
        self.ep_in = None
        self.ep_out = None
        self.rxbuffer = array.array("B")

    def start(self):
        logging.info("Init backend")
        self.backend = usb.backend.libusb1.get_backend()
        if not self.backend:
            raise RuntimeError("Could not initialize the libusb1 backend")

        logging.info(
            f"Waiting for device in BROM mode "
            f"({as_hex(UsbTransport.BROM_VID, 2)}:{as_hex(UsbTransport.BROM_PID, 2)})"
        )
        while not self.device:
            self.device = usb.core.find(
                idVendor=UsbTransport.BROM_VID,
                idProduct=UsbTransport.BROM_PID,
                backend=self.backend,
            )
            if self.device:
                break
            time.sleep(0.25)
        logging.info("Found device")

        try:
            if self.device.is_kernel_driver_active(0):
                self.device.detach_kernel_driver(0)
            if self.device.is_kernel_driver_active(1):
                self.device.detach_kernel_driver(1)
        except:
            raise RuntimeError("USB: Cannot detach kernel driver")

        try:
            self.configuration = self.device.get_active_configuration()
        except:
            raise RuntimeError("USB: Cannot request configuration")

        try:
            self.device.set_configuration(1)
            usb.util.claim_interface(self.device, 0)
            usb.util.claim_interface(self.device, 1)
        except:
            raise RuntimeError("USB: Cannot claim interface")

        try:
            cdc_if = usb.util.find_descriptor(
                self.device.get_active_configuration(), bInterfaceClass=0xA
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
            raise RuntimeError("USB: Cannot configure endpoints")

        try:
            self.device.ctrl_transfer(
                0x21,
                0x20,
                0,
                0,
                array.array(
                    "B", to_bytes(UsbTransport.BROM_BAUDRATE, 4, "<") + b"\x00\x00\x08"
                ),
            )
        except:
            raise RuntimeError("USB: Cannot set baudrate")

        logging.info(
            "USB transport has successfully started! Waiting for further commands..."
        )

    def stop(self):
        self.rxbuffer = array.array("B")

        try:
            usb.util.release_interface(self.device, 0)
            usb.util.release_interface(self.device, 1)
        except Exception:
            logging.debug("USB: Could not release interfaces")

        try:
            self.device.reset()
        except Exception:
            logging.debug("USB: Could not reset device")

        for i in range(0, 2):
            try:
                self.device.attach_kernel_driver(i)
            except Exception:
                logging.debug(f"USB: Could not reattach kernel driver on interface {i}")

        try:
            usb.util.dispose_resources(self.device)
        except Exception:
            logging.debug("USB: Could not dispose resources")

        self.device = None
        time.sleep(1)

        logging.info("USB transport has stopped!")

    def read(self, size=1, timeout=-1):
        timeout = timeout if timeout > 0 else UsbTransport.BROM_TIMEOUT

        while len(self.rxbuffer) < size:
            try:
                self.rxbuffer.extend(
                    self.ep_in.read(self.ep_in.wMaxPacketSize, timeout)
                )
            except usb.core.USBError as e:
                if e.errno == 110:
                    self.device.reset()
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

    def write(self, data, size=1, timeout=-1):
        timeout = timeout if timeout > 0 else UsbTransport.BROM_TIMEOUT

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
            self.ep_out.write(data[off_start:off_end], timeout)
            report_write_progress(off_start, off_end, data_sz)

            off_start += pkt_sz
