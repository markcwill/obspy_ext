## anss module
This is just an archive for the obspy portion of my code which writes info from databases to QuakeML for ANSS/USGS reporting of earthquakes. It will probably end up part of a larger program or module for [NSL](http://github.com/NVSeismoLab), but here are my forks of specific ObsPy code.

ANSS is working on defining its QuakeML standard to utilize a namespace called 'catalog'. This creates some problems. One cannot easily parse a QuakeML file and add elements or attributes in a namespace if it is not already defined (other than explicitly changing the namespace map and re-parsing the file). This modified ObsPy code simply adds the capability for renaming/defining a namespace. It is also possible to directly put in attributes into elements, but this is a convenience hackjob for now.

```python
from obspy.core.event import *
from quakeml import writeNamespaceQuakeML
# build up a Catalog of Event objects, etc...
catalog = Catalog(events=[my_events])
ns = {'name':'catalog', 'attributes': { 'datasource': 'ZZ', 'dataid': '999999'}}
writeNamespaceQuakeML(catalog, 'text.xml', namespace=ns)
```
###Example file lines
```
<?xml version='1.0' encoding='utf-8'?>
<catalog:quakeml xmlns:catalog="http://quakeml.org/xmlns/quakeml/1.2" xmlns="http://quakeml.org/xmlns/bed/1.2">
  <eventParameters publicID="quakeml:your_id_here" catalog:datasource="ZZ" catalog:dataid="999999">
```

