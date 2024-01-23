import logging

import sys


def getLogger(name=None, filename=None):
    formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
    logger = logging.getLogger(name)
    sh = logging.StreamHandler(sys.stdout)
    if filename:
        fh = logging.FileHandler(filename)
    else:
        fh = logging.FileHandler('bitty.log')
    fh.setFormatter(formatter)
    sh.setFormatter(formatter)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger
