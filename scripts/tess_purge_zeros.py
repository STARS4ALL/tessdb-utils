# /usr/bin/env python

# ----------------------------------------------------------------------
# Copyright (c) 2017 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

from __future__ import generators
from __future__ import division, absolute_import    # needs to be at the top of your module

import os
import os.path
import sys
import argparse
import sqlite3
import datetime
import time

from   collections import deque

# No xrange in Python3
try:
    xrange
except NameError:
    xrange = range

import logging as log

#--------------
# other imports
# -------------

#from . import __version__


# ----------------
# Module constants
# ----------------

DEFAULT_DBASE = "/var/dbase/tess.db"
DEFAULT_FILE  = "purge_zeros.sql"

FIFO_DEPTH = 7

# ----------------
# Global variables
# ----------------

gFIFO = deque(maxlen=FIFO_DEPTH)

# -----------------------
# Module global functions
# -----------------------


def createParser():
    # create the top-level parser
    parser = argparse.ArgumentParser(prog=sys.argv[0], description="TESS Zero Purge " )
    parser.add_argument('file', metavar='<SQL file>', help='Output file to dump SQL statements')
    parser.add_argument('-d', '--dbase', default=DEFAULT_DBASE, help='SQLite database full file path')
    parser.add_argument('-v', '--verbose',  action='store_true', help='verbose log level')
    parser.add_argument('-n', '--name', type=str, help='comma-separated list of TESS-W names for specific filtering')
    return parser


# ==================
# Auxiliar functions
# ==================

# --------------------------
# GENERIC DATABASE FUNCTIONS
# --------------------------

def open_database(dbase_path):
    if not os.path.exists(dbase_path):
       raise IOError("No SQLite3 Database file found at {0}. Exiting ...".format(dbase_path))
    log.info("Opening database %s", dbase_path)
    return sqlite3.connect(dbase_path)


def result_generator(cursor, arraysize=500):
    'An iterator that uses fetchmany to keep memory usage down'
    while True:
        results = cursor.fetchmany(arraysize)
        if not results:
            break
        for result in results:
            yield result

# ---------------------------
# SPECIFIC DATABASE FUNCTIONS
# ---------------------------

def get_photometer_list(connection):
    cursor = connection.cursor()
    cursor.execute(
        '''
        SELECT DISTINCT name
        FROM tess_t
        ORDER BY name ASC;
        ''')
    return [ item[0] for item in cursor.fetchall() ]


def fetch_all_dbreadings(connection, name):
    '''From start of month at midnight UTC'''
    row = {'name': name}
    cursor = connection.cursor()
    cursor.execute(
        '''
        SELECT r.date_id, r.time_id, r.tess_id, r.sequence_number, r.frequency, r.magnitude
        FROM tess_readings_t as r
        JOIN tess_t     as i USING (tess_id)
        WHERE i.name == :name
        ORDER BY r.date_id ASC, r.time_id ASC
        ''', row)
    return cursor


# -------------------
# AUXILIARY FUNCTIONS
# -------------------
def render_sql(data):
    date_id = data[0]
    time_id = data[1]
    tess_id = data[2]
    seqno   = data[3]
    freq    = data[4]
    mag     = data[5]
    return ("DELETE FROM tess_readings_t WHERE date_id == {0} AND time_id == {1} AND tess_id == {2}; -- seq {3} freq {4} mag{5}\n".format(date_id, time_id, tess_id, seqno, freq, mag))


# -------------------
# AUXILIARY FUNCTIONS
# -------------------


def chop(string, sep=None):
    '''Chop a list of strings, separated by sep and 
    strips individual string items from leading and trailing blanks'''
    chopped = [ elem.strip() for elem in string.split(sep) ]
    if len(chopped) == 1 and chopped[0] == '':
        chopped = []
    return chopped


def is_sequence_monotonic(aList):
        # Calculate first difference
        first_diff = [aList[i+1] - aList[i] for i in xrange(len(aList)-1)]
        # Modified second difference with absolute values, to avoid cancellation 
        # in final sum due to symmetric differences
        second_diff = [abs(first_diff[i+1] - first_diff[i]) for i in xrange(len(first_diff)-1)]
        return sum(second_diff) == 0


def is_sequence_invalid(aList):
        '''
        Invalide frequencies have a value of zero
        '''
        return sum(aList) == 0

       
def trace_reading(name, reading, discard):
    mark = "+++" if not discard else "---"
    log.info("[%s] (%02d) [%08dT%06d] [%06d] f=%s, m=%s -> %s", name, reading[2], reading[0], reading[1], reading[3], reading[4], reading[5], mark)

def debug_reading(name, reading, msg):
    log.debug("[%s] (%02d) [%08dT%06d] [%06d] f=%s, m=%s -> %s", name, reading[2], reading[0], reading[1], reading[3], reading[4], reading[5], msg)


def filter_reading(name, row):
        gFIFO.append(row)
        if len(gFIFO) <= FIFO_DEPTH//2:
            log.debug("[%s] Refilling the buffer", name)
            return None
        seqList   = [ item[3]  for item in gFIFO ]
        freqList  = [ item[4]  for item in gFIFO ]
        magList  =  [ item[5]  for item in gFIFO ]
        log.debug("%s: seqList = %s. freqList = %s, magList =%s", name, seqList, freqList, magList)
        chosen_row = gFIFO[FIFO_DEPTH//2]
        if  is_sequence_invalid(magList):
            discard = True
            result  = chosen_row
        else:
            discard = False
            result  = None
        trace_reading(name, chosen_row, discard)
        return result
              

def flush_filter(name):
    while len(gFIFO) > FIFO_DEPTH//2:
        row = gFIFO.popleft()
        debug_reading(name, row, "--- (dupl)")
    while len(gFIFO) > 0:
        row = gFIFO.popleft()
        trace_reading(name, row, False)


# =============
# MAIN FUNCTION
# =============

def main():
    '''
    Utility entry point
    '''
    try:
        options = createParser().parse_args(sys.argv[1:])
        level = log.DEBUG if options.verbose else log.INFO
        log.basicConfig(level=level, format='%(name)s - %(levelname)s - %(message)s')
        connection = open_database(options.dbase)
        if options.name is None:
            tess_names = get_photometer_list(connection)
        else:
            tess_names = chop(options.name, ',')
        with open(options.file, 'w') as outfile:
            outfile.write("BEGIN TRANSACTION;\n")
            for name in tess_names:
                outfile.write("-- deleting {0} invalid readings\n".format(name))
                cursor = fetch_all_dbreadings(connection, name)
                for reading in result_generator(cursor):
                    new_reading = filter_reading(name, reading)
                    if new_reading:
                        sql = render_sql(new_reading)
                        outfile.write(sql)
                flush_filter(name)
            outfile.write("COMMIT;\n")
            
    except KeyboardInterrupt:
        print('Interrupted by user ^C')
    #except Exception as e:
        print("Error => {0}".format(e))

if __name__== "__main__":
    main()

