#!/usr/bin/env python
#
# by Mark
# 2013-2-13
#
# Use: Use obspy event objects to write out QuakeML for ANSS reporting.
#
# Requirements: 
#               ObsPy (version with event, quakeml support)
#               Antelope Users Group contributed python module
#
# Example:
# >>> writeNamespaceQuakeML(catalog, 'test.xml', 
# ...    namespace={'name'      : 'catalog',
# ...               'attributes': { 'datasource': 'nn', 'dataid' : '999999'},
# ...              }
# ...    )
#
from obspy.core import UTCDateTime
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
    
    Basically, a namespace can be passed from writeNamespaceQuakeML as an
    additional keyword argument, and this version of serialize will check
    and implement it.

    Right now, you can only pass one namespace, which will simply rename
    the root element namespace from its default 'ns0' to a user choice.
    xmlns:ns0 --> xmlns:catalog, for example. One can then add namespaced
    attributes, like 'catalog:datasource' to QuakeML elements.
    
    The default namespace 'xmlns' is unchanged.

    This is the simplest way to make your QuakeML compliant with
    ANSS/USGS reporting.

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

        Modified by Mark - force 'ns0' namespace to be named
        ----------------
        If kwargs contains a named variable called 'namespace', which is a dict --
        namespace={'name' : <str of namespace>, 'attributes' : <dict of attr>}
        -- it will use namespace['name'] as the default namespace, and
        will stick all of the keys in namespace['attributes'] in selected
        esoteric elements (event, origin, momenttensor) for ANSS reporting
        to USGS.
        
        If used without this kwarg, works exactly as Pickler._serialize()
        """
        # -MCW added if-else to specify ns0 namespace if desired
        space = 'http://quakeml.org/xmlns/quakeml/1.2'
        if 'namespace' in kwargs:
            namespace = kwargs['namespace']
            ns_name = namespace['name']
            ns_attr = namespace['attributes'].copy()
            nsmap = { ns_name : space }
            # map attributes 'k' to new namespace new_k ='{space}k'
            for k in ns_attr.keys():
                new_k = '{{{ns}}}{tag}'.format(ns=space, tag=k)
                ns_attr[new_k] = ns_attr.pop(k)
        else:
            nsmap = None
            ns_name = None
            ns_attr = {}
        # -MCW end
        root_el = etree.Element(
            '{{{ns}}}quakeml'.format(ns=space),
            attrib={'xmlns': "http://quakeml.org/xmlns/bed/1.2"},
            nsmap=nsmap) # -MCW changed space tag, added nsmap
        catalog_el = etree.Element('eventParameters',
            attrib={'publicID': self._id(catalog.resource_id)})
        catalog_el.attrib.update(ns_attr) # -MCW
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
            # focal mechanisms
            for focal_mechanism in event.focal_mechanisms:
                event_el.append(self._focal_mechanism(focal_mechanism))
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
