The build step of ``pip wheel`` now builds all wheels to a cache first,
then copies them to the wheel directory all at once.
Before, it built them to a temporary direcory and moved
them to the wheel directory one by one.
