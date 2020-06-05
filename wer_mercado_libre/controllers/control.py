# -*- coding: utf-8 -*-
import odoo
from odoo import fields, models, api, _
from odoo.addons.web.controllers.main import Home, ensure_db
from odoo import http
from odoo.http import request

class OdooMercadoLibre(http.Controller):

    @http.route('/create_order_notify', auth='public', type='http')
    def create_order_notify(self, **kw):
	print("\n\n called controller>>>")
	print("\n\n kw>>>",kw)
