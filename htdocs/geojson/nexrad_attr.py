#!/usr/bin/env python
""" Generate a GeoJSON of nexrad attributes"""
import memcache
import sys
import cgi


def run():
    """ Actually do the hard work of getting the geojson """
    import json
    import psycopg2.extras
    import datetime

    pgconn = psycopg2.connect(database='postgis', host='iemdb', user='nobody')
    cursor = pgconn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    utcnow = datetime.datetime.utcnow()

    cursor.execute("""
        SELECT ST_x(geom) as lon, ST_y(geom) as lat, *,
        valid at time zone 'UTC' as utc_valid from
        nexrad_attributes WHERE valid > now() - '30 minutes'::interval
    """)

    res = {'type': 'FeatureCollection',
           'crs': {'type': 'EPSG',
                   'properties': {'code': 4326, 'coordinate_order': [1, 0]}},
           'features': [],
           'generation_time': utcnow.strftime("%Y-%m-%dT%H:%M:%SZ"),
           'count': cursor.rowcount}
    for i, row in enumerate(cursor):
        res['features'].append({"type": "Feature", "id": i, "properties": {
                "nexrad": row["nexrad"],
                "storm_id": row["storm_id"],
                "azimuth": row["azimuth"],
                "range": row["range"],
                "tvs": row["tvs"],
                "meso": row["meso"],
                "posh": row["posh"],
                "poh": row["poh"],
                "max_size": row["max_size"],
                "vil": row["vil"],
                "max_dbz": row["max_dbz"],
                "max_dbz_height": row["max_dbz_height"],
                "top": row["top"],
                "drct": row["drct"],
                "sknt": row["sknt"],
                "valid":  row['utc_valid'].strftime("%Y-%m-%dT%H:%M:%SZ")
            },
            "geometry": {"type": "Point",
                         "coordinates": [row['lon'], row['lat']]
                         }
        })

    return json.dumps(res)


def main():
    """Do Something"""
    # Go Main Go
    sys.stdout.write("Content-type: application/vnd.geo+json\n\n")

    form = cgi.FieldStorage()
    cb = form.getfirst('callback', None)

    mckey = "/geojson/nexrad_attr.geojson"
    mc = memcache.Client(['iem-memcached:11211'], debug=0)
    res = mc.get(mckey)
    if not res:
        res = run()
        mc.set(mckey, res, 30)

    if cb is None:
        sys.stdout.write(res)
    else:
        sys.stdout.write("%s(%s)" % (cb, res))

if __name__ == '__main__':
    main()