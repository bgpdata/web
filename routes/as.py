from flask import Blueprint, render_template, abort, current_app as app
from utils.database import PostgreSQL
from sqlalchemy import text
import httpx

# Create Blueprint
as_blueprint = Blueprint('as', __name__)

@as_blueprint.route("/<int:asn>")
async def asn(asn):
    try:
        # Retrieve ASN name
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://stat.ripe.net/data/as-names/data.json?resource=AS{asn}", timeout=10)
            response.raise_for_status()
            as_name = response.json()['data']['names'].get(str(asn), "Unknown")
#
        prefix = "2001:67c:2e8::/48"
        query = text(f"SELECT * FROM ris_lite WHERE prefix = '{prefix}' ORDER BY timestamp DESC LIMIT 10000")
        
        # Retrieve Routing History from Local
        async with PostgreSQL() as session:
            result = await session.execute(query)
            rows = result.fetchall()
            
        two_hops=False

        # Organize by origin and prefix
        by_origin = {}
        for row in rows:
            prefix = row['prefix']
            timestamp = row['timestamp']
            full_peer_count = row['full_peer_count']
            path = row['segment'].split(',')

            if prefix == "0/0" or prefix == "::/0":  # Ignore default routes
                continue

            if full_peer_count < 1:  # Apply low peer visibility filter
                continue

            origin = path[-1]
            if two_hops and len(path) > 1:
                first_hop = path[-2]
                origin_tuple = (first_hop, origin)
            else:
                origin_tuple = (origin,)

            # Organize by origin and prefix
            by_origin.setdefault(origin_tuple, {})
            by_origin[origin_tuple].setdefault(prefix, [])
            by_origin[origin_tuple][prefix].append((timestamp, full_peer_count))

        app.logger.info(f"Local ris_lite data for AS{asn}: {by_origin}")

        # Retrieve Routing History from RIPEstat
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://stat.ripe.net/data/routing-history/data.json?resource={prefix}", timeout=10)
            response.raise_for_status()
            ripestat_results = response.json()['data']['by_origin']
        
        app.logger.info(f"RIPEstat routing history for AS{asn}: {ripestat_results}")

    except Exception as e:
        app.logger.error(f"Failed to retrieve AS{asn}: {str(e)}")
        return abort(500, description="An error occurred")

    return render_template('pages/asn.html', asn=asn, as_name=as_name)