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
import glob
import logging
import traceback

# -------------------
# Third party imports
# -------------------


#--------------
# local imports
# -------------

#--------------
# local imports
# -------------

from . import CREATE_TEMPLATE 

# ----------------
# Module constants
# ----------------


# -----------------------
# Module global variables
# -----------------------

log = logging.getLogger('location')

# ===================
# Module entry points
# ===================

def generate(options):
	log.info("LOCATION GENERATION")