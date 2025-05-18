""" Helper functions for car modules """
from importlib import import_module

def load(car_type):
    """ Import a specific car module """
    return getattr(import_module("car.ioniq_bev"),
                   'IoniqBev')
