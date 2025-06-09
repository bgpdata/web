from flask import Blueprint, render_template, abort, current_app as app
from utils.database import PostgreSQL
from sqlalchemy import text

# Create Blueprint
asn_blueprint = Blueprint('as', __name__)

@asn_blueprint.route("/<int:asn>")
def asn(asn):
    try:
        # Initialize database connection
        db = PostgreSQL()
        
        # Query for IPv4 prefixes
        ipv4_query = text("""
            SELECT count(*) as count
            FROM global_ip_rib
            WHERE recv_origin_as = :asn
            AND family(prefix) = 4
            GROUP BY prefix
        """)
        
        # Query for IPv6 prefixes
        ipv6_query = text("""
            SELECT count(*) as count
            FROM global_ip_rib
            WHERE recv_origin_as = :asn
            AND family(prefix) = 6
            GROUP BY prefix
        """)
        
        # Execute queries
        ipv4_result = db.execute(ipv4_query, {"asn": asn})
        ipv6_result = db.execute(ipv6_query, {"asn": asn})
        
        # Calculate totals
        ipv4_count = sum(row[0] for row in ipv4_result.fetchall())
        ipv6_count = sum(row[0] for row in ipv6_result.fetchall())
        
        # Get AS name from info_asn table
        as_name_query = text("""
            SELECT as_name 
            FROM info_asn 
            WHERE asn = :asn
        """)
        as_name_result = db.execute(as_name_query, {"asn": asn})
        as_name_row = as_name_result.fetchone()
        as_name = as_name_row[0] if as_name_row else f"AS{asn}"

    except Exception as e:
        app.logger.error(f"Failed to retrieve AS{asn}: {str(e)}")
        return abort(500, description="An error occurred")

    return render_template('pages/asn.html', 
                         asn=asn, 
                         as_name=as_name,
                         ipv4_count=ipv4_count,
                         ipv6_count=ipv6_count)