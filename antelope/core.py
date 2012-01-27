#! /usr/bin/env python
#
# obspy antelope module
# by Mark Williams 2012.013
# Oregon State University
#
# Contains basic functions to interect with (read) data form Antelope
# Datascope database tables into ObsPy using the Antelope Python interface.
#
# This module will automatically add the antelope path, provided you have the
# $ANTELOPE environment variable set, which should be if Antelope is installed.
# If memory serves me correctly, you may need to set $PFPATH for the setup
# to actually work... just set it to the default:
#
# prompt$ PFPATH=$ANTELOPE/data/pf
#
# Obviously, you need to have the antelope python modules compiled and
# working on your machine before the import below will work. Here is the short
# version, adapted from /opt/antelope/5.0-64/Changes.txt:
#-----------------------------------------------------------------------------
# (1) Download the whole contributed-code repository from the github:
#       https://github.com/antelopeusersgroup/antelope_contrib
#       - unpack the source to src/contrib under the antelope dir
#       - DO NOT 'make' the whole thing, especially if your contributed
#         programs are working fine... I have had some compiler/linker issues
#         related to 32/64 bit stuff. I don't reccommend it.
#
# (2) Run the 'localmake_config' utility from command line
#       - enter the paths to the version of python you are using
#
# (3) Compile the interfaces by hand or, provided the
#     source-code is in the standard location $ANTELOPE/src/contrib,
#     you may use the localmake(1) utility e.g.:
#  	    prompt$ localmake python_antelope
#-----------------------------------------------------------------------------
#
# LOG: 2012.012 -Drafted v0.1.0 assembled from other classes/functions
#                and my personal modules.
#      2012.019 -v0.1.1
#               -Dbrecord now inherits from Obspy AttribDict, and
#               -New class! Dbview is a list of Dbrecords (a view OR
#                a table)
#               -db2object is now just a functionized version of the
#                Dbview class constuctor
#      2012.025 -v0.2.0
#               -added two classes, DbAttribPtr and DbAttribPtrList. For
#                large tables, this works better as only the pointers
#                are stored, not the entire table. Otherwise, they work
#                the same.
#      2012.026 -v0.2.1
#               -got DbMegaPtr working... one pointer, one love.
#
# FUTURE:
# - possibly change the tuple attributes of DBrecord to lists?
#
# - in place of dbTABLE_NAME in Dbrecord, check for dbTABLE_IS_VIEW
#   and use dbVIEW_TABLES? Might make repr string awkward though.
#
# - Could try and add db fields right into Stats in readANTELOPE,
#   if a joined view is passed, can contain other info like lat/lon
#   which for now will be in trace.db of the Trace.
#
# - Could make a realish ORM by creating a Dbview class which contains the
#   data, an AttribDptr and an _update() method. Then one could make changes
#   locally and do a type of 'commit' by updating the pointer object using
#   the data in the local object.
#
# NOTES:
# readANTELOPE:
# - Adding the 'db' attribute to Trace.stats basically remaps the Dbrecord
#   object to a AttribDict, because it passes the test as an instance of dict
#   basically a coding issue in Stats.__setattr__(), so it's either accept
#   that or do what I did and make it a Trace attribute directly.
#
##############################################################################
# OVERVIEW:
#
# Dbrecord    - basically a dictionary/object which holds all the data from
#               one record of a table. Field access as key or attribute.
#
# Dbview      - A list of Dbrecord's. ALL data are local, in namespace and memory.
#
# DbrecordPtr - acts the same as a Dbrecord, but the data are not local,
#               they are read from/(AND WRITTEN TO) to the database.
#
# DbviewPtr   - A list of DbrecordPtr's. Suitable for most occasions. Because
#               Dbview's can take up memory for a lot of records.
#
# AttribDbptr - A test class I'm building which consists of just a couple
#               pointers, no matter how many records are contained. Based on
#               DbviewPtr.
#
# db2object   - just a function that calls the constructor for Dbview. This
#               module began as me writing the 'db2struct' function in MATLAB
#               in Pythonese.
#
# readANTELOPE - Function which acts like an obspy.read for a 'wfdisc' table
#                (or any table which contains a waveform filename). Gives you
#                a Stream with 1 Trace for each record line in wfdisc, and
#                puts a Dbrecord in as an attribute of the Trace.

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

