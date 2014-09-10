from io import BytesIO


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

    def __is_fp_closed(self):
        try:
            return self.__fp.fp is None
        except AttributeError:
            pass

        try:
            return self.__fp.closed
        except AttributeError:
            pass

        # We just don't cache it then.
        # TODO: Add some logging here...
        return False

    def read(self, amt=None):
        data = self.__fp.read(amt)
        self.__buf.write(data)

        if self.__is_fp_closed():
            if self.__callback:
                self.__callback(self.__buf.getvalue())

            # We assign this to None here, because otherwise we can get into
            # really tricky problems where the CPython interpreter dead locks
            # because the callback is holding a reference to something which
            # has a __del__ method. Setting this to None breaks the cycle
            # and allows the garbage collector to do it's thing normally.
            self.__callback = None

        return data
