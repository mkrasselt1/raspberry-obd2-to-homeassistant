""" Module for ELM327 based dongles """
from threading import Lock
from time import sleep
import math
import serial

class CanError(Exception):
    """ CAN communication failed """


class NoData(Exception):
    """ CAN did not return any data in time """
    
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
                # Input-Buffer komplett leeren (Alternative zu flushInput)
                while self._serial.in_waiting:
                    self._serial.read(self._serial.in_waiting)
                    sleep(0.05)
                self._serial.flushOutput()  # Output-Buffer leeren
                self._serial.timeout = 0.5  # Set timeout for reading
                
                # Stelle sicher, dass cmd ein Byte-Objekt ist
                if isinstance(cmd, str):
                    cmd = (cmd + '\r').encode()  # String zu Bytes und Zeilenende anhängen
                elif isinstance(cmd, bytes):
                    if not cmd.endswith(b'\r'):
                        cmd += b'\r'
                self._serial.write(cmd)
                ret = bytearray()
                while expect is not None:
                    if not self._serial.in_waiting:
                        sleep(0.1)
                        continue
                    data = self._serial.read(self._serial.in_waiting)

                    endidx = data.find(b'>')
                    if endidx >= 0:
                        ret.extend(data[:endidx])
                        break

                    ret.extend(data)

                if expect and expect not in ret:
                    print(f"[WARNING] Expected '{expect}', but got '{ret}'")

        except serial.SerialTimeoutException:
            print("[ERROR] Serial timeout occurred while communicating with dongle.")
            ret = b'TIMEOUT'

        print(f"[DEBUG] Response from dongle: {ret}")
        return ret.strip(b'\r\n')

    def send_at_cmd(self, cmd, expect=None):
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
            raise NoData(ret)

        if ret in self._ret_can_error:
            print("[ERROR] CAN error occurred.")
            raise CanError("Failed Command %s\n%s" % (cmd, ret))

        print(f"[DEBUG] Extended command response: {ret}")

        try:
            data = None
            data_len = 0
            last_idx = 0
            raw = str(ret, 'ascii').split('\r\n')

            for line in raw:
                if ((self._is_extended is False and len(line) != 19)
                        or (self._is_extended is True and len(line) != 27)):
                    raise ValueError

                offset = 8 if self._is_extended else 3

                frame_type = int(line[offset:offset+1], 16)

                if frame_type == 0:     # Single frame
                    print(f"%s single frame", line)
                    data_len = int(line[offset+1:offset+2], 16)
                    data = bytes.fromhex(line[offset+2:data_len*2+offset+2])
                    break

                elif frame_type == 1:   # First frame
                    print(f"%s first frame", line)
                    data_len = int(line[offset+1:offset+4], 16)
                    data = bytearray.fromhex(line[offset+4:])
                    last_idx = 0

                elif frame_type == 2:   # Consecutive frame
                    print(f"%s consecutive frame", line)
                    idx = int(line[offset+1:offset+2], 16)
                    if (last_idx + 1) % 0x10 != idx:
                        raise CanError("Bad frame order: last_idx(%d) idx(%d)" %
                                       (last_idx, idx))

                    frame_len = min(7, data_len - len(data))
                    data.extend(bytearray.fromhex(
                        line[offset+2:frame_len*2+offset+2]))
                    last_idx = idx

                    if data_len == len(data):
                        break

                else:                   # Unexpected frame
                    raise ValueError

            if not data or data_len == 0:
                raise NoData('NO DATA')

            if data_len != len(data):
                raise CanError("Data length mismatch %s: %d vs %d %s" %
                               (cmd, data_len, len(data), data.hex()))

        except ValueError:
            raise CanError("Failed Command %s\n%s" % (cmd, ret))

        return data

    def init_dongle(self):
        """ Send some initializing commands to the dongle. """
        print("[DEBUG] Initializing dongle with AT commands...")
        cmds = (('AT D', None),  # Set all settings to default
                ('AT Z', None), #'ELM327'),
                ('AT E0', None), #'OK'),
                ('AT L1', None), #'OK'),
                ('AT S0', None), #'OK'),
                ('AT H1', None), #'OK'),
                ('AT ST FF', None), #'OK'),
                ('AT FE', None), #'OK'))
                )

        for cmd, exp in cmds:
            print(f"[DEBUG] Sending initialization command: {cmd}")
            self.send_at_cmd(cmd, exp)
        print("[DEBUG] Dongle initialization complete.")

    def set_protocol(self, prot):
        """ Set the variant of CAN protocol """
        print(f"[DEBUG] Setting protocol: {prot}")
        if prot == 'CAN_11_500':
            self.send_at_cmd('AT SP 6', None) #'OK')
            self._is_extended = False
        elif prot == 'CAN_29_500':
            self.send_at_cmd('AT SP 7', None) #'OK')
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
            self.send_at_cmd('AT SH ' + can_id)
            self._current_canid = can_id

    def set_can_rx_mask(self, mask):
        """ Set the CAN id mask for receiving frames """
        print(f"[DEBUG] Setting CAN RX mask: {mask}")
        if isinstance(mask, bytes):
            mask = str(mask)
        elif isinstance(mask, int):
            mask = format(mask, '08X' if self._is_extended else '03X')

        if self._current_canmask != mask:
            self.send_at_cmd('AT CM ' + mask)
            self._current_canmask = mask

    def set_can_rx_filter(self, can_id):
        """ Set the CAN id filter for receiving frames """
        print(f"[DEBUG] Setting CAN RX filter: {can_id}")
        if isinstance(can_id, bytes):
            can_id = str(can_id)
        elif isinstance(can_id, int):
            can_id = format(can_id, '08X' if self._is_extended else '03X')

        if self._current_canfilter != can_id:
            self.send_at_cmd('AT CF ' + can_id)
            self._current_canfilter = can_id

    def get_obd_voltage(self):
        """ Get the voltage at the OBD port """
        print("[DEBUG] Getting OBD voltage...")
        ret = self.send_at_cmd('AT RV ', None)
        voltage = round(float(ret[:-1]), 2)
        print(f"[DEBUG] OBD voltage: {voltage} V")
        return voltage

    # def calibrate_obd_voltage(self, real_voltage):
    #     """ Calibrate the voltage sensor using an
    #         externally measured voltage reading """
    #     print(f"[DEBUG] Calibrating OBD voltage to: {real_voltage} V")
    #     self.send_at_cmd('AT CV %04.0f' % (real_voltage * 100))
