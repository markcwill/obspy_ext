# -*- coding: utf-8 -*-
#
#
"""
obspy antelope module
"""
import sys, os
def add_antelope_path():
	_version_string = os.environ['ANTELOPE'].split('/')[-1]
	_pydirs = ['data','python']
	if float(_version_string[:3]) < 5.2:
		_pydirs = ['local'] + _pydirs
	_pypath = os.path.join(os.environ['ANTELOPE'], *_pydirs)
	if _pypath not in sys.path:
		sys.path.append(_pypath)
