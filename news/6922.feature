Add support for proper PEP425 tagging for the AIX platform.

The tag format is "AIX.{}.{:04d}.{}".format(vrtl, bd, sz)
The fileset bos.mp64 values for VRMF and Builddate
are the imputs for the run-time values.
For the "build" values the VRM values are obtained
from the configuration variable BUILD_GNU_TYPE.
When available the configuration variable AIX_BUILDDATE
provides the builddate, otherwise a fixed constant
vrtl is calculated from the VRMF value of bos.mp64

patch by M. Felt
