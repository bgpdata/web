from flask import Blueprint, render_template, abort, current_app as app, jsonify
from utils.database import get_db, close_db
from datetime import datetime, timedelta
from utils.limiter import limiter
from utils.cache import caching
from sqlalchemy import text

# Create Blueprints
asn_blueprint = Blueprint('as', __name__)
asn_api_v1_blueprint = Blueprint('as_api_v1', __name__)

@asn_api_v1_blueprint.route('/info/<int:asn>', methods=['GET'])
@limiter.limit("100 per minute")
def api_v1_asn_info(asn):
    db = None
    try:
        db = get_db()
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

        # Get ASN Info
        asn_info_result = db.execute(asn_info_query, {"asn": asn})
        asn_info = asn_info_result.fetchone()

        return jsonify({
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
        })

    except Exception as e:
        app.logger.error("Failed to get asn info: %s", str(e), exc_info=True)
        return abort(500, description="An error occurred")
    finally:
        close_db(db)

@asn_api_v1_blueprint.route('/ipv4-count/<int:asn>', methods=['GET'])
@limiter.limit("100 per minute")
def api_v1_asn_ipv4_count(asn):
    db = None
    try:
        db = get_db()
        ipv4_query = text("""
            SELECT count(*) as count
            FROM global_ip_rib
            WHERE recv_origin_as = :asn
            AND family(prefix) = 4
            GROUP BY prefix
        """)
        
        result = db.execute(ipv4_query, {"asn": asn})
        count = sum(row[0] for row in result.fetchall())
        return jsonify({"count": count})
    except Exception as e:
        app.logger.error("Failed to get ipv4 count: %s", str(e), exc_info=True)
        return abort(500, description="An error occurred")
    finally:
        close_db(db)

@asn_api_v1_blueprint.route('/ipv6-count/<int:asn>', methods=['GET'])
@limiter.limit("100 per minute")
def api_v1_asn_ipv6_count(asn):
    db = None
    try:
        db = get_db()
        ipv6_query = text("""
            SELECT count(*) as count
            FROM global_ip_rib
            WHERE recv_origin_as = :asn
            AND family(prefix) = 6
            GROUP BY prefix
        """)
        
        result = db.execute(ipv6_query, {"asn": asn})
        count = sum(row[0] for row in result.fetchall())
        return jsonify({"count": count})
    except Exception as e:
        app.logger.error("Failed to get ipv6 count: %s", str(e), exc_info=True)
        return abort(500, description="An error occurred")
    finally:
        close_db(db)

@asn_api_v1_blueprint.route('/upstream-count/<int:asn>', methods=['GET'])
@limiter.limit("100 per minute")
def api_v1_asn_upstream_count(asn):
    db = None
    try:
        db = get_db()
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
        
        result = db.execute(upstream_query, {"asn": asn})
        count = result.scalar() or 0
        return jsonify({"count": count})
    except Exception as e:
        app.logger.error("Failed to get upstream count: %s", str(e), exc_info=True)
        return abort(500, description="An error occurred")
    finally:
        close_db(db)

@asn_api_v1_blueprint.route('/downstream-count/<int:asn>', methods=['GET'])
@limiter.limit("100 per minute")
def api_v1_asn_downstream_count(asn):
    db = None
    try:
        db = get_db()
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
        
        result = db.execute(downstream_query, {"asn": asn})
        count = result.scalar() or 0
        return jsonify({"count": count})
    except Exception as e:
        app.logger.error("Failed to get downstream count: %s", str(e), exc_info=True)
        return abort(500, description="An error occurred")
    finally:
        close_db(db)

@asn_api_v1_blueprint.route('/upstream-details/<int:asn>', methods=['GET'])
@limiter.limit("100 per minute")
def api_v1_asn_upstream_details(asn):
    db = None
    try:
        db = get_db()
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
        
        result = db.execute(upstream_details_query, {"asn": asn})
        upstream_asns = [
            {'asn': row[0], 'name': row[1] or f'AS{row[0]}'}
            for row in result.fetchall()
        ]
        return jsonify(upstream_asns)
    except Exception as e:
        app.logger.error("Failed to get upstream details: %s", str(e), exc_info=True)
        return abort(500, description="An error occurred")
    finally:
        close_db(db)

