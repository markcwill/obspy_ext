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
class XMLNamespace(AttribDict):
    '''
    Holds Namespace info
    
    Extra class I was trying to avoid, but it's a little better than
    passing dicts of dicts of dicts, this has some useful methods,
    which could be more elegantly implemeted in the Pickler class
    at some other time...
    '''
    
    default    = None   # str  - Default namespace (xmlns="this")
    nsmap      = {}     # dict - namespace map for ElementTree elmts
    prefix_map = {}     # dict - prefix keys with list of attributes
                        #    (keys MUST be in nsmap)
    
    def __init__(self, **kwargs):
        '''
        Could work for any namespace, but init to QuakeML ANSS
        '''
        super(XMLNamespace, self).__init__()
        self.default = "http://quakeml.org/xmlns/bed/1.2"
        self.nsmap = {'q' : 'http://quakeml.org/xmlns/quakeml/1.2',
                      'catalog': 'http://anss.org/xmlns/catalog/0.1'}
        self.prefix_map = {'catalog': ['datasource','dataid','eventsource','eventid']}
        if kwargs:
            for k in kwargs:
                self[k] = kwargs[k]
    
    def _prefix(self, key, prefix):
        '''Return an namespaced element/attribute for a given name/prefix'''
        return '{{{ns}}}{tag}'.format(ns=self.nsmap[prefix],tag=key)
    
    def map_prefix(self, attributes):
        '''Return a namespaced attribute dict from the prefix map
        
        Curently a hackjob, won't support identical attributes in
        different namespaces
        '''
        if isinstance(attributes, dict):
            name = attributes.copy() 
        for a in attributes:
            for k in self.prefix_map.keys():
                if a in self.prefix_map[k]:
                    name[self._prefix(a,k)] = name.pop(a)
        return name
    

#
# Inherit Pickler, override _serialize for ANSS compatibility    
#
class NamespacePickler(Pickler):
    '''
    ObsPy quakeml.Pickler with support for the ANSS 'catalog' namespace
    
    See obspy.core.quakeml for details on the Pickler class. This overrides two
    methods, _serialize, and dumps which I then call from my own writeXML fxn,
    
    Basically, a namespace can be passed from writeNamespaceQuakeML as an
    additional keyword argument to dumps, and this version of serialize will check
    and implement the namespace map. A couple things are still hard-coded in,
    like the root element namespace, and attributes are automatically added
    to event and focalMechanism tags. This produces fine QuakeML, but it's
    not namespace generic. You would have to specify elements to add to, and
    their prefixes, and maybe even their values, any way you slice it, it
    would mean a lot more code modifications. Could just change the name to
    'ANSSPickler'.

    When used without passing extra **kwargs, these class methods work
    exactly as their original ObsPy counterparts.
    '''
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
        If kwargs contains a named variable called 'namespace', which is an 
        XMLNamespace, it will use it to add namespaces and any attributes
        in a kwarg called 'attributes'.

        Hard coded to put these attributes into specific esoteric elements
        (event and focalMechanism, for now) for ANSS reporting to USGS.
        
        If used without this kwarg, works exactly as Pickler._serialize()
        """
        # -MCW added if-else to specify ns0 namespace if desired
        nsmap = {}
        ns_attr = {}
        default = 'http://quakeml.org/xmlns/bed/1.2'
        root_space = 'http://quakeml.org/xmlns/quakeml/1.2'
        if 'namespace' in kwargs and isinstance(kwargs['namespace'], XMLNamespace):
            ns = kwargs['namespace']
            default = ns.default
            nsmap = ns.nsmap
            root_space = nsmap['q'] # hard coded, fix this
            # map attributes to proper namespace (temp solution)
            if 'attributes' in kwargs:
                ns_attr = ns.map_prefix(kwargs['attributes'])
        # -MCW end
        root_el = etree.Element(
            '{{{ns}}}quakeml'.format(ns=root_space),
            attrib={'xmlns': default },
            nsmap=nsmap) # -MCW changed space tag, added nsmap
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
