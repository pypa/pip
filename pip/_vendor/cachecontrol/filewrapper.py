from io import BytesIO

from .compat import is_fp_closed


class CallbackFileWrapper(object):
    """
    Small wrapper around a fp object which will tee everything read into a
    buffer, and when that file is closed it will execute a callback with the
    contents of that buffer.

    All attributes are proxied to the underlying file object.

    This class uses members with a double underscore (__) leading prefix so as
    not to accidentally shadow an attribute.
    """

    def __init__(self, fp, callback):
        self.__buf = BytesIO()
        self.__fp = fp
        self.__callback = callback

    def __getattr__(self, name):
        return getattr(self.__fp, name)

    def read(self, amt=None):
        data = self.__fp.read(amt)
        self.__buf.write(data)

        # Is this the best way to figure out if the file has been completely
        #   consumed?
        if is_fp_closed(self.__fp):
            self.__callback(self.__buf.getvalue())

            # We assign this to None here, because otherwise we can get into
            # really tricky problems where the CPython interpreter dead locks
            # because the callback is holding a reference to something which
            # has a __del__ method. Setting this to None breaks the cycle
            # and allows the garbage collector to do it's thing normally.
            self.__callback = None

        return data
