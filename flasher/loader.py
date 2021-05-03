#!/usr/bin/env python3

"""
Requrements:
    pip3 install gpiozero
"""

import sys
import time
import logging
import argparse
from typing import List
from contextlib import contextmanager

from gpiozero import DigitalInputDevice, DigitalOutputDevice
from tqdm import tqdm


# Start addresses on DUP (Increased buffer size improves performance)
ADDR_BUF0 =                  0x0000  # Buffer (512 bytes)
ADDR_DMA_DESC_0 =             0x0200  # DMA descriptors (8 bytes)
ADDR_DMA_DESC_1  =           (ADDR_DMA_DESC_0 + 8)

# DMA channels used on DUP
CH_DBG_TO_BUF0 =             0x01   # Channel 0
CH_BUF0_TO_FLASH =           0x02   # Channel 1


class FlashError(Exception):
    """Base exception"""


class DebugComand:
    """Debug commands"""
    CMD_CHIP_ERASE =   0x10
    CMD_WR_CONFIG  =             0x19
    CMD_RD_CONFIG  =             0x24
    CMD_READ_STATUS =            0x30
    CMD_RESUME =                 0x4C
    CMD_DEBUG_INSTR_1B =          (0x54|1)
    CMD_DEBUG_INSTR_2B =         (0x54|2)
    CMD_DEBUG_INSTR_3B =         (0x54|3)
    CMD_BURST_WRITE =            0x80
    CMD_GET_CHIP_ID =            0x68


class DebugStatus:
    """Debug status bitmasks"""
    STATUS_CHIP_ERASE_BUSY_BM =   0x80  # New debug interface
    STATUS_PCON_IDLE_BM =         0x40
    STATUS_CPU_HALTED_BM =        0x20
    STATUS_PM_ACTIVE_BM =         0x10
    STATUS_HALT_STATUS_BM =       0x08
    STATUS_DEBUG_LOCKED_BM =      0x04
    STATUS_OSC_STABLE_BM =        0x02
    STATUS_STACK_OVERFLOW_BM =    0x01


class DupRegisters:
    """DUP registers (XDATA space address)"""
    DUP_DBGDATA =                 0x6260  # Debug interface data buffer
    DUP_FCTL =                    0x6270  # Flash controller
    DUP_FADDRL =                  0x6271  # Flash controller addr
    DUP_FADDRH =                  0x6272  # Flash controller addr
    DUP_FWDATA =                  0x6273  # Clash controller data buffer
    DUP_CLKCONSTA =               0x709E  # Sys clock status
    DUP_CLKCONCMD =               0x70C6  # Sys clock configuration
    DUP_MEMCTR =                  0x70C7  # Flash bank xdata mapping
    DUP_DMA1CFGL =                0x70D2  # Low byte, DMA config ch. 1
    DUP_DMA1CFGH =                0x70D3  # Hi byte , DMA config ch. 1
    DUP_DMA0CFGL =                0x70D4  # Low byte, DMA config ch. 0
    DUP_DMA0CFGH =                0x70D5  # Low byte, DMA config ch. 0
    DUP_DMAARM =                  0x70D6  # DMA arming register


class Flash:

    def __init__(self):
        self.pin_dd = 20
        self.pin_dc = 16
        self.pin_rst = 19

        self.tw = 0.0001  # Time wait (sec)

        # self.dev_dd = None
        self.dev_dc = None

        self.init()

        # DUP DMA descriptor
        # Debug Interface -> Buffer
        self.dma_desc_0 = [
            self._hibyte(DupRegisters.DUP_DBGDATA),  # src[15:8]
            self._lobyte(DupRegisters.DUP_DBGDATA),  # src[7:0]
            self._hibyte(ADDR_BUF0),  # dest[15:8]
            self._lobyte(ADDR_BUF0),  # dest[7:0]
            0,  # len[12:8] - filled in later
            0,  # len[7:0]
            31,  # trigger: DBG_BW
            0x11  # increment destination
        ]

        # DUP DMA descriptor
        # Buffer -> Flash controller
        self.dma_desc_1 = [
            self._hibyte(ADDR_BUF0),  # src[15:8]
            self._lobyte(ADDR_BUF0),  # src[7:0]
            self._hibyte(DupRegisters.DUP_FWDATA),  # dest[15:8]
            self._lobyte(DupRegisters.DUP_FWDATA),  # dest[7:0]
            0,  # len[12:8] - filled in later
            0,  # len[7:0]
            18,  # trigger: DBG_BW
            0x42  # increment destination
        ]

    def init(self):
        # self.dev_dd = DigitalInputDevice(pin=self.pin_dd, pull_up=True)
        self.dev_dc = DigitalOutputDevice(pin=self.pin_dc)
    
    def debug_init(self):
        """
        Resets the DUP into debug mode. Function assumes that
        the programmer I/O has already been configured using e.g.
        """
        dev_dc = self.dev_dc
        with DigitalOutputDevice(pin=self.pin_rst) as dev_rst:
            with DigitalOutputDevice(pin=self.pin_dd) as dev_dd:
                # Send two flanks on DC while keeping RESET_N low
                # All low (incl. RESET_N)
                dev_rst.off()
                dev_dd.off()
                dev_dc.off()
                self._wait()

                dev_dc.on()
                self._wait()
                dev_dc.off()
                self._wait()
                dev_dc.on()
                self._wait()
                dev_dc.off()
                self._wait()

                dev_rst.on()
                self._wait()
    
    def run_dup(self):
        # Send two flanks on DC while keeping RESET_N low
        # All low (incl. RESET_N)
        dev_dc = self.dev_dc
        with DigitalOutputDevice(pin=self.pin_rst) as dev_rst:
            with DigitalOutputDevice(pin=self.pin_dd) as dev_dd:
                dev_rst.off()
                dev_dd.off()
                dev_dc.off()
                self._wait()

                dev_rst.on()
                self._wait()

    def read_chip_id(self) -> int:
        """
        Reads the chip ID over the debug interface using the 
        GET_CHIP_ID command.
        
        Return
            Returns the chip id returned by the DUP
        """
        _id = None
        
        # Send command
        self._write_debug_byte(DebugComand.CMD_GET_CHIP_ID)
        self._wait()
        self.wait_dup_ready()
        # Read ID and revision
        _id = self._read_debug_byte()
        self._read_debug_byte()  # Revision (discard)
        return _id
    
    def wait_dup_ready(self):
        """
        Function waits for DUP to indicate that it is ready. The DUP will
        pulls DD line low when it is ready. Requires DD to be input when
        function is called.

        Return:
            Returns 0 if function timed out waiting for DD line to go low
            Returns 1 when DUP has indicated it is ready.
        """
        count = 0

        dev_dd = DigitalOutputDevice(pin=self.pin_dd)
        dev_dd.on()
        dev_dd.close()
        self._wait()

        dev_dd = DigitalInputDevice(pin=self.pin_dd)

        while ((dev_dd.value == 1) and count < 16):
            # Clock out 8 bits before checking if DD is low again
            for _ in range(8):
                self.dev_dc.on()
                self._wait()
                self.dev_dc.off()
                self._wait()
            count += 1
        
        dev_dd.close()

        if count == 16:
            raise FlashError("Timeout for wait dup read")
    
    def debug_command(self, cmd: int, cmd_bytes: List[int]):
        """
        Issues a command on the debug interface. Only commands that return
        one output byte are supported.

        Args:
            cmd - Command byte
            cmd_bytes -  Pointer to the array of data bytes following the
                command byte [0-3]
        
        Return
            Data returned by command, or None if error
        """
        data = None

        self._is_byte(cmd)
        self._is_byte_list(cmd_bytes)
        
        # Send command
        self._write_debug_byte(cmd)
        # Send bytes
        for value in cmd_bytes:
            self._write_debug_byte(value)
        # Wait for data to be ready
        self.wait_dup_ready()

        # Very strange. Skip value
        # for _ in range(len(cmd_bytes)):
        #     self._read_debug_byte()

        # Read data
        data = self._read_debug_byte()

        return data
    
    def chip_erase(self):
        """
        Issues a CHIP_ERASE command on the debug interface and waits for it
        to complete.
        """
        status = 0
        self.debug_command(DebugComand.CMD_CHIP_ERASE, [])
        while (status & DebugStatus.STATUS_CHIP_ERASE_BUSY_BM):
            status = self.debug_command(DebugComand.CMD_READ_STATUS, [])
    
    def burst_write_block(self, src: List[int]):
        """
        Sends a block of data over the debug interface using the
        BURST_WRITE command.

        Args:
            src - Pointer to the array of input bytes
        """
        self._is_byte_list(src)

        self._write_debug_byte(
            DebugComand.CMD_BURST_WRITE | self._hibyte(len(src))
        )
        self._write_debug_byte(self._lobyte(len(src)))

        for data in src:
            self._write_debug_byte(data)
        
        self.wait_dup_ready()
        self._read_debug_byte()
    
    def write_xdata_memory_block(self, address: int, data: List[int]):
        """Writes a block of data to the DUP's XDATA space.

        Args:
            address - XDATA start address
            data - list of bytes to write
        """
        # MOV DPTR, address
        instr = [0x90, self._hibyte(address), self._lobyte(address)]
        self.debug_command(DebugComand.CMD_DEBUG_INSTR_3B, instr)
        
        for item in data:
            # MOV A, values[i]
            instr = [0x74, item]
            self.debug_command(DebugComand.CMD_DEBUG_INSTR_2B, instr)

            # MOV @DPTR, A
            instr = [0xF0]
            self.debug_command(DebugComand.CMD_DEBUG_INSTR_1B, instr)

            # INC DPTR
            instr = [0xA3]
            self.debug_command(DebugComand.CMD_DEBUG_INSTR_1B, instr)
    
    def write_xdata_memory(self, address: int, data: int):
        """Writes a byte to a specific address in the DUP's XDATA space.

        Args:
            address - XDATA address
            data - Value to write
        """
        # MOV DPTR, address
        self.debug_command(
            DebugComand.CMD_DEBUG_INSTR_3B,
            [0x90, self._hibyte(address), self._lobyte(address)]
        )
        # MOV A, data
        self.debug_command(DebugComand.CMD_DEBUG_INSTR_2B, [0x74, data])
        # MOV @DPTR, A
        self.debug_command(DebugComand.CMD_DEBUG_INSTR_1B, [0xF0])
    
    def read_xdata_memory(self, address: int) -> int:
        """Read a byte from a specific address in the DUP's XDATA space.

        Args:
            address - XDATA address
        
        Return:
            Value read from XDATA
        """
        # MOV DPTR, address
        self.debug_command(
            DebugComand.CMD_DEBUG_INSTR_3B,
            [0x90, self._hibyte(address), self._lobyte(address)]
        )
        # MOVX A, @DPTR
        return self.debug_command(DebugComand.CMD_DEBUG_INSTR_1B, [0xE0])
    
    def read_flash_memory_block(
        self, bank: int, address: int, num_bytes: int
    ) -> List[int]:
        """Reads 1-32767 bytes from DUP's flash to a given buffer on the
        programmer.

        Args:
            bank - Flash bank to read from [0-7]
            address - Flash memory start address [0x0000 - 0x7FFF]
            num_bytes - Count byte for read

        Return:
            Buffer with data
        """
        result = []
        xdata_addr = 0x8000 + flash_addr

        # 1. Map flash memory bank to XDATA address 0x8000-0xFFFF
        self.write_xdata_memory(DupRegisters.DUP_MEMCTR, bank)

        # 2. Move data pointer to XDATA address (MOV DPTR, xdata_addr)
        debug_command(
            DebugComand.CMD_DEBUG_INSTR_3B,
            [0x90, self._hibyte(xdata_addr), self._lobyte(xdata_addr)]
        )

        for i in range(num_bytes):
            # 3. Move value pointed to by DPTR to accumulator (MOVX A, @DPTR)
            result.append(
                self.debug_command(DebugComand.CMD_DEBUG_INSTR_1B, [0xE0])
            )
            # 4. Increment data pointer (INC DPTR)
            self.debug_command(DebugComand.CMD_DEBUG_INSTR_1B, [0xA3])

        return result
    
    def write_flash_memory_block(
        self, src: List[int], start_addr: int, num_bytes: int
    ):
        """Writes 4-2048 bytes to DUP's flash memory. Parameter \c num_bytes
        must be a multiple of 4.

        Args:
            src - source buffer (in XDATA space)
            start_addr - FLASH memory start address [0x0000 - 0x7FFF]
            num_bytes - Number of bytes to transfer [4-1024]
        """
        # 1. Write the 2 DMA descriptors to RAM
        self.write_xdata_memory_block(ADDR_DMA_DESC_0, self.dma_desc_0)
        self.write_xdata_memory_block(ADDR_DMA_DESC_1, self.dma_desc_1)

        # 2. Update LEN value in DUP's DMA descriptors
        len_value = [self._hibyte(num_bytes), self._lobyte(num_bytes)]
        self.write_xdata_memory_block(ADDR_DMA_DESC_0 + 4, len_value)  # LEN, DBG => ram
        self.write_xdata_memory_block(ADDR_DMA_DESC_1 + 4, len_value)  # LEN, ram => flash

        # 3. Set DMA controller pointer to the DMA descriptors
        self.write_xdata_memory(
            DupRegisters.DUP_DMA0CFGH, self._hibyte(ADDR_DMA_DESC_0))
        self.write_xdata_memory(
            DupRegisters.DUP_DMA0CFGL, self._lobyte(ADDR_DMA_DESC_0))
        self.write_xdata_memory(
            DupRegisters.DUP_DMA1CFGH, self._hibyte(ADDR_DMA_DESC_1))
        self.write_xdata_memory(
            DupRegisters.DUP_DMA1CFGL, self._lobyte(ADDR_DMA_DESC_1))
        
        # 4. Set Flash controller start address (wants 16MSb of 18 bit address)
        self.write_xdata_memory(
            DupRegisters.DUP_FADDRH, self._hibyte(start_addr))
        self.write_xdata_memory(
            DupRegisters.DUP_FADDRL, self._lobyte(start_addr))
        
        # 5. Arm DBG=>buffer DMA channel and start burst write
        self.write_xdata_memory(DupRegisters.DUP_DMAARM, CH_DBG_TO_BUF0)
        self.burst_write_block(src)

        # 6. Start programming: buffer to flash
        self.write_xdata_memory(DupRegisters.DUP_DMAARM, CH_BUF0_TO_FLASH)
        self.write_xdata_memory(DupRegisters.DUP_FCTL, 0x0A)

        # 7. Wait until flash controller is done
        while (self.read_xdata_memory(DupRegisters.DUP_FCTL) & 0x80):
            pass

    def _write_debug_byte(self, data: int):
        """
        Writes a byte on the debug interface. Requires DD to be
        output when function is called.

        Args:
            data - Byte to write
        """
        if data > 255:
            raise ValueError("The data len is not one byte")
        
        with DigitalOutputDevice(pin=self.pin_dd) as dev_dd:
            for bit in self._get_bit(data):
                self.dev_dc.on()  # Set clock high and put data on DD line
                if bit:
                    dev_dd.on()
                else:
                    dev_dd.off()
                self._wait()
                self.dev_dc.off()  # Set clock low (DUP capture flank)
                self._wait()
    
    def _read_debug_byte(self) -> int:
        """
        Reads a byte from the debug interface. Requires DD to be
        input when function is called.
        
        Return
            Returns the byte read.
        """
        data = 0

        dev_dd = DigitalInputDevice(pin=self.pin_dd)

        for _ in range(8):
            self.dev_dc.on()

            data = data << 1
            if dev_dd.value == 1:
                data |= 0x01

            self.dev_dc.off()
            self._wait()
        
        dev_dd.close()

        return data
    
    def _get_bit(self, data: int):
        """
        Get all bit. (MSB-first)

        Args:
            data - one byte

        Return
            Iterator
        """
        bits = []
        for idx in range(8):
            bits.append((data >> idx) & 1)
        
        # MSB
        bits.reverse()
        for bit in bits:
            yield bit
    
    def _hibyte(self, data):
        return (data & 0xFF00) >> 8
    
    def _lobyte(self, data):
        return (data & 0xFF)
    
    def _is_byte(self, data: int):
        """Check value does't more that 255"""
        if data > 255:
            raise ValueError("More 255")
    
    def _is_byte_list(self, data: List[int]):
        for x in data:
            self._is_byte(x)
    
    def _wait(self):
        time.sleep(self.tw)


def read_file_chunk(path: str, ch_size=512) -> List[int]:
    """Read a file piece by piece. Generator
    """
    with open(path, "rb") as f:
        while True:
            data = f.read(ch_size)
            if not data:
                break
            data = list(data)
            # align to chink size
            if len(data) % ch_size:
                align_value = ch_size - (len(data) % ch_size)
                print("Len data:", len(data), "Align:", align_value)
                data = data + [0] * align_value
            yield data


def get_cnt_chunk(path: str, ch_size=512) -> int:
    """Return count chunk for size of file"""
    with open(path, "rb") as f:
        data = f.read()
        size = len(data)
    return round(size / ch_size)


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--file", type=str, required=True, help="Path to firmware")
    parser.add_argument(
        "--verify", default=False, action="store_true",
        help="Verify firmware after write"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = arguments()

    print("Init")

    flash = Flash()

    flash.debug_init()

    chip_id = flash.read_chip_id()
    if chip_id is None:
        print("Couldn't to read chip id")
        sys.exit(1)
    print("Chip id:", chip_id)

    print("Erase chip")
    flash.chip_erase()

    print("Flash")
    # Switch DUP to external crystal osc. (XOSC) and wait for it to be stable.
    # This is recommended if XOSC is available during programming. If
    # XOSC is not available, comment out these two lines.
    flash.write_xdata_memory(DupRegisters.DUP_CLKCONCMD, 0x80)
    while (flash.read_xdata_memory(DupRegisters.DUP_CLKCONSTA) != 0x80):
        pass

    # Enable DMA (Disable DMA_PAUSE bit in debug configuration)
    flash.debug_command(DebugComand.CMD_WR_CONFIG, [0x22])

    # Program data (start address must be word aligned [32 bit])
    addr = 0x0000
    bar = tqdm(total=get_cnt_chunk(args.file, ch_size=512))
    bar.set_description("Write firmware")
    for item in read_file_chunk(args.file, ch_size=512):
        flash.write_flash_memory_block(item, addr, len(item))
        if args.verify:
            bank = int(addr / (512 * 16))
            offset = int(addr % (512 * 16)) * 4
            read_data = flash.read_flash_memory_block(bank, offset, 512)
            if read_data != item:
                print("Error write block")
                flash.chip_erase()
                sys.exit(1)
        addr += 128
        bar.update()

    print("Done")
