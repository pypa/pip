Added a way to distinguish between pip installed packages and those from
the system package manager in 'pip list'. Specifically, 'pip list -v' also
shows the installer of package if it has that meta data.
