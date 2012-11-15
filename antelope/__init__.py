# -*- coding: utf-8 -*-
#
#
"""
obspy antelope module
"""
from obspy_ext.antelope.core import (db2object, readANTELOPE)
from obspy_ext.antelope.dbobjects import (Dbrecord, DbrecordList)
from obspy_ext.antelope.dbpointers import (DbrecordPtr, DbrecordPtrList, AttribDbptr)
from obspy_ext.antelope.utils import (add_antelope_path, open_db_or_string)
