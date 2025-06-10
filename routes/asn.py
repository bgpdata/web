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
        
        # Query for detailed upstream ASNs
        upstream_details_query = text("""
            SELECT d.asn, i.as_name as name
            FROM (
                SELECT DISTINCT
                    as_path[array_position(as_path, :asn) - 1] as asn
                FROM base_attrs a
                WHERE as_path && ARRAY[:asn]::bigint[]
            ) d
            LEFT JOIN info_asn i ON (i.asn = d.asn)
            WHERE d.asn is not null and d.asn != :asn
            ORDER BY d.asn
        """)
        
        # Query for detailed downstream ASNs
        downstream_details_query = text("""
            SELECT d.asn, i.as_name as name
            FROM (
                SELECT DISTINCT
                    as_path[(array_positions(as_path, :asn))[cardinality(array_positions(as_path, :asn))] + 1] as asn
                FROM base_attrs a
                WHERE as_path && ARRAY[:asn]::bigint[]
            ) d
            LEFT JOIN info_asn i ON (i.asn = d.asn)
            WHERE d.asn is not null
            ORDER BY d.asn
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
        
        # Query for ASN Info
        asn_info_query = text("""
            SELECT 
                as_name,
                org_id,
                org_name,
                address,
                city,
                state_prov,
                country,
                remarks,
                raw_output,
                source
            FROM info_asn
            WHERE asn = :asn
        """)
        
        # Execute queries
        ipv4_result = db.execute(ipv4_query, {"asn": asn})
        ipv6_result = db.execute(ipv6_query, {"asn": asn})
        upstream_result = db.execute(upstream_query, {"asn": asn})
        downstream_result = db.execute(downstream_query, {"asn": asn})
        
        # Get detailed upstream and downstream ASNs
        upstream_details_result = db.execute(upstream_details_query, {"asn": asn})
        downstream_details_result = db.execute(downstream_details_query, {"asn": asn})
        
        # Get trend data for last 24 hours
        start_time = datetime.utcnow() - timedelta(hours=24)
        trend_result = db.execute(trend_query, {
            "asn": asn,
            "start_time": start_time
        })
        
        # Get ASN Info
        asn_info_result = db.execute(asn_info_query, {"asn": asn})
        asn_info = asn_info_result.fetchone()
        
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
        
        # Process ASN Info
        asn_info_dict = {
            'as_name': asn_info[0] if asn_info else None,
            'org_id': asn_info[1] if asn_info else None,
            'org_name': asn_info[2] if asn_info else None,
            'address': asn_info[3] if asn_info else None,
            'city': asn_info[4] if asn_info else None,
            'state_prov': asn_info[5] if asn_info else None,
            'country': asn_info[6] if asn_info else None,
            'remarks': asn_info[7] if asn_info else None,
            'raw_output': asn_info[8] if asn_info else None,
            'source': asn_info[9] if asn_info else None
        }
        
        # Process upstream and downstream ASNs
        upstream_asns = [
            {'asn': row[0], 'name': row[1] or f'AS{row[0]}'}
            for row in upstream_details_result.fetchall()
        ]
        
        downstream_asns = [
            {'asn': row[0], 'name': row[1] or f'AS{row[0]}'}
            for row in downstream_details_result.fetchall()
        ]

    except Exception as e:
        app.logger.error(f"Failed to retrieve AS{asn}: {str(e)}")
        return abort(500, description="An error occurred")

    return render_template(
        'pages/asn.html', 
        asn=asn, 
        as_name=asn_info_dict['as_name'],
        ipv4_count=ipv4_count,
        ipv6_count=ipv6_count,
        upstream_count=upstream_count,
        downstream_count=downstream_count,
        trend_data=trend_data,
        asn_info=asn_info_dict,
        upstream_asns=upstream_asns,
        downstream_asns=downstream_asns
    )