from flask import Blueprint, render_template, abort, current_app as app
from utils.database import PostgreSQL
from sqlalchemy import text

# Create Blueprint
asn_blueprint = Blueprint('as', __name__)

@asn_blueprint.route("/<int:asn>")
def asn(asn):
    try:
        as_name = "Example AS"

    except Exception as e:
        app.logger.error(f"Failed to retrieve AS{asn}: {str(e)}")
        return abort(500, description="An error occurred")

    return render_template('pages/asn.html', asn=asn, as_name=as_name)