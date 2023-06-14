# ----------------------------------------------------------------------
# Copyright (c) 2020
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import os
import sys

# Access SQL scripts withing the package
from pkg_resources import resource_filename

#--------------
# local imports
# -------------

from ._version import get_versions

# ----------------
# Module constants
# ----------------

DEFAULT_DBASE = '/var/dbase/tess.db'

# -----------------------
# Module global variables
# -----------------------

__version__ = get_versions()['version']

# DATABASE RESOURCES
CREATE_LOCATIONS_TEMPLATE = resource_filename(__name__, os.path.join('templates', 'location-create.j2'))
PROBLEMATIC_LOCATIONS_TEMPLATE = resource_filename(__name__, os.path.join('templates', 'location-problematic.j2'))
del get_versions

