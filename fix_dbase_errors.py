#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TESS UTILITY TO PERFORM SOME MAINTENANCE COMMANDS

# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#TOTAL: Processed 20721 lines
#{'accepted': {'2018-09': 6, '2019-02': 2, '2018-11': 17325}, 'rejected': {}}


#--------------------
# System wide imports
# -------------------

import datetime

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


import jinja2

# ----------------
# Module constants
# ----------------

LINE1 = r"'runOperation' for row ({.+})"
LINE2 = r"locked for row ({.+})"

DEFAULT_FILE = "./errores_db.txt"
DEFAULT_DBASE = "/var/dbase/tess.db"
DEFAULT_REP_DBASE = "/var/dbase/tess.db-*"
DEFAULT_MODULUS = 400
DEFAULT_TPLT = "./templates/tess_ida-fix.j2"
DEFAULT_DIR  = "/var/dbase/reports/IDA"

# --------------------
# Auxiliary functions
# --------------------

def utf8(s):
    return unicode(s, 'utf8')

def open_database(options):
    if not os.path.exists(options.dbase):
        raise IOError("No SQLite3 Database file found in {0}. Exiting ...".format(options.dbase))
    return sqlite3.connect(options.dbase)
 


def createParser():
    # create the top-level parser
    parser = argparse.ArgumentParser(prog=sys.argv[0])
    parser.add_argument('-i', '--input_file', type=str,  required=True, default=DEFAULT_FILE, help='input file')
    parser.add_argument('-d', '--dbase', default=DEFAULT_DBASE, help='SQLite operational database full file path')
    parser.add_argument('-r', '--reports-dbase', default=DEFAULT_REP_DBASE, help='SQLite reports database full file path')
    parser.add_argument('-m', '--modulus', default=DEFAULT_MODULUS, help='Print progress every N rows')
    parser.add_argument('-o', '--out_dir', default=DEFAULT_DIR, help='Output directory to dump record')
    return parser

def increment(context, topic, key):
    counter = context[topic].get(key, 0)
    counter += 1
    context[topic][key] = counter
    return context


def render(template_path, context):
    if not os.path.exists(template_path):
        raise IOError("No Jinja2 template file found at {0}. Exiting ...".format(template_path))
    path, filename = os.path.split(template_path)
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(path or './')
    ).get_template(filename).render(context)


def insert_row(row, cursor, context):     
    try:
        key = "{0} -m {1}".format(row['name'], row['tstamp'].strftime("%Y-%m"))
        cursor.execute(
        '''
            INSERT INTO tess_readings_t (
                date_id,
                time_id,
                tess_id,
                location_id,
                units_id,
                sequence_number,
                frequency,
                magnitude,
                ambient_temperature,
                sky_temperature
            ) VALUES (
                :date_id,
                :time_id,
                :instr_id,
                :loc_id,
                :units_id,
                :seq,
                :freq,
                :mag,
                :tamb,
                :tsky
            )
            ''', row)
        context = increment(context, 'accepted', key)
    except sqlite3.IntegrityError:
        context = increment(context, 'rejected', key)
    return context




def process_data(regexps, line, cursor, context):
    matchobjs = [ regexp.search(line) for regexp in regexps]
    for matchobj in matchobjs:
        if matchobj:
            row = eval(matchobj.group(1))
            if row['freq'] != 0.0:
                context = insert_row(row, cursor, context)
    return context



def main():
    '''
    Utility entry point
    '''
    context  = dict()
    context['accepted']= {}
    context['rejected']= {}

    lines = 0

    options = createParser().parse_args(sys.argv[1:])
    regexps   = [ re.compile(item) for item in [LINE1, LINE2] ]
    connection = open_database(options)
    cursor = connection.cursor()
    for line in open(options.input_file):
        context = process_data(regexps, line, cursor, context)
        lines += 1
        if lines % options.modulus == 0:
            print("Processed {0} lines".format(lines))
    connection.commit()
    context['database'] = options.reports_dbase
    context['out_dir']  = options.out_dir
    script = render(DEFAULT_TPLT, context).encode('utf-8')
    print(script)




main()
