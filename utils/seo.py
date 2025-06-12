from flask import current_app as app

def get_sitemap():    
    # Sitemap XML
    sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap_xml += f'<?xml-stylesheet type="text/xsl" href="{app.config["HOST"]}/sitemap.xsl"?>\n'
    sitemap_xml += '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    # Generate sitemap here...

    sitemap_xml += '</sitemapindex>'
    
    return sitemap_xml