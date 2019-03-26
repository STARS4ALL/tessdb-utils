#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TESS UTILITY TO PERFORM SOME MAINTENANCE COMMANDS

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

DEFAULT_FILE = "./tess_spreadsheet.csv"
DEFAULT_TPLT = "./templates/macsql-template.j2"
MEASURING = "Midiendo"
CURRENT_DATABASE = "/var/dbase/tess.db"

KEYS = [
    ['tess',       0],
    ['mac',        9],
    ['latitude',  11],
    ['longitude', 12],
    ['elevation', 13],
    ['country',   14],
    ['location',  15],
    ['site_name', 16],
    ['tzone',     19],
    ['status',    21],
    ['owner',     22],
    ['email',     23],
]
  


def open_database():
    if not os.path.exists(CURRENT_DATABASE):
        raise IOError("No SQLite3 Database file found in {0}. Exiting ...".format(CURRENT_DATABASE))
    return sqlite3.connect(CURRENT_DATABASE)
 

def get_instruments_from_db(connection):
    cursor = connection.cursor()
    cursor.execute(
            '''
            SELECT name,mac_address
            FROM tess_t
            WHERE valid_state == "Current"
            AND name LIKE "stars%"
            ORDER BY name ASC;
            ''')
    result = cursor.fetchall()
    result = { name: mac for name, mac in result }
    return result


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
    with open(filename, 'rb') as f:
        csv_reader = csv.reader(utf_8_encoder(f))
        for row in csv_reader:
            # decode UTF-8 back to Unicode, cell by cell:
            yield [unicode(cell, 'utf-8') for cell in row]

# =================

def to_dict(row):
    '''Convert a given row from list form to dictionary'''
    result = dict()
    for key in KEYS:
        try:
            if row[key[1]] == '':
                continue
            result[key[0]] = row[key[1]].strip()
        except Exception as e:
            result[key[0]] = "UNKNOWN" 
    
    if not 'status' in result:
        return dict()
    if not result['status'].startswith(MEASURING):
        return dict()
    if 'mac' in result:
        result['mac'] = result['mac'].upper().replace('-' , ':')
    result['database'] = CURRENT_DATABASE
    result['tess'] = 'stars' + str(tess_index(result['tess']))
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

# =================

def main():
    context = dict()
    data = unicode_csv_reader(DEFAULT_FILE)
    context['excel'] = select_data(data, 1, 1000)
    context['dbase'] = get_instruments_from_db(open_database())
    script = render(DEFAULT_TPLT, context).encode('utf-8')
    print(script)

main()