class DbrecordPtr(dict, object):
    """
    Holds the pointer to a db record, NOT the data, can access the
    same as Dbrecord, but the pointer must remain open
    
    Useful for large datasets that may have trouble in memory
    Only stores the pointer, not contents, all attributes are
    returned by querying the open db using the pointer.
    """
    # Only holds one thing in Python namespace, Dbptr object:
    Ptr = Dbptr()
    
    @property
    def Table(self):
        return self.Ptr.query(dbTABLE_NAME)  # string of what table record came from
    @property
    def PrimaryKey(self):
        return self.Ptr.query(dbPRIMARY_KEY) # tuple of strings of fields in primary key
    @property
    def _fields_unsorted(self):              # tuple of fields from database record
        return self.Ptr.query(dbTABLE_FIELDS)        
    @property
    def Fields(self):     
        flist = list(self._fields_unsorted)
        flist.sort()
        return flist
        
    def __init__(self, db=None):
        """
        Testing object relational mapper-type thing...
        """
        if db:
            if db.record == dbALL:
                raise ValueError("Rec # is 'dbALL', one record only, please.")
            self.Ptr = Dbptr(db)
        else:
            self.Ptr = Dbptr()
            raise NotImplementedError("No empty contructor allowed here yet...")
            
    def __getattr__(self, field):
        """
        Looks for attributes in fields of a db pointer
        """
        return self.Ptr.getv(field)[0]
        
    def __setattr__(self, field, value):
        """Try to set a db field
        
        You must have opened your db with r+ permissions!
        """
        # Special case: trying to set the pointer. Else try to write to the db
        if field == 'Ptr':
            super(DbrecordPtr,self).__setattr__(field, value)           
        else:    
           # Could try to catch an ElogComplain in else, but the same
           # error comes up for read-only or a wrong field
           # if self.Ptr.query(dbDATABASE_IS_WRITABLE):
           self.Ptr.putv(field, value)
        
    # Dictionary powers activate:
    __getitem__ = __getattr__
    __setitem__ = __setattr__
        
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
                keyf = '::'.join([str(self.__getattr__(_k)) for _k in k.split('::')])
            else:
                keyf = str(self.__getattr__(k))
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
        fields = [str(self.__getattr__(f)) for f in self._fields_unsorted] 
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

class DbviewPtr(list):
    """
    A list-like container of DbrecordPtr objects.
    
    A list that accepts a Dbptr as a constructor argument, calls DbrecordPtr for
    every record the pointer references, and adds it to the list.
    
    .. rubric:: Example
    >>> db = dbopen('demo','r')
    >>> db.lookup(table='site')
    >>> dblist = DbviewPtr(db)
    >>> db.nrecs() == len(dblist)
    True
    
    """
    def __init__(self, dbv=None):
        """
        Creates a Dbview from a pointer
        
        :type dbv: antelope.datascope.Dbptr
        :param dbv: Open pointer to an Antelope database view or table
        """
        super(DbviewPtr,self).__init__()
        if isinstance(dbv, Dbptr):
            db = Dbptr(dbv)
            self.extend([DbrecordPtr(db) for db.record in range(db.nrecs())])
        # otherwise returns empty list
        
    # Convenience functions
    # may do funny things if you have records from different tables...
    def col(self, field):
        """A column of the same field from each Dbrecord"""
        return [dbr[field] for dbr in self if field in dbr.Fields ]
    
    def acol(self, field):
        """A numpy array of the same field from each Dbrecord"""
        return array(self.col(field)) 
        
class AttribDbptr(list):
    """
    A pointer to a DB view, that acts like a Python list of DbrecordPtr's.
    
    This is essentially a very basic object-relational-mapper for an Antelope
    Datascope database using the existing Dbptr class.
    
    No data (not even individual record pointers) are stored. The object acts like
    a list (similar to Dbview and DbviewPtr) but the entire
    contents are just a pointer to an open db and one integer
    
    When accessing items, will return a DbrecordPtr, by building a pointer,
    rather than actually storing them in the list.
    
    Should work exactly like DbviewPtr except slicing doesn't work right now. That
    may take some work (should it be implemented as subsetting, or just selecting within
    Python?)
    
    Good for large datasets that would take up a lot of memory to load the whole table
    or even millions of DbrecordPtr's (which are holding one Dbptr each) into RAM.
    
    Attributes
    ----------
    Ptr - the actual Dbptr
    
    .. rubric:: Example
    >>> db = dbopen('/opt/antelope/data/db/demo/demo')
    >>> db.lookup(table='site')
    >>> dbptr = AttribDbptr(db)
    >>> len(dbptr)
    13
    >>> print dbptr[0].sta, dbptr[0].lat, dbptr[0].lon
    HIA 49.2667 119.7417
    >>> print dbptr[10].sta, dbptr[10].lat, dbptr[10].lon
    TKM 42.8601 75.3184
    """
    Ptr = Dbptr() # the only data stored locally
    _rptr = -1    # internal pointer for the 'list'
    
    def __init__(self, dbv=None):
        """
        Sets the pointer
        
        :type dbv: antelope.datascope.Dbptr
        :param dbv: Open pointer to an Antelope database view or table
        """
        super(AttribDbptr,self).__init__()
        if isinstance(dbv, Dbptr):
            self.Ptr = Dbptr(dbv)
        # otherwise returns empty list
        
    def __getitem__(self, index):
        """
        Build a pointer to an individual record
        """
        if 0 <= index < len(self):
            dbp = Dbptr(self.Ptr)
            dbp[3] = index
            return DbrecordPtr(dbp)
        else:
            raise ValueError("Index out of range")

    def __len__(self):
        """Number of items in the view"""
        return self.Ptr.nrecs()
    
    def __iter__(self):
        """Required for an iterator"""
        return self
        
    def next(self):
        """Return next item in the 'list'"""
        self._rptr += 1
        if self._rptr < len(self):
            return self.__getitem__(self._rptr)
        else:
            self._rptr = -1
            raise StopIteration    

    # Convenience methods
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