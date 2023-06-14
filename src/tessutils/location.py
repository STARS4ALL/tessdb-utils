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
import math
import logging
import traceback

# -------------------
# Third party imports
# -------------------

import jinja2

#--------------
# local imports
# -------------

from . import CREATE_LOCATIONS_TEMPLATE, PROBLEMATIC_LOCATIONS_TEMPLATE
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
    '''
    Requirement is to have real longitude and latitude
    and properly bound to 180 degress (longitude) or 90 degrees (latitude)
    '''
    try:
        longitude = float(row.get('Longitud')) # may raise a ValueError
        latitude = float(row.get('Latitud'))  # may raise a ValueError
        if( (math.fabs(longitude) > 180) or  (math.fabs(latitude) > 90)):
            raise ValueError
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
    
def check_not_empty_sitenames(row):
    return not (row['Nombre lugar'] == '' or  row['Nombre lugar'].isspace())

def remove_embedded_newlines_in_sitenames(row):
    row['Nombre lugar'] = row['Nombre lugar'].replace("\n","")
    return row

def photometer_filtering(dbase, input_file):
    '''
    Analyzes all photometers from the excel and divides them into two categories:
    - the ones with valid latitud and Longitud coordinates
    - The rest
    '''
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
    log.info("%d photometers with invalid coordinates", len(invalid_coord_list))
    valid_coord_list = list(filter(check_not_empty_sitenames,valid_coord_list))
    valid_coord_list = list(map(remove_embedded_newlines_in_sitenames, valid_coord_list))
    return valid_coord_list, invalid_coord_list

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
    valid_coord_list, invalid_coord_list = photometer_filtering(options.dbase, options.input_file)
    context = dict()
    context['locations'] = valid_coord_list
    context['database'] = options.dbase
    contents = render(CREATE_LOCATIONS_TEMPLATE, context)
    with open(options.output_script, "w") as script:
        script.write(contents)
    log.info("generated script file at %s", options.output_script)
    context['locations'] = invalid_coord_list
    problems = render(PROBLEMATIC_LOCATIONS_TEMPLATE, context)
    with open(options.problems_csv, "w") as csvfile:
        csvfile.write(problems)
    log.info("generated CSV problems file at %s", options.problems_csv)
    
   