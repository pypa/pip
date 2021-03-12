Run the wheel install in a multiprocessing Pool, this has x1.5 speedup factor
when installing cached packages. Packages that could not be installed
(exception raised), will be installed serially once the Pool is done.
If multiprocessing.Pool is not supported by the platform,
fall-back to serial installation.
