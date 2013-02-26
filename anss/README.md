## anss module
This is just an archive for the obspy portion of my code which writes info from databases to QuakeML for ANSS/USGS reporting of earthquakes. It will probably end up part of a larger program or module for [NSL](http://github.com/NVSeismoLab), but here are my forks of specific ObsPy code.

ANSS is working on defining its QuakeML standard to utilize a namespace called 'catalog'. This modified ObsPy code adds the capability for renaming/defining a namespace. It is also set up (for now) to directly put in attributes into the 'event' and 'focalMechanism' elements, but this is a convenience hackjob for now.

One can now modify the lxml.etree namespace map by passing one to NamespacePickler through the write function included here. ONe can also pass a dictionary of dictionary variables as attributes. Still experimental and needs some generalization, but it works and produces valid QuakeML. Right now, a default NamespacePickler inits to the ANSS namespace mappings.

```python
from obspy.core.event import *
from quakeml import writeNamespaceQuakeML
# build up a Catalog of Event objects, etc...
catalog = Catalog(events=[Event()], resource_id=ResourceIdentifier('quakeml:your_id_here'))
# this is unnecessary (the class has 'catalog' in its default nsmap), but included as an example
ns_mapping = {'catalog': 'http://anss.org/xmlns/catalog/0.1'}
# add any desired attributes (forced into event and focalMechanism elements)
atts = {'catalog': {'datasource':'ZZ', 'dataid':'999999'}}
# This produces the example
writeNamespaceQuakeML(catalog, 'quakeml.xml', nsmap=ns_mapping, attributes=atts)
```
###Example file lines
```
<?xml version='1.0' encoding='utf-8'?>
<q:quakeml xmlns:q="http://quakeml.org/xmlns/quakeml/1.2" xmlns:catalog="http://anss.org/xmlns/catalog/0.1" xmlns="http://quakeml.org/xmlns/bed/1.2">
  <eventParameters publicID="quakeml:your_id_here" catalog:datasource="ZZ" catalog:dataid="999999">
```

