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
import csv
import logging
import traceback

# -------------------
# Third party imports
# -------------------

import jinja2

#--------------
# local imports
# -------------

from . import CREATE_TEMPLATE
from .utils import open_database

# ----------------
# Module constants
# ----------------

DESPLIEGUE = "Fotometros TESS-W - Despliegue.csv"

# -----------------------
# Module global variables
# -----------------------

log = logging.getLogger('location')

# -------------------------
# Module auxiliar functions
# -------------------------

def deployment_list(path):
    with open(path, newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=',')
        return [row for row in reader]
    

def database_list(connection):
    cursor = connection.cursor()
    cursor.execute(
        '''
        SELECT DISTINCT name 
        FROM tess_v 
        WHERE valid_state = 'Current'
        AND name LIKE 'stars%'
        AND location = 'Unknown'
        ''')
    return [row[0] for row in cursor]

from functools import partial


def filter_by_name(row, names_iterable):
    if row['stars'] in names_iterable:
        return True
    return False

def valid_coordinates(row):
    '''The minimumn requrement is to have real longitude and latitude'''
    try:
        longitude = float(row.get('Longitud'))
        latitide = float(row.get('Latitud'))
    except ValueError:
        flag = False
    else:
        flag = True
    return flag

def invalid_coordinates(row):
    return not valid_coordinates(row)


def check_disjoint_sets(valid_list, invalid_list):
    '''
    Check if a given photometer is at the same time in the valid list with valid coordinates
    and the invalid list with invalid coordinates
    '''
    valid_set = set([row['stars'] for row in valid_list])
    invalid_set = set([row['stars'] for row in invalid_list])
    problem_set = valid_set.intersection(invalid_set)
    if (len(problem_set)):
        log.info("The following set of photometers have lines in the spreadhseet with both valid and invalid coordinates at the same time:")
        log.info("%r", problem_set )
    else:
        log.info("Check photometer complete")
    return valid_set - problem_set
    

def photometer_filtering(dbase, input_file):
    connection = open_database(dbase)
    deployed_list = deployment_list(input_file)
    registered_list = database_list(connection)
    matching_list = list(filter(partial(filter_by_name, names_iterable=registered_list), deployed_list))
    log.info("Matched %d photometers", len(matching_list))
    valid_coord_list = list(filter(valid_coordinates, matching_list))
    log.info("%d photometers with valid coordinates", len(valid_coord_list))
    invalid_coord_list = list(filter(invalid_coordinates, matching_list))
    purged_set = check_disjoint_sets(valid_coord_list, invalid_coord_list)
    valid_coord_list = list(filter(partial(filter_by_name, names_iterable=purged_set), valid_coord_list))
    log.info("%d photometers with valid coordinates after the problematic ones have been removed", len(valid_coord_list))
    return valid_coord_list

def render(template_path, context):
    if not os.path.exists(template_path):
        raise IOError("No Jinja2 template file found at {0}. Exiting ...".format(template_path))
    path, filename = os.path.split(template_path)
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(path or './')
    ).get_template(filename).render(context)


# ===================
# Module entry points
# ===================

def generate(options):
    log.info("LOCATIONS SCRIPT GENERATION")
    valid_coord_list = photometer_filtering(options.dbase, options.input_file)
    context = dict()
    context['locations'] = valid_coord_list
    context['database'] = options.dbase
    contents = render(CREATE_TEMPLATE, context)
    with open(options.output_file, "w") as script:
        script.write(contents)
    log.info("generated script file at %s", options.output_file)
    
   