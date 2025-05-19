""" Module for the Hyundai Ioniq Electric 28kWh """
from car import Car
from isotp_decoder import IsoTpDecoder
from elm327 import NoData, CanError

b2101 = bytes.fromhex('2101')
b2102 = bytes.fromhex('2102')
b2103 = bytes.fromhex('2103')
b2104 = bytes.fromhex('2104')
b2105 = bytes.fromhex('2105')
b2180 = bytes.fromhex('2180')
b22b002 = bytes.fromhex('22b002')

Fields = (
    {'cmd': b2101, 'canrx': 0x7ec, 'cantx': 0x7e4,
     'fields': (
         {'padding': 6},
         {'name': 'SOC_BMS', 'width': 1, 'scale': .5, "units": "%"},
         {'name': 'availableChargePower', 'width': 2, 'scale': .01,'units': "kW"},
         {'name': 'availableDischargePower', 'width': 2, 'scale': .01,'units': "kW"},
         {'name': 'charging_bits', 'width': 1},
         {'name': 'dcBatteryCurrent', 'width': 2, 'signed': True, 'scale': .1, 'units': "A"},
         {'name': 'dcBatteryVoltage', 'width': 2, 'scale': .1, 'units': "V"},
         {'name': 'batteryMaxTemperature', 'width': 1, 'signed': True, 'units': "°C"},
         {'name': 'batteryMinTemperature', 'width': 1, 'signed': True, 'units': "°C"},
         {'name': 'cellTemp%02d', 'idx': 1, 'cnt': 5, 'width': 1, 'signed': True, 'units': "°C"},
         {'padding': 1},
         {'name': 'batteryInletTemperature', 'width': 1, 'signed': True, 'units': "°C"},
         {'padding': 4},
         {'name': 'fanStatus', 'width': 1},
         {'name': 'fanFeedback', 'width': 1, 'scale': 100, 'units': "RPM"},
         {'name': 'auxBatteryVoltage', 'width': 1, 'scale': .1, 'units': "V"},
         {'name': 'cumulativeChargeCurrent', 'width': 4, 'scale': .1, 'units': "kWh"},
         {'name': 'cumulativeDischargeCurrent', 'width': 4, 'scale': .1, 'units': "kWh"},
         {'name': 'cumulativeEnergyCharged', 'width': 4, 'scale': .1, 'units': "kWh"},
         {'name': 'cumulativeEnergyDischarged', 'width': 4, 'scale': .1, 'units': "kWh"},
         {'name': 'operatingTime', 'width': 4, 'units':'s'},  # seconds
         {'padding': 3},
         {'name': 'driveMotorSpeed', 'width': 2, 'signed': True, 'offset': 0, 'scale': 1, 'units': "RPM"},
         {'padding': 4},
         # Len: 56
     )
     },
    {'cmd': b2102, 'canrx': 0x7ec, 'cantx': 0x7e4,
     'fields': (
         {'padding': 6},
         {'name': 'cellVoltage%02d', 'idx': 1, 'cnt': 32, 'width': 1, 'scale': .02, 'units': "V"},
         # Len: 38
     )
     },
    {'cmd': b2103, 'canrx': 0x7ec, 'cantx': 0x7e4,
     'fields': (
         {'padding': 6},
         {'name': 'cellVoltage%02d', 'idx': 33, 'cnt': 32, 'width': 1, 'scale': .02, 'units': "V"},
         # Len: 38
     )
     },
    {'cmd': b2104, 'canrx': 0x7ec, 'cantx': 0x7e4,
     'fields': (
         {'padding': 6},
         {'name': 'cellVoltage%02d', 'idx': 65, 'cnt': 32, 'width': 1, 'scale': .02, 'units': "V"},
         # Len: 38
     )
     },
    {'cmd': b2105, 'canrx': 0x7ec, 'cantx': 0x7e4,
     'fields': (
         {'padding': 11},
         {'name': 'cellTemp%02d', 'idx': 6, 'cnt': 7, 'width': 1, 'signed': True, 'units': "°C"},
         {'padding': 9},
         {'name': 'soh', 'width': 2, 'scale': .1, 'units': "%"},
         {'padding': 4},
         {'name': 'SOC_DISPLAY', 'width': 1, 'scale': .5, "units": "%"},
         {'padding': 11},
         # Len: 45
     )
     },
    {'cmd': b2180, 'canrx': 0x7ee, 'cantx': 0x7e6,
     'fields': (
         {'padding': 14},
         {'name': 'externalTemperature', 'width': 1, 'scale': .5, 'offset': -40, 'units': "°C"},
         {'padding': 10},
         # Len: 25
     )
     },
    {'cmd': b22b002, 'canrx': 0x7ce, 'cantx': 0x7c6, 'optional': True,
     'fields': (
         {'padding': 9},
         {'name': 'odo', 'width': 3, 'units': "km"},
         {'padding': 3},
         # Len: 15
     )
     },
    {'computed': True,
     'fields': (
         {'name': 'dcBatteryPower',
          'lambda': lambda d: d['dcBatteryCurrent'] * d['dcBatteryVoltage'] / 1000.0},
         {'name': 'charging',
          'lambda': lambda d: int(d['charging_bits'] & 0x80 != 0)},
         {'name': 'normalChargePort',
          'lambda': lambda d: int(d['charging_bits'] & 0x20 != 0)},
         {'name': 'rapidChargePort',
          'lambda': lambda d: int(d['charging_bits'] & 0x40 != 0)},
     )
     },
)


class IoniqBev(Car):
    """ Class for Ioniq Electric """

    def __init__(self, config, dongle, gps):
        super().__init__(config, dongle, gps)
        self._dongle.set_protocol('CAN_11_500')
        self._isotp = IsoTpDecoder(self._dongle, self.get_fields())

    def get_fields(self):
        """ Return the fields for the Ioniq Electric """
        return Fields

    def read_dongle(self, data):
        """ Fetch data from CAN-bus and decode it.
            "data" needs to be a dictionary that will
            be modified with decoded data """
        data.update(self._isotp.get_data())

