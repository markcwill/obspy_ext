#! /usr/bin/env python
#
# obspy antelope module
# by Mark Williams 2012.013
# Oregon State University
#
# Contains basic functions to interect with (read) data form Antelope
# Datascope database tables into ObsPy using the Antelope Python interface.

import sys,os              
sys.path.append(os.path.join(os.environ['ANTELOPE'],'local','data','python'))
from antelope.datascope import *  # all is necessary for db query variables
from obspy.core import read, Stream, UTCDateTime
from obspy.core.util import AttribDict
from numpy import array


class Dbrecord(AttribDict):
    """
    Holds one record line from an Antelope Datascope database
    
    Fields can be accessed as attributes, e.g. dbr.sta or keys, dbr['sta']
    """
    # These are according to Antelope and the schema of your db
    Ptr        = Dbptr()
    Table      = None     # string of what table record came from
    PrimaryKey = ()       # tuple of strings of fields in primary key
    _fields_unsorted = () # tuple of fields from database record
                          #  IN FIELD NUMBERD ORDER        
    @property
    def Fields(self):     
        flist = list(self._fields_unsorted)
        flist.sort()
        return flist
        
    def __init__(self, db=None):
        """
        Create a Dbrecord
        
        Pass an open db pointer, or make an empty one to populate.
        set every field to its value according to the db, even NULLS.
        If there's a problem, you will get None for the value, which won't
        be a NULL value but it's the next best thing.
        
        .. rubric:: Example
        
        >>> dbopen('demo','r')
        >>> db.lookup(table='arrival')
        >>> db.record = 0
        >>> pick = Dbrecord(db)

        """
        if db:
            if db.record == dbALL:
                raise ValueError("Rec # is 'dbALL', for multiple records, use Dbview().")
            self.Ptr              = Dbptr(db)
            self.Table            = db.query(dbTABLE_NAME)
            self.PrimaryKey       = db.query(dbPRIMARY_KEY)
            self._fields_unsorted = db.query(dbTABLE_FIELDS)
            # NOTE: in some cases, the query will return a valid field name,
            # but dbgetv can't extract a value. The try catches this error.
            for field_name in self._fields_unsorted:
                try:
                    field_value = db.getv(field_name)[0]
                except:
                    field_value = None
                super(Dbrecord,self).__setitem__(field_name, field_value)
        else:
            self.Table      =  'Empty'
            self.PrimaryKey = ('Table',)
            self._fields_unsorted = ()
            
    def __repr__(self):
        """
        Useful representation - shows the table and primary key of the record.
        """
        start = "{0}('{1}' -> ".format(self.__class__.__name__, self.Table)
        # Build up a list containing the fields of the primary key
        # Annoyingly, times have a '::' between them, so deal with that...
        mids = []
        for k in self.PrimaryKey:
            if '::' in k:
                keyf = '::'.join([str(self.__dict__[_k]) for _k in k.split('::')])
            else:
                keyf = str(self.__dict__[k])
            mids.append(keyf)
        middle = ' '.join(mids)
        end = ")"    
        return start+middle+end
        
    def __str__(self):
        """
        Prints out record content as a string.
        
        SHOULD be the same as if you cat'ted a line from the table file
        (w/o the extra whitespace)
        """
        fields = [str(self.__dict__[f]) for f in self._fields_unsorted] 
        return ' '.join(fields)


class Dbview(list):
    """
    A list-like container of Dbrecord objects.
    
    A list that accepts a Dbptr as a constructor argument, calls Dbrecord for
    every record the pointer references, and adds it to the list. Index number
    corresponds to record number for that view.
    
    .. rubric:: Example
    >>> db = dbopen('demo','r')
    >>> db.lookup(table='site')
    >>> dblist = Dbview(db)
    >>> db.nrecs() == len(dblist)
    True
    
    """
    def __init__(self, dbv=None):
        """
        Creates a Dbview from a pointer
        
        :type dbv: antelope.datascope.Dbptr
        :param dbv: Open pointer to an Antelope database view or table
        """
        super(Dbview,self).__init__()
        if isinstance(dbv, Dbptr):
            db = Dbptr(dbv)
            self.extend([Dbrecord(db) for db.record in range(db.nrecs())])
        # otherwise returns empty list
        
    # Convenience functions
    def col(self, field):
        """A column of the same field from each Dbrecord"""
        return [dbr[field] for dbr in self if field in dbr.Fields ]
    
    def acol(self, field):
        """A numpy array of the same field from each Dbrecord"""
        return array(self.col(field))


def db2object(dbv):
    """
    Port of Antelope MATLAB toolbox 'db2struct' function.
        
    Returns a Dbview, this is the function version of calling Dbview()
    directly.
    
    :type dbv: antelope.datascope.Dbptr
    :param dbv: Open pointer to an Antelope database view or table
    :rtype: :class:`~obspy.antelope.Dbview`
    :return: Dbview of Dbrecord objeccts
    """
    if isinstance(dbv, Dbptr):
        db = Dbptr(dbv)
    else:
        raise TypeError("'{0}' is not a Dbptr object".format(dbv))
    return Dbview(db)

    
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
        db.lookup(table='wfdisc')
    else:
        raise TypeError("Must input a string or pointer to a valid database")
        
    if station is not None:
        db.subset('sta=~/{0}/'.format(station))
    if channel is not None:
        db.subset('chan=~/{0}/'.format(channel))
    if starttime is not None and endtime is not None:
        ts = starttime.timestamp
        te = endtime.timestamp
        db.subset('endtime > {0} && time < {1}'.format(ts,te) )
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