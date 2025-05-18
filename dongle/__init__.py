""" Helper functions for dongle modules """
from importlib import import_module


class CanError(Exception):
    """ CAN communication failed """


class NoData(Exception):
    """ CAN did not return any data in time """


def load():
    """ import a specific OBD2 module """
    return getattr(import_module("dongle.elm327"),'Elm327')
