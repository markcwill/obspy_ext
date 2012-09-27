#! /usr/bin/env python
#
# obspy antelope module
# by Mark Williams 2012.013
# Oregon State University
#
# Contains basic functions to interect with (read) data from Antelope
# Datascope database tables into ObsPy using the Antelope Python interface.

from numpy import array
from obspy.core import read, Stream, UTCDateTime
from obspy_ext.antelope.utils import add_antelope_path
from obspy_ext.antelope.dbobjects import Dbrecord, DbrecordList 
# Antelope path to python tools not added by default install
add_antelope_path()               # adds path if not there
from antelope.datascope import *  # all is necessary for db query variables


def db2object(dbv):
    """
    Port of Antelope MATLAB toolbox 'db2struct' function.
        
    Returns a list-like object, this is the function version of calling
    DbrecordList() directly.
    
    :type dbv: antelope.datascope.Dbptr
    :param dbv: Open pointer to an Antelope database view or table
    :rtype: :class:`~obspy.antelope.Dbview`
    :return: Dbview of Dbrecord objeccts
    """
    if isinstance(dbv, Dbptr):
        db = Dbptr(dbv)
    else:
        raise TypeError("'{0}' is not a Dbptr object".format(dbv))
    return DbrecordList(db)

    
def readANTELOPE(database, station=None, channel=None, starttime=None, endtime=None):
    '''
    Reads a portion of a Antelope wfdisc table to a Stream.
    
    Attempts to return one Trace per line of the 'wfdisc' view passed.    
    Additionally, will filter and cut with respect to any of the fields
    in the primary key IF specified. (sta chan time::endtime)
    
    NOTE: Currently MUST have both times (start/end) or neither.
    the returned Traces will have a new attribute, 'db'

    :type database: string or antelope.datascope.Dbptr
    :param database: Antelope database name or pointer
    :type station: string
    :param station: Station expression to subset
    :type channel: string
    :param channel: Channel expression to subset
    :type starttime: :class: `~obspy.core.utcdatetime.UTCDateTime`
    :param starttime: Desired start time
    :type endtime: :class: `~obspy.core.utcdatetime.UTCDateTime`
    :param endtime: Desired end time
        
    :rtype: :class: `~obspy.core.stream.Stream'
    :return: Stream with one Trace for each row of the database view
    
    .. rubric:: Example
    
    >>> st = readANTELOPE('/Volumes/colza_HD/dbs/land', station='TOL0', channel='LH.',
                        starttime=UTCDateTime(2008,6,13), endtime=UTCDateTime(2008,6,14))
    >>> print(st)
    6 Trace(s) in Stream:
    XA.TOL0..LHE | 2008-06-12T23:59:59.640000Z - 2008-06-13T00:04:11.640000Z | 1.0 Hz, 253 samples
    XA.TOL0..LHE | 2008-06-13T00:04:12.640000Z - 2008-06-13T23:59:59.640000Z | 1.0 Hz, 86148 samples
    XA.TOL0..LHN | 2008-06-12T23:59:59.640000Z - 2008-06-13T00:04:11.640000Z | 1.0 Hz, 253 samples
    XA.TOL0..LHN | 2008-06-13T00:04:12.640000Z - 2008-06-13T23:59:59.640000Z | 1.0 Hz, 86148 samples
    XA.TOL0..LHZ | 2008-06-12T23:59:59.640000Z - 2008-06-13T00:04:21.640000Z | 1.0 Hz, 263 samples
    XA.TOL0..LHZ | 2008-06-13T00:04:22.640000Z - 2008-06-13T23:59:59.640000Z | 1.0 Hz, 86138 samples
    
    Also adds a Dbrecord as an attribute of the Trace
    
    >>> st[0].db
    Dbrecord('View43' -> TOL0 LHE 1213229044.64::1213315451.64)
 
    '''
    if isinstance(database,Dbptr):
        db = Dbptr(database)
    elif isinstance(database,str):
        db = dbopen(database, 'r')
        db = dblookup(db,table='wfdisc')
    else:
        raise TypeError("Must input a string or pointer to a valid database")
        
    if station is not None:
        db = dbsubset(db,'sta=~/{0}/'.format(station))
    if channel is not None:
        db = dbsubset(db,'chan=~/{0}/'.format(channel))
    if starttime is not None and endtime is not None:
        ts = starttime.timestamp
        te = endtime.timestamp
        db = dbsubset(db,'endtime > {0} && time < {1}'.format(ts,te) )
    else:
        ts = starttime
        te = endtime
    assert db.nrecs() is not 0, "No records for given time period"
    
    st = Stream()
    for db.record in range(db.nrecs() ):
        fname = db.filename() 
        dbr = Dbrecord(db)
        t0 = UTCDateTime(dbr.time)
        t1 = UTCDateTime(dbr.endtime)
        if dbr.time < ts:
            t0 = starttime
        if dbr.endtime > te:
            t1 = endtime
        _st = read(fname, starttime=t0, endtime=t1)         # add format?
        _st = _st.select(station=dbr.sta, channel=dbr.chan) #not location aware
        _st[0].db = dbr
        st += _st
    # Close what we opened, BUT garbage collection may take care of this:
    # if you have an open pointer but pass db name as a string, global
    # use of your pointer won't work if this is uncommented:
    #
    #if isinstance(database,str):
    #    db.close()
    return st
