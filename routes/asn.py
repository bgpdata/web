from flask import Blueprint, render_template, abort, current_app as app
from utils.database import PostgreSQL
from sqlalchemy import text
from datetime import datetime, timedelta

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
        
        # Query for upstream ASNs
        upstream_query = text("""
            SELECT count(distinct asn) as count
            FROM (
                SELECT
                    as_path[array_position(as_path, :asn) - 1] as asn
                FROM base_attrs a
                WHERE as_path && ARRAY[:asn]::bigint[]
            ) d
            WHERE asn is not null and asn != :asn
        """)
        
        # Query for downstream ASNs
        downstream_query = text("""
            SELECT count(distinct asn) as count
            FROM (
                SELECT
                    as_path[(array_positions(as_path, :asn))[cardinality(array_positions(as_path, :asn))] + 1] as asn
                FROM base_attrs a
                WHERE as_path && ARRAY[:asn]::bigint[]
            ) d
            WHERE asn is not null
        """)
        
        # Query for Originating Prefix trend
        trend_query = text("""
            SELECT
                interval_time,
                v4_prefixes,
                v6_prefixes,
                v4_with_rpki,
                v6_with_rpki,
                v4_with_irr,
                v6_with_irr
            FROM stats_ip_origins
            WHERE asn = :asn
            AND interval_time >= :start_time
            ORDER BY interval_time ASC
        """)
        
        # Execute queries
        ipv4_result = db.execute(ipv4_query, {"asn": asn})
        ipv6_result = db.execute(ipv6_query, {"asn": asn})
        upstream_result = db.execute(upstream_query, {"asn": asn})
        downstream_result = db.execute(downstream_query, {"asn": asn})
        
        # Get trend data for last 24 hours
        start_time = datetime.utcnow() - timedelta(hours=24)
        trend_result = db.execute(trend_query, {
            "asn": asn,
            "start_time": start_time
        })
        
        # Process trend data
        trend_data = []
        for row in trend_result.fetchall():
            trend_data.append({
                'time': row[0].isoformat(),
                'v4_prefixes': row[1],
                'v6_prefixes': row[2],
                'v4_with_rpki': row[3],
                'v6_with_rpki': row[4],
                'v4_with_irr': row[5],
                'v6_with_irr': row[6]
            })
        
        # Calculate totals
        ipv4_count = sum(row[0] for row in ipv4_result.fetchall())
        ipv6_count = sum(row[0] for row in ipv6_result.fetchall())
        upstream_count = upstream_result.scalar() or 0
        downstream_count = downstream_result.scalar() or 0
        
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
                         ipv6_count=ipv6_count,
                         upstream_count=upstream_count,
                         downstream_count=downstream_count,
                         trend_data=trend_data)