@asn_api_v1_blueprint.route('/downstream-details/<int:asn>', methods=['GET'])
@limiter.limit("100 per minute")
def api_v1_asn_downstream_details(asn):
    db = None
    try:
        db = get_db()
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
        
        result = db.execute(downstream_details_query, {"asn": asn})
        downstream_asns = [
            {'asn': row[0], 'name': row[1] or f'AS{row[0]}'}
            for row in result.fetchall()
        ]
        return jsonify(downstream_asns)
    except Exception as e:
        app.logger.error("Failed to get downstream details: %s", str(e), exc_info=True)
        return abort(500, description="An error occurred")
    finally:
        close_db(db)

@asn_api_v1_blueprint.route('/trend/<int:asn>', methods=['GET'])
@limiter.limit("100 per minute")
def api_v1_asn_trend(asn):
    db = None
    try:
        db = get_db()
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
        
        start_time = datetime.utcnow() - timedelta(hours=24)
        result = db.execute(trend_query, {
            "asn": asn,
            "start_time": start_time
        })
        
        trend_data = []
        for row in result.fetchall():
            trend_data.append({
                'time': row[0].isoformat(),
                'v4_prefixes': row[1],
                'v6_prefixes': row[2],
                'v4_with_rpki': row[3],
                'v6_with_rpki': row[4],
                'v4_with_irr': row[5],
                'v6_with_irr': row[6]
            })
        return jsonify(trend_data)
    except Exception as e:
        app.logger.error("Failed to get trend data: %s", str(e), exc_info=True)
        return abort(500, description="An error occurred")
    finally:
        close_db(db)

@asn_api_v1_blueprint.route('/prefix-aggregates/<int:asn>', methods=['GET'])
@limiter.limit("100 per minute")
def api_v1_asn_prefix_aggregates(asn):
    db = None
    try:
        db = get_db()
        aggregates_query = text("""
            SELECT r.aggregate
            FROM (
                SELECT distinct w.prefix,
                    FIRST_VALUE(a.prefix) OVER (
                        PARTITION BY w.prefix ORDER BY a.prefix ASC) as aggregate
                FROM (
                    SELECT prefix
                    FROM global_ip_rib
                    WHERE iswithdrawn = false
                        AND recv_origin_as = :asn
                        AND prefix_len > 0 and prefix_len <= 25
                    GROUP BY prefix
                ) w
                JOIN (
                    SELECT distinct prefix
                    FROM global_ip_rib
                    WHERE iswithdrawn = false 
                        AND recv_origin_as = :asn
                        AND prefix_len > 0 and prefix_len <= 25
                ) a ON (w.prefix <<= a.prefix)
            ) r
            GROUP BY r.aggregate
            ORDER BY aggregate
        """)
        
        result = db.execute(aggregates_query, {"asn": asn})
        prefixes_aggregates = [row[0] for row in result.fetchall()]
        return jsonify(prefixes_aggregates)
    except Exception as e:
        app.logger.error("Failed to get prefix aggregates: %s", str(e), exc_info=True)
        return abort(500, description="An error occurred")
    finally:
        close_db(db)

@asn_api_v1_blueprint.route('/advertised-prefixes/<int:asn>', methods=['GET'])
@limiter.limit("100 per minute")
def api_v1_asn_advertised_prefixes(asn):
    db = None
    try:
        db = get_db()
        advertised_prefixes_query = text("""
            SELECT 
                r.prefix,
                r.rpki_origin_as,
                i.origin_as as irr_origin_as,
                r.last_change,
                i.descr as irr_description,
                i.source as irr_source
            FROM (
                SELECT 
                    prefix,
                    rpki_origin_as,
                    max(timestamp) as last_change
                FROM global_ip_rib
                WHERE recv_origin_as = :asn
                GROUP BY prefix, rpki_origin_as
            ) r
            LEFT JOIN info_route i ON (i.prefix = r.prefix)
            ORDER BY r.prefix
        """)
        
        result = db.execute(advertised_prefixes_query, {"asn": asn})
        prefixes = [
            {
                'prefix': row[0],
                'rpki_origin_as': row[1],
                'irr_origin_as': row[2],
                'last_changed': row[3].isoformat() if row[3] else None,
                'irr_description': row[4],
                'irr_source': row[5]
            }
            for row in result.fetchall()
        ]
        return jsonify(prefixes)
    except Exception as e:
        app.logger.error("Failed to get advertised prefixes: %s", str(e), exc_info=True)
        return abort(500, description="An error occurred")
    finally:
        close_db(db)

@asn_blueprint.route("/<int:asn>")
#@caching(timeout=86400) # 24 hours
def asn(asn):
    return render_template('pages/asn.html', asn=asn)

# Register blueprints
def init_app(app):
    app.register_blueprint(asn_blueprint)
    app.register_blueprint(asn_api_v1_blueprint)