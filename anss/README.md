## anss module
This is just an archive for the obspy portion of my code which writes info from databases to QuakeML for ANSS/USGS reporting of earthquakes. It will probably end up part of a larger program or module for [NSL](http://github.com/NVSeismoLab), but here are my forks of specific ObsPy code.

ANSS is working on defining its QuakeML standard to utilize a namespace called 'catalog'. This modified ObsPy code adds the capability for renaming/defining a namespace. It is also set up (for now) to directly put in attributes into the 'event' and 'focalMechanism' elements, but this is a convenience hackjob for now.

Added the XMLNamespace class, which can be passed into the Pickler. Still experimental and needs some generalization, but it works and produces valid QuakeML. Right now, a default XMLNamespace inits to the ANSS namespace mappings.

```python
from obspy.core.event import *
from quakeml import XMLNamespace, writeNamespaceQuakeML
# build up a Catalog of Event objects, etc...
catalog = Catalog(events=[my_events])
atts = {'datasource':'ZZ', 'dataid':'999999'}
writeNamespaceQuakeML(catalog, 'text.xml', namespace=XMLNamespace(), attributes=atts)
```
###Example file lines
```
<?xml version='1.0' encoding='utf-8'?>
<q:quakeml xmlns:q="http://quakeml.org/xmlns/quakeml/1.2" xmlns:catalog="http://anss.org/xmlns/catalog/0.1" xmlns="http://quakeml.org/xmlns/bed/1.2">
  <eventParameters publicID="quakeml:your_id_here" catalog:datasource="ZZ" catalog:dataid="999999">
```

