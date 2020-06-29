#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# TESS UTILITY TO PERFORM SOME MAINTENANCE COMMANDS
# 

# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import csv
import re
import os
import os.path

import sys
import argparse
import sqlite3
import json
import datetime
import shlex
import subprocess

#--------------
# other imports
# -------------

import jinja2

# ----------------
# Module constants
# ----------------

DEFAULT_FILE     = "./Fotometros TESS-W - Despliegue.csv"
DEFAULT_TPLT     = "./templates/location-template.j2"
MEASURING        = "midiendo"
CURRENT_DATABASE = "/var/dbase/tess.db"

KEYS = [
    ['tess',       0],  # TESS name
    ['mac',        1],   # 
    ['latitude',   2],
    ['longitude',  3],
    ['elevation',  4],
    ['status',     5],  # Free descriptive status
    ['country',    7],
    ['location',   8],  
    ['site_name',  9],  # Location site name
    ['tzone',      11],  # Timezone
    ['owner',      12],  # Contact name
    ['email',      13],  # Contact email
    ['org',        14],  # Organization
]
  

# ====== SELECTING TESS BY INDEX NUMBER

def tess_index(tess_name):
    pattern = re.compile('^stars(\d{1,3})')
    matchobj = pattern.search(tess_name)
    if matchobj:
        return int(matchobj.group(1))
    else:
        return 0


def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        yield line

def unicode_csv_reader(filename):
    # csv.py doesn't do Unicode; encode temporarily as UTF-8:
    with open(filename, 'r') as f:
        csv_reader = csv.reader(utf_8_encoder(f))
        for row in csv_reader:
            # decode UTF-8 back to Unicode, cell by cell:
            yield row



def to_dict(row):
    '''Convert a given row from list form to dictionary'''
    #print("--- BEGIN ---"*3); print(row); 
    result = dict()
    for key in KEYS:
        #print(key)
        try:
            # if value is empty for a given key, continue
            if row[key[1]] == '':
                #print("VACIO")
                continue
            #print("JOPUTA {0:s}".format(result[key[0]]))
            result[key[0]] = row[key[1]].strip()
        except Exception as e:
            result[key[0]] = "UNKNOWN" 
    
    if not 'site_name' in result:
        print("# {0:s}: Missing site name field".format(result['tess']))
        return dict()
    if not 'longitude' in result:
        print("# {0:s}: Missing longitude field".format(result['tess']))
        return dict()
    if not 'latitude' in result:
        print("# {0:s}: Missing latitude field".format(result['tess']))
        return dict()
    if not 'elevation' in result:
        print("# {0:s}: Missing elevation field".format(result['tess']))
        return dict()
    if not 'status' in result:
        print("# {0:s}: Missing status field".format(result['tess']))
        return dict()

    result['operable'] = True if result['status'].lower().startswith(MEASURING) else False
    result['database'] = CURRENT_DATABASE
    result['tess'] = 'stars' + str(tess_index(result['tess']))
    #print("--- END ---"*3)
    return result


def select_data(data, lower, upper):
    result = [ to_dict(row) for row in data if lower <= tess_index(row[0]) <= upper]
    # takes out empty dictionaries
    result = [ row for row in result if bool(row) ]
    return result

# =================




def render(template_path, context):
    if not os.path.exists(template_path):
        raise IOError("No Jinja2 template file found at {0}. Exiting ...".format(template_path))
    path, filename = os.path.split(template_path)
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(path or './')
    ).get_template(filename).render(context)


def main():
    data = unicode_csv_reader(DEFAULT_FILE)
    rows = select_data(data, 1, 1000)
    context = dict()
    context['locations'] = rows
    script = render(DEFAULT_TPLT, context)
    print(script)

main()
