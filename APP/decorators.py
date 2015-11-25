"""
    A bunch of function decorators for various purposes
"""
__author__ = 'austin'

from threading import Thread
import multiprocessing

FILE_TAG = __name__

def async(f):
    """
        Do in the background
        This is used for sending emails, when we want to split from the main API serving thread
    """
    def wrapper(*args, **kwargs):
        thr = Thread(target=f, args=args, kwargs=kwargs)
        thr.start()
    return wrapper


def multiprocess(f):
    def wrapper(*args, **kwargs):
        p = multiprocessing.Process(target=f, args=args, kwargs=kwargs)
        p.start()
    return wrapper


import functools
def deprecated(in_version, reason=None):
    """
        Mostly for visual use when programmin but will log a blurb when one of these functions are called
    :param in_version:
    :type in_version: str
    :param reason:
    :type reason: str
    :return:
    """
    from APP.utility import log
    def dec(f):
        @functools.wraps(f)
        def new_func(*args, **kwargs):
            message = "Call to deprecated function {f}{args}. Dep in version: {version}."\
                            .format(version=str(in_version), f=f.__name__, args=str(args))
            if reason is not None:
                message += " Because: " + reason
            log(message, f.__name__)
            return f(*args, **kwargs)
        return new_func
    return dec