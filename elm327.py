""" Module for ELM327 based dongles """
from threading import Lock
from time import sleep
import math
import serial


class Elm327:
    """ Implementation for ELM327 """

    def __init__(self, config):
        print(f"[DEBUG] Initializing ELM327 dongle on port {config['port']} with baudrate {config['baudrate']}...")
        self._serial_lock = Lock()
        self._serial = serial.Serial(config['port'],
                                     baudrate=config['baudrate'],
                                     timeout=1)
        self._config = config
        self._current_canid = 0
        self._current_canfilter = 0
        self._current_canmask = 0
        self._is_extended = False
        self._ret_no_data = (b'NO DATA', b'DATA ERROR', b'ACT ALERT')
        self._ret_can_error = (b'BUFFER FULL', b'BUS BUSY', b'BUS ERROR', b'CAN ERROR',
                               b'ERR', b'FB ERROR', b'LP ALERT', b'LV RESET', b'STOPPED',
                               b'UNABLE TO CONNECT')
        self.init_dongle()
        print("[DEBUG] ELM327 dongle initialized successfully.")

    def talk_to_dongle(self, cmd, expect=None):
        """ Send command to dongle and return the response as string. """
        print(f"[DEBUG] Sending command to dongle: {cmd}")
        try:
            with self._serial_lock:
                while self._serial.in_waiting:   # Clear the input buffer
                    self._serial.read(self._serial.in_waiting)
                    sleep(0.1)

                self._serial.write(bytes(cmd + '\r\n', 'ascii'))
                ret = bytearray()
                while True:
                    if not self._serial.in_waiting:
                        sleep(0.1)
                        continue
                    data = self._serial.read(self._serial.in_waiting)

                    endidx = data.find(b'>')
                    if endidx >= 0:
                        ret.extend(data[:endidx])
                        break

                    ret.extend(data)

                if expect:
                    expect = bytes(expect, 'ascii')
                    if expect not in ret:
                        print(f"[ERROR] Expected '{expect}', but got '{ret}'")
                        raise Exception(f"Expected {expect}, got {ret}")

        except serial.SerialTimeoutException:
            print("[ERROR] Serial timeout occurred while communicating with dongle.")
            ret = b'TIMEOUT'

        print(f"[DEBUG] Response from dongle: {ret}")
        return ret.strip(b'\r\n')

    def send_at_cmd(self, cmd, expect='OK'):
        """ Send AT command to dongle and return response. """
        print(f"[DEBUG] Sending AT command: {cmd}")
        ret = self.talk_to_dongle(cmd, expect)
        print(f"[DEBUG] AT command response: {ret}")
        return ret.split(b"\r\n")[-1]

    def send_command(self, cmd):
        """ Convert bytearray "cmd" to string,
            send to dongle and parse the response. """
        print(f"[DEBUG] Sending command: {cmd.hex()}")
        cmd = cmd.hex()
        ret = self.talk_to_dongle(cmd)

        if ret in self._ret_no_data:
            print("[WARNING] No data received from dongle.")
            raise Exception("No Data")

        if ret in self._ret_can_error:
            print("[ERROR] CAN error occurred.")
            raise Exception("CAN Error")

        print(f"[DEBUG] Command response: {ret}")
        return ret

    def send_command_ex(self, cmd, cantx, canrx):
        """ Convert bytearray "cmd" to string,
            send to dongle and parse the response.
            Also handles filters and masks. """
        print(f"[DEBUG] Sending extended command: {cmd.hex()}, CAN TX: {cantx}, CAN RX: {canrx}")
        cmd = cmd.hex()
        self.set_can_id(cantx)
        self.set_can_rx_filter(canrx)
        self.set_can_rx_mask(0x1fffffff if self._is_extended else 0x7ff)

        ret = self.talk_to_dongle(cmd)

        if ret in self._ret_no_data:
            print("[WARNING] No data received from dongle.")
            raise Exception("No Data")

        if ret in self._ret_can_error:
            print("[ERROR] CAN error occurred.")
            raise Exception("CAN Error")

        print(f"[DEBUG] Extended command response: {ret}")
        return ret

    def init_dongle(self):
        """ Send some initializing commands to the dongle. """
        print("[DEBUG] Initializing dongle with AT commands...")
        cmds = (('AT Z', 'ELM327'),
                ('AT E0', 'OK'),
                ('AT L1', 'OK'),
                ('AT S0', 'OK'),
                ('AT H1', 'OK'),
                ('AT ST FF', 'OK'),
                ('AT FE', 'OK'))

        for cmd, exp in cmds:
            print(f"[DEBUG] Sending initialization command: {cmd}")
            self.send_at_cmd(cmd, exp)
        print("[DEBUG] Dongle initialization complete.")

    def set_protocol(self, prot):
        """ Set the variant of CAN protocol """
        print(f"[DEBUG] Setting protocol: {prot}")
        if prot == 'CAN_11_500':
            self.send_at_cmd('ATSP6', 'OK')
            self._is_extended = False
        elif prot == 'CAN_29_500':
            self.send_at_cmd('ATSP7', 'OK')
            self._is_extended = True
        else:
            print(f"[ERROR] Unsupported protocol: {prot}")
            raise ValueError(f"Unsupported protocol {prot}")

    def set_can_id(self, can_id):
        """ Set CAN id to use for sent frames """
        print(f"[DEBUG] Setting CAN ID: {can_id}")
        if isinstance(can_id, bytes):
            can_id = str(can_id)
        elif isinstance(can_id, int):
            can_id = format(can_id, '08X' if self._is_extended else '03X')

        if self._current_canid != can_id:
            self.send_at_cmd('ATSH' + can_id)
            self._current_canid = can_id

    def set_can_rx_mask(self, mask):
        """ Set the CAN id mask for receiving frames """
        print(f"[DEBUG] Setting CAN RX mask: {mask}")
        if isinstance(mask, bytes):
            mask = str(mask)
        elif isinstance(mask, int):
            mask = format(mask, '08X' if self._is_extended else '03X')

        if self._current_canmask != mask:
            self.send_at_cmd('ATCM' + mask)
            self._current_canmask = mask

    def set_can_rx_filter(self, can_id):
        """ Set the CAN id filter for receiving frames """
        print(f"[DEBUG] Setting CAN RX filter: {can_id}")
        if isinstance(can_id, bytes):
            can_id = str(can_id)
        elif isinstance(can_id, int):
            can_id = format(can_id, '08X' if self._is_extended else '03X')

        if self._current_canfilter != can_id:
            self.send_at_cmd('ATCF' + can_id)
            self._current_canfilter = can_id

    def get_obd_voltage(self):
        """ Get the voltage at the OBD port """
        print("[DEBUG] Getting OBD voltage...")
        ret = self.send_at_cmd('ATRV', None)
        voltage = round(float(ret[:-1]), 2)
        print(f"[DEBUG] OBD voltage: {voltage} V")
        return voltage

    def calibrate_obd_voltage(self, real_voltage):
        """ Calibrate the voltage sensor using an
            externally measured voltage reading """
        print(f"[DEBUG] Calibrating OBD voltage to: {real_voltage} V")
        self.send_at_cmd('ATCV%04.0f' % (real_voltage * 100))
