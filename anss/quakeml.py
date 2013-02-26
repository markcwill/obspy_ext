#!/usr/bin/env python
#
# by Mark
# 2013-2-13
#
# Use: Use obspy event objects to write out QuakeML for ANSS reporting.
#
# Requirements: 
#               ObsPy (version with event, quakeml support)
#
# Example:
# >>> writeNamespaceQuakeML(catalog, 'test.xml', 
# ...    namespace=XMLNamespace(),
# ...    attributes={ 'datasource':'XX', 'dataid':'999999',
# ...                 'eventsource':'XX'
# ...                }
# ...    )
#
from obspy.core import UTCDateTime
# get rid of star import
from obspy.core.event import *
from obspy.core.quakeml import Pickler
from obspy.core.util import tostring
   
##############################################################################
# obspy tools for writing out QuakeML files
##############################################################################
#
# Inherit Pickler, override _serialize for ANSS compatibility    
#
class NamespacePickler(Pickler):
    '''
    ObsPy quakeml.Pickler with support for the ANSS 'catalog' namespace
    
    See obspy.core.quakeml for details on the Pickler class. This overrides two
    methods, _serialize, and dumps which I then call from my own writeXML fxn,
    
    Basically, this is a namespace-aware/editable version of Pickler, which
    can implement a namespace map.
    
    A couple things are still hard-coded in,
    like the root element namespace, and attributes are automatically added
    to event and focalMechanism tags. This produces fine QuakeML, but it's
    not namespace generic. You would have to specify elements to add to, and
    their prefixes, and maybe even their values, any way you slice it, it
    would mean a lot more code modifications. Could just change the name to
    'ANSSPickler'.

    When used without passing extra **kwargs, these class methods work
    exactly as their original ObsPy counterparts.
    '''
    nsmap = {    None : 'http://quakeml.org/xmlns/bed/1.2',
                  'q' : 'http://quakeml.org/xmlns/quakeml/1.2',
             'catalog': 'http://anss.org/xmlns/catalog/0.1',    }
    
    def _prefix(self, key, prefix=None):
        '''Return an namespaced element/attribute for a given name/prefix'''
        return '{{{ns}}}{tag}'.format(ns=self.nsmap[prefix],tag=key)
    
    def _prefix_mapper(self, tags, prefix=None):
        '''Return a namespaced dictionary for a given dict/prefix'''
        return dict([(self._prefix(tag, prefix),tags[tag]) for tag in tags])
    
    def _namespaced_attributes(self, attributes):
        '''Return a namespaced dictionary given a dict of dicts
        
        Input: dict of dicts where keys are prefixes, like so:
        attributes={'catalog':{'id': '1', 'source':'MoonBase'}}

        Output: One dictionary containing all namespaced values in
        all input dicts namespaced with their keys as prefixes.
        
        '''
        ns_attributes = {}
        for a in attributes:
            ns_attributes.update(self._prefix_mapper(attributes[a], a))
        return ns_attributes


    def dumps(self, catalog, **kwargs):
        """
        Exact copy of the Pickler.dumps() function, for consistency with 
        the ObsPy code
        """
        return self._serialize(catalog, **kwargs)

    def _serialize(self, catalog, pretty_print=True, **kwargs):
        """
        Converts a Catalog object into XML string.

        Modified by Mark - Check for namespaces and attributes for ANSS/USGS
        ----------------
        Can pass a namespace map 'nsmap' and 'attributes' dict keyed by map
        prefix in as kwargs.

        Hard coded to put these attributes into specific esoteric elements
        (event and focalMechanism, for now) for ANSS reporting to USGS.
        
        """
        # -MCW added if-else to specify ns0 namespace if desired
        root_prefix = 'q'
        ns_attr = {}
        # allow for namespace map specification (optional)
        if 'nsmap' in kwargs:
            self.nsmap.update(kwargs['nsmap'])
        # map attributes to proper namespacei using self.nsmap
        if 'attributes' in kwargs:
            ns_attr = self._namespaced_attributes(kwargs['attributes'])
        # -MCW end
        root_el = etree.Element(
            self._prefix('quakeml', root_prefix),
            nsmap=self.nsmap) # -MCW
        catalog_el = etree.Element('eventParameters',
            attrib={'publicID': self._id(catalog.resource_id)})
        if catalog.description:
            self._str(catalog.description, catalog_el, 'description')
        self._comments(catalog.comments, catalog_el)
        self._creation_info(catalog.creation_info, catalog_el)
        root_el.append(catalog_el)
        for event in catalog:
            # create event node
            event_el = etree.Element('event',
                attrib={'publicID': self._id(event.resource_id)})
            event_el.attrib.update(ns_attr) # -MCW
            # optional event attributes
            if hasattr(event, "preferred_origin_id"):
                self._str(event.preferred_origin_id, event_el,
                        'preferredOriginID')
            if hasattr(event, "preferred_magnitude_id"):
                self._str(event.preferred_magnitude_id, event_el,
                         'preferredMagnitudeID')
            if hasattr(event, "preferred_focal_mechanism_id"):
                self._str(event.preferred_focal_mechanism_id, event_el,
                         'preferredFocalMechanismID')
            # event type and event type certainty also are optional attributes.
            if hasattr(event, "event_type"):
                self._str(event.event_type, event_el, 'type')
            if hasattr(event, "event_type_certainty"):
                self._str(event.event_type_certainty, event_el,
                    'typeCertainty')
            # event descriptions
            for description in event.event_descriptions:
                el = etree.Element('description')
                self._str(description.text, el, 'text', True)
                self._str(description.type, el, 'type')
                event_el.append(el)
            self._comments(event.comments, event_el)
            self._creation_info(event.creation_info, event_el)
            # origins
            for origin in event.origins:
                event_el.append(self._origin(origin))
            # magnitudes
            for magnitude in event.magnitudes:
                event_el.append(self._magnitude(magnitude))
            # station magnitudes
            for magnitude in event.station_magnitudes:
                event_el.append(self._station_magnitude(magnitude))
            # picks
            for pick in event.picks:
                event_el.append(self._pick(pick))
            # focal mechanisms -MCW add ns attribs
            for focal_mechanism in event.focal_mechanisms:
                focal_mech_el = self._focal_mechanism(focal_mechanism)
                focal_mech_el.attrib.update(ns_attr)
                event_el.append(focal_mech_el)
            # add event node to catalog
            catalog_el.append(event_el)
        return tostring(root_el, pretty_print=pretty_print)

#
# Mark's version of the Catalog.write QUAKEML method to pass namespace info
#
# forked from obspy.core.quakeml.writeQuakeML()
#
def writeNamespaceQuakeML(catalog, filename, **kwargs):  # @UnusedVariable
    """
    Writes a QuakeML file.

    Modified by Mark for ANSS
    -------------------------
    Changes: - Use NamespacePickler class
             - Pass **kwargs through dumps, to _serialize
             (which now checks for a 'namespace' kwarg)

    :type catalog: :class:`~obspy.core.stream.Catalog`
    :param catalog: The ObsPy Catalog object to write.
    :type filename: str
    :param filename: Name of file to write.
    """
    # Open filehandler or use an existing file like object.
    if not hasattr(filename, 'write'):
        fh = open(filename, 'wt')
    else:
        fh = filename
    xml_doc = NamespacePickler().dumps(catalog, **kwargs)
    fh.write(xml_doc)
    fh.close()
    # Close if its a file handler.
    if isinstance(fh, file):
        fh.close()
#-----------------------------------------------------------------------------
