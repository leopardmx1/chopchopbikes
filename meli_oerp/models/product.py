# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import models, fields, api, osv
from odoo.tools.translate import _

import pdb
import logging
_logger = logging.getLogger(__name__)

import requests
import base64
import mimetypes
from urllib.request import urlopen

from datetime import datetime

from .meli_oerp_config import *

from ..melisdk.meli import Meli
import string
if (not ('replace' in string.__dict__)):
    string = str

class product_template(models.Model):
    _inherit = "product.template"

    def product_template_post(self):
        product_obj = self.env['product.template']
        company = self.env.user.company_id
        warningobj = self.env['warning']

        REDIRECT_URI = company.mercadolibre_redirect_uri
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)

        if ACCESS_TOKEN=='':
            meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET)
            url_login_meli = meli.auth_url(redirect_URI=REDIRECT_URI)
            return {
                "type": "ir.actions.act_url",
                "url": url_login_meli,
                "target": "new",
            }

        _logger.info("Product Template Post")
        ret = {}
        for product in self:
            if (product.meli_pub_as_variant):
                _logger.info("Posting as variants")
                #filtrar las variantes que tengan esos atributos que definimos
                #la primera variante que cumple las condiciones es la que publicamos.
                variant_principal = False
                #las condiciones es que los atributos de la variante
                conditions_ok = True
                for variant in product.product_variant_ids:
                    if (variant._conditions_ok() ):
                        variant.meli_pub = True
                        if (variant_principal==False):
                            _logger.info("Posting variant principal:")
                            _logger.info(variant)
                            variant_principal = variant
                            product.meli_pub_principal_variant = variant
                            ret = variant.product_post()
                            if ('name' in ret):
                                return ret
                        else:
                            if (variant_principal):
                                variant.product_post_variant(variant_principal)
                    else:
                        _logger.info("No condition met for:"+variant.display_name)
                _logger.info(product.meli_pub_variant_attributes)


            else:
                for variant in product.product_variant_ids:
                    _logger.info("Variant:", variant)
                    if (variant.meli_pub):
                        _logger.info("Posting variant")
                        ret = variant.product_post()
                        if ('name' in ret):
                            return ret
                    else:
                        _logger.info("No meli_pub for:"+variant.display_name)

        return ret

    def product_template_update(self):
        product_obj = self.env['product.template']
        company = self.env.user.company_id
        warningobj = self.env['warning']
        ret = {}

        REDIRECT_URI = company.mercadolibre_redirect_uri
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)

        if ACCESS_TOKEN=='':
            meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET)
            url_login_meli = meli.auth_url(redirect_URI=REDIRECT_URI)
            return {
                "type": "ir.actions.act_url",
                "url": url_login_meli,
                "target": "new",
            }

        _logger.info("Product Template Update")

        for product in self:
            if (product.meli_pub_as_variant and product.meli_pub_principal_variant.id):
                _logger.info("Updating principal variant")
                ret = product.meli_pub_principal_variant.product_meli_get_product()
            else:
                for variant in product.product_variant_ids:
                    _logger.info("Variant:", variant)
                    if (variant.meli_pub):
                        _logger.info("Updating variant")
                        ret = variant.product_meli_get_product()
                        if ('name' in ret):
                            return ret

        return ret

    def _variations(self):
        variations = False
        for product_tmpl in self:
            for variant in product_tmpl.product_variant_ids:
                if ( variant._conditions_ok() ):
                    variant.meli_pub = True
                    var = variant._combination()
                    if (var):
                        if (variations==False):
                            variations = []
                        variations.append(var)

        return variations


    def product_template_stats(self):

        _pubs = ""
        _stats = ""
        for product in self:
            for variant in product.product_variant_ids:
                if (variant.meli_pub):
                    if ( (variant.meli_status=="active" or variant.meli_status=="paused") and variant.meli_id):
                        if (len(_pubs)):
                            _pubs = _pubs + "|" + variant.meli_id + ":" + variant.meli_status
                        else:
                            _pubs = variant.meli_id + ":" + variant.meli_status

                        if (variant.meli_status=="active"):
                            _stats = "active"

                        if (_stats == "" and variant.meli_status=="paused"):
                            _stats = "paused"

            product.meli_publications = _pubs
            product.meli_variants_status = _stats

        return {}


    def action_meli_pause(self):
        for product in self:
            for variant in product.product_variant_ids:
                if (variant.meli_pub):
                    variant.product_meli_status_pause()
        return {}


    def action_meli_activate(self):
        for product in self:
            for variant in product.product_variant_ids:
                if (variant.meli_pub):
                    variant.product_meli_status_active()
        return {}


    def action_meli_close(self):
        for product in self:
            for variant in product.product_variant_ids:
                if (variant.meli_pub):
                    variant.product_meli_status_close()
        return {}


    def action_meli_delete(self):
        for product in self:
            for variant in product.product_variant_ids:
                if (variant.meli_pub):
                    variant.product_meli_delete()
        return {}

    @api.onchange('meli_pub') # if these fields are changed, call method
    def change_meli_pub(self):
        _logger.info("onchange meli_pub:"+str(self.meli_pub))
        product = self._origin
        for variant in product.product_variant_ids:
            _logger.info("onchange meli_pub variant before::"+str(variant.meli_pub))
            variant.write({'meli_pub':self.meli_pub})


    name = fields.Char('Name', size=128, required=True, translate=False, index=True)
    meli_title = fields.Char(string='Nombre del producto en Mercado Libre',size=256)
    meli_description = fields.Text(string='Descripción')
    meli_category = fields.Many2one("mercadolibre.category","Categoría de MercadoLibre")
    meli_buying_mode = fields.Selection( [("buy_it_now","Compre ahora"),("classified","Clasificado")], string='Método de compra')
    meli_price = fields.Char(string='Precio de venta', size=128)
    meli_currency = fields.Selection([("ARS","Peso Argentino (ARS)"),
    ("MXN","Peso Mexicano (MXN)"),
    ("COP","Peso Colombiano (COP)"),
    ("PEN","Sol Peruano (PEN)"),
    ("BOB","Boliviano (BOB)"),
    ("BRL","Real (BRL)"),
    ("CLP","Peso Chileno (CLP)")],
                                    string='Moneda')
    meli_condition = fields.Selection([ ("new", "Nuevo"),
                                        ("used", "Usado"),
                                        ("not_specified","No especificado")],
                                        'Condición del producto')
    meli_dimensions = fields.Char( string="Dimensiones del producto", size=128)
    meli_pub = fields.Boolean('Meli Publication',help='MELI Product',index=True)
    meli_master = fields.Boolean('Meli Producto Maestro',help='MELI Product Maestro',index=True)
    meli_warranty = fields.Char(string='Garantía', size=256)
    meli_listing_type = fields.Selection([("free","Libre"),("bronze","Bronce"),("silver","Plata"),("gold","Oro"),("gold_premium","Gold Premium"),("gold_special","Gold Special/Clásica"),("gold_pro","Oro Pro")], string='Tipo de lista')
    meli_attributes = fields.Text(string='Atributos')

    meli_publications = fields.Text(compute=product_template_stats,string='Publicaciones en ML')
    meli_variants_status = fields.Text(compute=product_template_stats,string='Meli Variant Status')

    meli_pub_as_variant = fields.Boolean('Publicar variantes como variantes en ML',help='Publicar variantes como variantes de la misma publicación, no como publicaciones independientes.')
    meli_pub_variant_attributes = fields.Many2many('product.template.attribute.line', string='Atributos a publicar en ML',help='Seleccionar los atributos a publicar')
    meli_pub_principal_variant = fields.Many2one( 'product.product',string='Variante principal',help='Variante principal')

    meli_model = fields.Char(string="Modelo [meli]",size=256)
    meli_brand = fields.Char(string="Marca [meli]",size=256)
    meli_stock = fields.Float(string="Cantidad inicial (Solo para actualizar stock)[meli]")

    meli_product_bom = fields.Char(string="Lista de materiales (skux:1,skuy:2,skuz:4) [meli]")

    meli_product_price = fields.Float(string="Precio [meli]")
    meli_product_cost = fields.Float(string="Costo del proveedor [meli]")
    meli_product_code = fields.Char(string="Codigo de proveedor [meli]")
    meli_product_supplier = fields.Char(string="Proveedor del producto [meli]")

product_template()

class product_image(models.Model):
    _inherit = "product.image"

    meli_imagen_id = fields.Char(string='Imagen Id',index=True)
    meli_imagen_link = fields.Char(string='Imagen Link')
    meli_imagen_size = fields.Char(string='Size')
    meli_imagen_max_size = fields.Char(string='Max Size')
    meli_imagen_bytes = fields.Integer(string='Size bytes')
    meli_pub = fields.Boolean(string='Publicar en ML')

product_image()

class product_product(models.Model):

    _inherit = "product.product"

    #
    @api.onchange('lst_price') # if these fields are changed, call method
    def check_change_price(self):
        # GUS
        #pdb.set_trace();
        #pricelists = self.env['product.pricelist'].search([])
        #if pricelists:
        #    if pricelists.id:
        #        pricelist = pricelists.id
        #    else:
        #        pricelist = pricelists[0].id
        self.meli_price = str(self.lst_price)
        #res = {}
        #for id in self:
        #    res[id] = self.lst_price
        #return res

    def _meli_set_price( self, product_template, meli_price ):
        company = self.env.user.company_id
        ml_price_converted = meli_price
        if (product_template.taxes_id):
            txtotal = 0
            _logger.info("Adjust taxes")
            for txid in product_template.taxes_id:
                if (txid.type_tax_use=="sale"):
                    txtotal = txtotal + txid.amount
                    _logger.info(txid.amount)
            if (txtotal>0):
                _logger.info("Tx Total:"+str(txtotal)+" to Price:"+str(ml_price_converted))
                ml_price_converted = meli_price / (1.0 + txtotal*0.01)
                _logger.info("Price converted:"+str(ml_price_converted))

        product_template.write({'lst_price': ml_price_converted})

    def _meli_set_category( self, product_template, category_id ):

        product = self
        company = self.env.user.company_id
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token
        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)

        mlcatid = False
        www_cat_id = False

        ml_cat = self.env['mercadolibre.category'].search([('meli_category_id','=',category_id)])
        ml_cat_id = ml_cat.id
        if (ml_cat_id):
            #_logger.info( "category exists!" + str(ml_cat_id) )
            mlcatid = ml_cat_id
            www_cat_id = ml_cat.public_category_id
        else:
            #_logger.info( "Creating category: " + str(category_id) )
            #https://api.mercadolibre.com/categories/MLA1743
            response_cat = meli.get("/categories/"+str(category_id), {'access_token':meli.access_token})
            rjson_cat = response_cat.json()
            #_logger.info( "category:" + str(rjson_cat) )
            fullname = ""
            if ("path_from_root" in rjson_cat):
                path_from_root = rjson_cat["path_from_root"]
                p_id = False
                #pdb.set_trace()
                for path in path_from_root:
                    fullname = fullname + "/" + path["name"]

                    if (company.mercadolibre_create_website_categories):
                        www_cats = self.env['product.public.category']
                        if www_cats!=False:
                            www_cat_id = www_cats.search([('name','=',path["name"])]).id
                            if www_cat_id==False:
                                www_cat_fields = {
                                  'name': path["name"],
                                  #'parent_id': p_id,
                                  #'sequence': 1
                                }
                                if p_id:
                                    www_cat_fields['parent_id'] = p_id
                                www_cat_id = www_cats.create((www_cat_fields)).id
                                if www_cat_id:
                                    _logger.info("Website Category created:"+fullname)

                            p_id = www_cat_id

            #fullname = fullname + "/" + rjson_cat['name']
            #_logger.info( "category fullname:" + fullname )
            cat_fields = {
                'name': fullname,
                'meli_category_id': ''+str(category_id),
                'public_category_id': 0,
            }

            if www_cat_id:
                p_cat_id = www_cats.search([('id','=',www_cat_id)])
                cat_fields['public_category_id'] = www_cat_id
                #cat_fields['public_category'] = p_cat_id

            ml_cat_id = self.env['mercadolibre.category'].create((cat_fields)).id
            if (ml_cat_id):
                mlcatid = ml_cat_id

        if (mlcatid):
            product.write( {'meli_category': mlcatid} )
            product_template.write( {'meli_category': mlcatid} )

        if www_cat_id!=False:
            #assign
            product_template.public_categ_ids = [(4,www_cat_id)]

    def _meli_set_images( self, product_template, pictures ):
        company = self.env.user.company_id
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)

        try:
            product = self
            thumbnail_url = pictures[0]['url']
            image = urlopen(thumbnail_url).read()
            image_base64 = base64.encodestring(image)
            product.image_1920 = image_base64

            if (len(pictures)>1):
                #complete product images:
                #delete all images...
                _logger.info("Importing all images...")
                #_logger.info(pictures)
                for ix in range(1,len(pictures)-1):
                    pic = pictures[ix]
                    bin_updating = False
                    resimage = meli.get("/pictures/"+pic['id'], {'access_token':meli.access_token})
                    imgjson = resimage.json()

                    thumbnail_url = pic['secure_url']
                    if 'error' in imgjson:
                        pass;
                    else:
                        if (len(imgjson['variations'])>0):
                            thumbnail_url = imgjson['variations'][0]['secure_url']

                    image = urlopen(thumbnail_url).read()
                    image_base64 = base64.encodestring(image)
                    meli_imagen_bytes = len(image)
                    pimage = False
                    pimg_fields = {
                        'name': thumbnail_url+' - '+pic["size"]+' - '+pic["max_size"],
                        'meli_imagen_id': pic["id"],
                        'meli_imagen_link': thumbnail_url,
                        'meli_imagen_size': pic["size"],
                        'meli_imagen_max_size': pic["max_size"],
                        'meli_imagen_bytes': meli_imagen_bytes,
                        'product_tmpl_id': product_template.id,
                        'meli_pub': True
                    }
                    #_logger.info(pimg_fields)
                    if (product.product_variant_image_ids):
                        pimage = self.env["product.image"].search([('meli_imagen_id','=',pic["id"]),('product_tmpl_id','=',product_template.id)])
                        #_logger.info(pimage)
                        if (pimage and pimage.image):
                            imagebin = base64.b64decode( pimage.image )
                            bin_diff = meli_imagen_bytes - len(imagebin)
                            _logger.info("Image:"+str(len(imagebin))+" vs URLImage:"+str(meli_imagen_bytes)+" diff:"+str(bin_diff) )
                            bin_updating = (abs(bin_diff)>0)

                    if (pimage==False or len(pimage)==0):
                        _logger.info("Creating new image")
                        bin_updating = True
                        pimage = self.env["product.image"].create(pimg_fields)

                    if (pimage):
                        pimage.write(pimg_fields)
                        if (bin_updating):
                            _logger.info("Updating image data.")
                            _logger.info("Image:"+str(meli_imagen_bytes) )
                            pimage.image_1920 = image_base64
        except Exception as e:
            _logger.info("_meli_set_images Exception")
            _logger.info(e, exc_info=True)

    def product_meli_get_product( self ):
        company = self.env.user.company_id
        product_obj = self.env['product.product']
        uomobj = self.env['uom.uom']
        #pdb.set_trace()
        product = self

        _logger.info("product_meli_get_product")
        _logger.info(product.default_code)

        product_template_obj = self.env['product.template']
        product_template = product_template_obj.browse(product.product_tmpl_id.id)

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)

        try:
            response = meli.get("/items/"+product.meli_id, {'access_token':meli.access_token})
            #_logger.info(response)
            rjson = response.json()
            #_logger.info(rjson)
        except IOError as e:
            _logger.info( "I/O error({0}): {1}".format(e.errno, e.strerror) )
            return {}
        except:
            _logger.info( "Rare error" )
            return {}



        des = ''
        desplain = ''
        vid = ''
        if 'error' in rjson:
            return {}

        #if "content" in response:
        #    _logger.info(response.content)
        #    _logger.info( "product_meli_get_product > response.content: " + response.content )

        #TODO: traer la descripcion: con
        #https://api.mercadolibre.com/items/{ITEM_ID}/description?access_token=$ACCESS_TOKEN
        if rjson and rjson['descriptions']:
            response2 = meli.get("/items/"+product.meli_id+"/description", {'access_token':meli.access_token})
            rjson2 = response2.json()
            if 'text' in rjson2:
               des = rjson2['text']
            if 'plain_text' in rjson2:
               desplain = rjson2['plain_text']
            if (len(des)>0):
                desplain = des

        #TODO: verificar q es un video
        if rjson['video_id']:
            vid = ''

        #TODO: traer las imagenes
        #TODO:
        pictures = rjson['pictures']
        if pictures and len(pictures):
            product._meli_set_images(product_template, pictures)

        #categories
        product._meli_set_category( product_template, rjson['category_id'] )

        imagen_id = ''
        meli_dim_str = ''
        if ('dimensions' in rjson):
            if (rjson['dimensions']):
                meli_dim_str = rjson['dimensions']

        if ('pictures' in rjson):
            if (len(rjson['pictures'])>0):
                imagen_id = rjson['pictures'][0]['id']

        product._meli_set_price( product_template, rjson['price'] )

        meli_fields = {
            'name': rjson['title'].encode("utf-8"),
            #'default_code': rjson['id'],
            'meli_imagen_id': imagen_id,
            'meli_post_required': True,
            'meli_id': rjson['id'],
            'meli_permalink': rjson['permalink'],
            'meli_title': rjson['title'].encode("utf-8"),
            'meli_description': desplain,
            'meli_listing_type': rjson['listing_type_id'],
            'meli_buying_mode':rjson['buying_mode'],
            'meli_price': str(rjson['price']),
            'meli_price_fixed': True,
            'meli_currency': rjson['currency_id'],
            'meli_condition': rjson['condition'],
            'meli_available_quantity': rjson['available_quantity'],
            'meli_warranty': rjson['warranty'],
            'meli_imagen_link': rjson['thumbnail'],
            'meli_video': str(vid),
            'meli_dimensions': meli_dim_str,
        }

        tmpl_fields = {
          'name': meli_fields["name"],
          'description_sale': desplain,
          #'name': str(rjson['id']),
          #'lst_price': ml_price_convert,
          'meli_title': meli_fields["meli_title"],
          'meli_description': meli_fields["meli_description"],
          #'meli_category': meli_fields["meli_category"],
          'meli_listing_type': meli_fields["meli_listing_type"],
          'meli_buying_mode': meli_fields["meli_buying_mode"],
          'meli_price': meli_fields["meli_price"],
          'meli_currency': meli_fields["meli_currency"],
          'meli_condition': meli_fields["meli_condition"],
          'meli_warranty': meli_fields["meli_warranty"],
          'meli_dimensions': meli_fields["meli_dimensions"]
        }

        if (product.name and not company.mercadolibre_overwrite_variant):
            del meli_fields['name']
        if (product_template.name and not company.mercadolibre_overwrite_template):
            del tmpl_fields['name']
        if (product_template.description_sale and not company.mercadolibre_overwrite_template):
            del tmpl_fields['description_sale']

        product.write( meli_fields )
        product_template.write( tmpl_fields )

        if (rjson['available_quantity']>0):
            product_template.website_published = True
        else:
            product_template.website_published = False

        posting_fields = {
            'posting_date': str(datetime.now()),
            'meli_id':rjson['id'],
            'product_id':product.id,
            'name': 'Post (ML): ' + product.meli_title
        }

        posting = self.env['mercadolibre.posting'].search([('meli_id','=',rjson['id'])])
        posting_id = posting.id

        if not posting_id:
            posting = self.env['mercadolibre.posting'].create((posting_fields))
            posting_id = posting.id
            if (posting):
                posting.posting_query_questions()
        else:
            posting.write({'product_id':product.id })
            posting.posting_query_questions()


        b_search_nonfree_ship = False
        if ('shipping' in rjson):
            att_shipping = {
                'name': 'Con envío',
                'create_variant': 'no_variant'
            }
            if ('variations' in rjson):
                #_logger.info("has variations")
                pass
            else:
                rjson['variations'] = []

            if ('free_methods' in rjson['shipping']):
                att_shipping['value_name'] = 'Sí'
                #buscar referencia del template correspondiente
                b_search_nonfree_ship = True
            else:
                att_shipping['value_name'] = 'No'

            rjson['variations'].append({'attribute_combinations': [ att_shipping ]})

        #_logger.info(rjson['variations'])
        published_att_variants = False
        if ('variations' in rjson):
            #recorrer los variations>attribute_combinations y agregarlos como atributos de las variantes
            #_logger.info(rjson['variations'])
            vindex = -1
            for variation in rjson['variations']:
                vindex = vindex + 1
                if ('attribute_combinations' in variation):
                    _attcomb_str = ""
                    rjson['variations'][vindex]["default_code"] = ""
                    for attcomb in variation['attribute_combinations']:
                        namecap = attcomb['name']
                        if (len(namecap)):
                            att = {
                                'name': namecap,
                                'value_name': attcomb['value_name'],
                                'create_variant': 'always',
                                'att_id': False
                            }
                            if ('id' in attcomb):
                                if (attcomb["id"]):
                                    if (len(attcomb["id"])):
                                        att["att_id"] = attcomb["id"]
                            if (att["att_id"]==False):
                                namecap = namecap.strip()
                                namecap = namecap[0].upper()+namecap[1:]
                                att["name"] = namecap
                            if ('create_variant' in attcomb):
                                att['create_variant'] = attcomb['create_variant']
                            else:
                                rjson['variations'][vindex]["default_code"] = rjson['variations'][vindex]["default_code"]+namecap+":"+attcomb['value_name']+";"
                            #_logger.info(att)
                            if (att["att_id"]):
                                # ML Attribute , we could search first...
                                #attribute = self.env['product.attribute'].search([('name','=',att['name']),('meli_default_id_attribute','!=',False)])
                                #if (len(attribute)==0):
                                # ningun atributo con ese nombre asociado
                                ml_attribute = self.env['mercadolibre.category.attribute'].search([('att_id','=',att['att_id'])])
                                attribute = []
                                if (len(ml_attribute)==1):
                                    attribute = self.env['product.attribute'].search([('meli_default_id_attribute','=',ml_attribute.id)])
                                if (len(attribute)==0):
                                    attribute = self.env['product.attribute'].search([('name','=',att['name'])])
                            else:
                                #customizado
                                #_logger.info("Atributo customizado:"+str(namecap))
                                attribute = self.env['product.attribute'].search([('name','=',namecap),('meli_default_id_attribute','=',False)])
                                _logger.info(attribute)

                                if (attcomb['name']!=namecap):
                                    attribute_duplicates = self.env['product.attribute'].search([('name','=',attcomb['name']),('meli_default_id_attribute','=',False)])
                                    _logger.info("attribute_duplicates:")
                                    _logger.info(attribute_duplicates)
                                    if (len(attribute_duplicates)>=1):
                                        #archive
                                        _logger.info("attribute_duplicates:",len(attribute_duplicates))
                                        for attdup in attribute_duplicates:
                                            _logger.info("duplicate:"+attdup.name+":"+str(attdup.id))
                                            attdup_line =  self.env['product.template.attribute.line'].search([('attribute_id','=',attdup.id),('product_tmpl_id','=',product_template.id)])
                                            if (len(attdup_line)):
                                                for attline in attdup_line:
                                                    attline.unlink()
                                            #attdup.unlink()

                                #buscar en las lineas existentes
                                if (len(attribute)>1):
                                    att_line = self.env['product.template.attribute.line'].search([('attribute_id','in',attribute.ids),('product_tmpl_id','=',product_template.id)])
                                    _logger.info(att_line)
                                    if (len(att_line)):
                                        _logger.info("Atributo ya asignado!")
                                        attribute = att_line.attribute_id

                            attribute_id = False
                            if (len(attribute)==1):
                                attribute_id = attribute.id
                            elif (len(attribute)>1):
                                _logger.error("Attributes duplicated names!!!")
                                attribute_id = attribute[0].id


                            #_logger.info(attribute_id)
                            if attribute_id:
                                #_logger.info(attribute_id)
                                pass
                            else:
                                #_logger.info("Creating attribute:")
                                attribute_id = self.env['product.attribute'].create({ 'name': att['name'],'create_variant': att['create_variant'] }).id

                            if (att['create_variant']=='always'):
                                #_logger.info("published_att_variants")
                                published_att_variants = True

                            if (attribute_id):
                                #_logger.info("Publishing attribute")
                                attribute_value_id = self.env['product.attribute.value'].search([('attribute_id','=',attribute_id),('name','=',att['value_name'])]).id
                                #_logger.info(_logger.info(attribute_id))
                                if attribute_value_id:
                                    #_logger.info(attribute_value_id)
                                    pass
                                else:
                                    _logger.info("Creating attribute value:"+str(att))
                                    if (att['value_name']!=None):
                                        attribute_value_id = self.env['product.attribute.value'].create({'attribute_id': attribute_id,'name': att['value_name']}).id

                                if (attribute_value_id):
                                    #_logger.info("attribute_value_id:")
                                    #_logger.info(attribute_value_id)
                                    #search for line ids.
                                    attribute_line =  self.env['product.template.attribute.line'].search([('attribute_id','=',attribute_id),('product_tmpl_id','=',product_template.id)])
                                    #_logger.info(attribute_line)
                                    if (attribute_line and attribute_line.id):
                                        #_logger.info(attribute_line)
                                        pass
                                    else:
                                        #_logger.info("Creating att line id:")
                                        attribute_line =  self.env['product.template.attribute.line'].create( { 'attribute_id': attribute_id,'product_tmpl_id': product_template.id, 'value_ids': [(4,attribute_value_id)] } )

                                    if (attribute_line):
                                        #_logger.info("Check attribute line values id.")
                                        #_logger.info("attribute_line:")
                                        #_logger.info(attribute_line)
                                        if (attribute_line.value_ids):
                                            #check if values
                                            #_logger.info("Has value ids:")
                                            #_logger.info(attribute_line.value_ids.ids)
                                            if (attribute_value_id in attribute_line.value_ids.ids):
                                                #_logger.info(attribute_line.value_ids.ids)
                                                pass
                                            else:
                                                #_logger.info("Adding value id")
                                                attribute_line.value_ids = [(4,attribute_value_id)]
                                        else:
                                            #_logger.info("Adding value id")
                                            attribute_line.value_ids = [(4,attribute_value_id)]

        #_logger.info("product_uom_id")
        product_uom_id = uomobj.search([('name','=','Unidad(es)')])
        if (product_uom_id.id==False):
            product_uom_id = 1
        else:
            product_uom_id = product_uom_id.id

        _product_id = product.id
        _product_name = product.name
        _product_meli_id = product.meli_id

        #this write pull the trigger for create_variant_ids()...
        #_logger.info("rewrite to create variants")
        product_template.write({ 'attribute_line_ids': product_template.attribute_line_ids  })
        #_logger.info("published_att_variants:"+str(published_att_variants))
        if (published_att_variants):
            product_template.meli_pub_as_variant = True

            #_logger.info("Auto check product.template meli attributes to publish")
            for line in  product_template.attribute_line_ids:
                if (line.id not in product_template.meli_pub_variant_attributes.ids):
                    if (line.attribute_id.create_variant):
                        product_template.meli_pub_variant_attributes = [(4,line.id)]

            #_logger.info("check variants")
            for variant in product_template.product_variant_ids:
                #_logger.info("Created variant:")
                #_logger.info(variant)
                variant.meli_pub = product_template.meli_pub
                variant.meli_id = rjson['id']
                #variant.default_code = rjson['id']
                #variant.name = rjson['title'].encode("utf-8")
                has_sku = False

                _v_default_code = ""
                for att in variant.attribute_value_ids:
                    _v_default_code = _v_default_code + att.attribute_id.name+':'+att.name+';'
                #_logger.info("_v_default_code: " + _v_default_code)
                for variation in rjson['variations']:
                    #_logger.info(variation)
                    #_logger.info("variation[default_code]: " + variation["default_code"])
                    if (len(variation["default_code"]) and (variation["default_code"] in _v_default_code)):
                        if ("seller_custom_field" in variation):
                            #_logger.info("has_sku")
                            #_logger.info(variation["seller_custom_field"])
                            variant.default_code = variation["seller_custom_field"]
                            variant.meli_id_variation = variation["id"]
                            has_sku = True
                        else:
                            variant.default_code = variant.meli_id+'-'+_v_default_code
                        variant.meli_available_quantity = variation["available_quantity"]

                if (has_sku):
                    variant.set_bom()

                #_logger.info('meli_pub_principal_variant')
                #_logger.info(product_template.meli_pub_principal_variant.id)
                if (product_template.meli_pub_principal_variant.id is False):
                    #_logger.info("meli_pub_principal_variant set!")
                    product_template.meli_pub_principal_variant = variant
                    product = variant

                if (_product_id==variant.id):
                    product = variant
        else:
            #NO TIENE variantes pero tiene SKU
            if ("seller_custom_field" in rjson):
                if (rjson["seller_custom_field"]):
                    product.default_code = rjson["seller_custom_field"]
                product.set_bom()


        if (company.mercadolibre_update_local_stock):
            product_template.type = 'product'

            if (len(product_template.product_variant_ids)):
                for variant in product_template.product_variant_ids:

                    _product_id = variant.id
                    _product_name = variant.name
                    _product_meli_id = variant.meli_id

                    if (variant.meli_available_quantity != variant.virtual_available):
                        variant.product_update_stock(variant.meli_available_quantity)
            else:
                product.product_update_stock(product.meli_available_quantity)

        #assign envio/sin envio
        #si es (Con envio: Sí): asigna el meli_default_stock_product al producto sin envio (Con evio: No)
        if (b_search_nonfree_ship):
            ptemp_nfree = False
            ptpl_same_name = self.env['product.template'].search([('name','=',product_template.name),('id','!=',product_template.id)])
            #_logger.info("ptpl_same_name:"+product_template.name)
            #_logger.info(ptpl_same_name)
            if len(ptpl_same_name):
                for ptemp in ptpl_same_name:
                    #check if sin envio
                    #_logger.info(ptemp.name)
                    for line in ptemp.attribute_line_ids:
                        #_logger.info(line.attribute_id.name)
                        #_logger.info(line.value_ids)
                        es_con_envio = False
                        try:
                            line.attribute_id.name.index('Con env')
                            es_con_envio = True
                        except ValueError:
                            pass
                            #_logger.info("not con envio")
                        if (es_con_envio==True):
                            for att in line.value_ids:
                                #_logger.info(att.name)
                                if (att.name=='No'):
                                    #_logger.info("Founded")
                                    if (ptemp.meli_pub_principal_variant.id):
                                        #_logger.info("has meli_pub_principal_variant!")
                                        ptemp_nfree = ptemp.meli_pub_principal_variant
                                        if (ptemp_nfree.meli_default_stock_product):
                                            #_logger.info("has meli_default_stock_product!!!")
                                            ptemp_nfree = ptemp_nfree.meli_default_stock_product
                                    else:
                                        if (ptemp.product_variant_ids):
                                            if (len(ptemp.product_variant_ids)):
                                                ptemp_nfree = ptemp.product_variant_ids[0]

            if (ptemp_nfree):
                #_logger.info("Founded ptemp_nfree, assign to all variants")
                for variant in product_template.product_variant_ids:
                    variant.meli_default_stock_product = ptemp_nfree

        if ('attributes' in rjson):
            if (len(rjson['attributes']) and 1==1):
                for att in rjson['attributes']:
                    try:
                        _logger.info(att)
                        ml_attribute = self.env['mercadolibre.category.attribute'].search([('att_id','=',att['id'])])
                        attribute = []

                        if (ml_attribute and ml_attribute.id):
                            #_logger.info(ml_attribute)
                            attribute = self.env['product.attribute'].search([('meli_default_id_attribute','=',ml_attribute.id)])
                            #_logger.info(attribute)

                        if (len(attribute) and attribute.id):
                            attribute_id = attribute.id
                            attribute_value_id = self.env['product.attribute.value'].search([('attribute_id','=',attribute_id), ('name','=',att['value_name'])]).id
                            #_logger.info(_logger.info(attribute_id))
                            if attribute_value_id:
                                #_logger.info(attribute_value_id)
                                pass
                            else:
                                _logger.info("Creating attribute value:")
                                _logger.info(att)
                                if (att['value_name']!=None):
                                    attribute_value_id = self.env['product.attribute.value'].create({'attribute_id': attribute_id, 'name': att['value_name'] }).id

                            if (attribute_value_id):
                                attribute_line =  self.env['product.template.attribute.line'].search([('attribute_id','=',attribute_id),('product_tmpl_id','=',product_template.id)])
                                if (attribute_line and attribute_line.id):
                                    #_logger.info(attribute_line)
                                    pass
                                else:
                                    #_logger.info("Creating att line id:")
                                    attribute_line =  self.env['product.template.attribute.line'].create( { 'attribute_id': attribute_id, 'product_tmpl_id': product_template.id, 'value_ids': [(4,attribute_value_id)] } )

                                if (attribute_line):
                                    #_logger.info("Check attribute line values id.")
                                    #_logger.info("attribute_line:")
                                    #_logger.info(attribute_line)
                                    if (attribute_line.value_ids):
                                        #check if values
                                        #_logger.info("Has value ids:")
                                        #_logger.info(attribute_line.value_ids.ids)
                                        if (attribute_value_id in attribute_line.value_ids.ids):
                                            #_logger.info(attribute_line.value_ids.ids)
                                            pass
                                        else:
                                            #_logger.info("Adding value id")
                                            attribute_line.value_ids = [(4,attribute_value_id)]
                                    else:
                                        #_logger.info("Adding value id")
                                        attribute_line.value_ids = [(4,attribute_value_id)]
                    except Exception as e:
                        _logger.info("Attributes exception:")
                        _logger.info(e, exc_info=True)

        return {}

    def set_bom(self, has_sku=True):
        #generar lista de materiales si y ssi existe un producto CON ENVIO/SIN ENVIO
        # CONDICION: tener un
        variant = self
        product_template = self.product_tmpl_id
        uomobj = self.env['uom.uom']
        if (not ("mrp.bom" in self.env)):
            _logger.info("mrp.bom not found")
            _logger.error("Must install Manufacturing Module")
            return {}
        bom = self.env["mrp.bom"]
        bom_l = self.env["mrp.bom.line"]
        #_logger.info("set bom: " + str(has_sku))

        product_uom_id = uomobj.search([('name','=','Unidad(es)')])
        if (product_uom_id.id==False):
            product_uom_id = 1
        else:
            product_uom_id = product_uom_id.id

        if (has_sku and variant.default_code and len(variant.default_code)>2):
            E_S = variant.default_code[-2:]
            #_logger.info("check sin envio code")
            #_logger.info(E_S)
            if (E_S=="CE" or E_S=="SE"):
                #buscamos el sin envio
                #_logger.info("buscamos sin envio")
                sin_envio = variant.default_code[0:-2] + 'SE'
                #_logger.info(sin_envio)
                #pse = self.env["product.product"].search([('default_code','=',sin_envio),('name','=',variant.name)])
                pse = self.env["product.product"].search([  ('default_code','=',sin_envio),
                                                            ('product_tmpl_id','!=',product_template.id),
                                                            ('meli_master','!=',False)])
                if (len(pse)==0):
                    pse = self.env["product.product"].search([  ('default_code','=',sin_envio),
                                                                ('product_tmpl_id','!=',product_template.id)])

                if (len(pse)>1):
                    #pse = pse[0]
                    pse_master = False
                    pmin = 10000
                    for ps in pse:
                        if ps.categ_id:
                            _logger.info("cat/name: ")
                            _logger.info(ps.categ_id.display_name)
                            _logger.info(ps.display_name)
                            #if (ps.categ_id.parent_id==False):
                            _pmin = len(ps.categ_id.display_name)+len(ps.display_name)
                            if (_pmin<pmin):
                                pmin = _pmin
                                pse_master = ps
                                _logger.info("Seleccionado!:" + str(ps.display_name))
                    pse = pse_master

                if (pse):
                    #_logger.info("SE encontrado: " + sin_envio)
                    # igualar stock
                    variant.meli_available_quantity = pse.meli_available_quantity
                    #_logger.info("SE meli_available_quantity: " + str(pse.meli_available_quantity))
                    bom_list = bom.search([('product_tmpl_id','=',product_template.id),('product_id','=',variant.id)])
                    if (bom_list):
                        #_logger.info("bom_list:")
                        #_logger.info(bom_list)
                        pass
                    else:
                        #lista de materiales: KIT (phantom)
                        bl_fields = {
                            "product_tmpl_id": product_template.id,
                            "product_id": variant.id,
                            "type": "phantom",
                            "product_qty": 1,
                            "product_uom_id": product_uom_id
                        }
                        bom_list = bom.create(bl_fields)
                        #_logger.info("bom_list created:")
                        #_logger.info(bom_list)

                    if (bom_list):
                        #check line ids
                        lineids = bom_l.search([('bom_id','=',bom_list.id)])
                        if (lineids):
                            #check if lineids is ok
                            bomline_fields = {
                                'product_id': pse.id
                            }
                            lineids.write(bomline_fields)
                        else:
                            bomline_fields = {
                                'bom_id': bom_list.id,
                                'product_id': pse.id,
                                'product_uom_id': product_uom_id,
                                'product_qty': 1.0
                            }
                            lineids = bom_l.create(bomline_fields)
                            #_logger.info("bom_list line created")
                        variant.meli_default_stock_product = pse
                else:
                    _logger.info("SE no existe?")


    def product_meli_login(self ):

        company = self.env.user.company_id

        REDIRECT_URI = company.mercadolibre_redirect_uri
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET)

        url_login_meli = meli.auth_url(redirect_URI=REDIRECT_URI)

        return {
	        "type": "ir.actions.act_url",
	        "url": url_login_meli,
	        "target": "new",
        }

    def product_meli_status_close( self ):
        company = self.env.user.company_id
        product_obj = self.env['product.product']
        product = self

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)

        response = meli.put("/items/"+product.meli_id, { 'status': 'closed' }, {'access_token':meli.access_token})

        return {}

    def product_meli_status_pause( self ):
        company = self.env.user.company_id
        product_obj = self.env['product.product']
        product = self

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)

        response = meli.put("/items/"+product.meli_id, { 'status': 'paused' }, {'access_token':meli.access_token})

        return {}

    def product_meli_status_active( self ):
        company = self.env.user.company_id
        product_obj = self.env['product.product']
        product = self

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)

        response = meli.put("/items/"+product.meli_id, { 'status': 'active' }, {'access_token':meli.access_token})

        return {}

    def product_meli_delete( self ):

        company = self.env.user.company_id
        product_obj = self.env['product.product']
        product = self

        if product.meli_status!='closed':
            self.product_meli_status_close()

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)

        response = meli.put("/items/"+product.meli_id, { 'deleted': 'true' }, {'access_token':meli.access_token})

        #_logger.info( "product_meli_delete: " + response.content )
        rjson = response.json()
        ML_status = rjson["status"]
        if "error" in rjson:
            ML_status = rjson["error"]
        if "sub_status" in rjson:
            if len(rjson["sub_status"]) and rjson["sub_status"][0]=='deleted':
                product.write({ 'meli_id': '' })

        return {}

    def product_meli_upload_image( self ):

        company = self.env.user.company_id

        product_obj = self.env['product.product']
        product = self

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        #
        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)

        if product.image_1920==None or product.image_1920==False:
            return { 'status': 'error', 'message': 'no image to upload' }

        imagebin = base64.b64decode(product.image_1920)
        imageb64 = product.image_1920
        files = { 'file': ('image.jpg', imagebin, "image/jpeg"), }
        response = meli.upload("/pictures", files, { 'access_token': meli.access_token } )

        rjson = response.json()
        if ("error" in rjson):
            #raise osv.except_osv( _('MELI WARNING'), _('No se pudo cargar la imagen en MELI! Error: %s , Mensaje: %s, Status: %s') % ( rjson["error"], rjson["message"],rjson["status"],))
            return rjson
            #return { 'status': 'error', 'message': 'not uploaded'}

        _logger.info( rjson )

        if ("id" in rjson):
            #guardar id
            product.write( { "meli_imagen_id": rjson["id"], "meli_imagen_link": rjson["variations"][0]["url"] })
            #asociar imagen a producto
            if product.meli_id:
                response = meli.post("/items/"+product.meli_id+"/pictures", { 'id': rjson["id"] }, { 'access_token': meli.access_token } )
            else:
                return { 'status': 'warning', 'message': 'uploaded but not assigned' }

        return { 'status': 'success', 'message': 'uploaded and assigned' }

    def product_meli_upload_multi_images( self  ):

        company = self.env.user.company_id

        product_obj = self.env['product.product']
        product = self

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        #
        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)

        if product.product_variant_image_ids==None:
            return { 'status': 'error', 'message': 'no images to upload' }

        image_ids = []
        c = 0

        #loop over images
        for product_image in product.product_variant_image_ids:
            if (product_image.image_1920):
                #_logger.info( "product_image.image_1920:" + str(product_image.image_1920) )
                imagebin = base64.b64decode( product_image.image_1920 )
                #files = { 'file': ('image.png', imagebin, "image/png"), }
                files = { 'file': ('image.jpg', imagebin, "image/jpeg"), }
                response = meli.upload("/pictures", files, { 'access_token': meli.access_token } )
                _logger.info( "meli upload:" + str(response.content) )
                rjson = response.json()
                if ("error" in rjson):
                    #raise osv.except_osv( _('MELI WARNING'), _('No se pudo cargar la imagen en MELI! Error: %s , Mensaje: %s, Status: %s') % ( rjson["error"], rjson["message"],rjson["status"],))
                    return rjson
                else:
                    image_ids+= [ { 'id': rjson['id'] }]
                    c = c + 1
                    _logger.info( "image_ids:" + str(image_ids) )
                    image_uploaded = {}
                    ilink = ""
                    isize = ""
                    if ('variations' in rjson):
                        if (len(rjson['variations'])):
                            #big one, first one XXX-F
                            image_uploaded = rjson['variations'][0]
                    else:
                        image_uploaded = rjson

                    if 'secure_url' in image_uploaded:
                        ilink = image_uploaded['secure_url']
                    if 'size' in image_uploaded:
                        isize = image_uploaded['size']
                    product_image.meli_imagen_id = rjson['id']
                    product_image.meli_imagen_max_size = rjson['max_size']
                    product_image.meli_imagen_link = ilink
                    product_image.meli_imagen_size = isize

        product.write( { "meli_multi_imagen_id": "%s" % (image_ids) } )

        return image_ids

    def product_on_change_meli_banner(self, banner_id ):

        banner_obj = self.env['mercadolibre.banner']

        #solo para saber si ya habia una descripcion completada
        product_obj = self.env['product.product']
        product = self
        banner = banner_obj.browse( banner_id )

        #banner.description
        _logger.info( banner.description )
        result = ""
        if (banner.description!="" and banner.description!=False and product.meli_imagen_link!=""):
            imgtag = "<img style='width: 420px; height: auto;' src='%s'/>" % ( product.meli_imagen_link )
            result = banner.description.replace( "[IMAGEN_PRODUCTO]", imgtag )
            if (result):
                _logger.info( "result: %s" % (result) )
            else:
                result = banner.description

        return { 'value': { 'meli_description' : result } }


    def product_get_meli_update( self ):
        company = self.env.user.company_id
        warningobj = self.env['warning']
        product_obj = self.env['product.product']
        _logger.info("product_get_meli_update:")
        _logger.info(self)
        for product in self:
            _logger.info(product)
            CLIENT_ID = company.mercadolibre_client_id
            CLIENT_SECRET = company.mercadolibre_secret_key
            ACCESS_TOKEN = company.mercadolibre_access_token
            REFRESH_TOKEN = company.mercadolibre_refresh_token

            ML_status = "unknown"
            ML_permalink = ""
            ML_state = False

            if (ACCESS_TOKEN=='' or ACCESS_TOKEN==False):
                ML_status = "unknown"
                ML_permalink = ""
                ML_state = True
            else:
                meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
                if product.meli_id:
                    response = meli.get("/items/"+product.meli_id, {'access_token':meli.access_token} )
                    rjson = response.json()
                    #_logger.info(rjson)
                    if "status" in rjson:
                        ML_status = rjson["status"]
                    if "permalink" in rjson:
                        ML_permalink = rjson["permalink"]
                    if "error" in rjson:
                        ML_status = rjson["error"]
                        ML_permalink = ""
                    if "sub_status" in rjson:
                        if len(rjson["sub_status"]) and rjson["sub_status"][0]=='deleted':
                            product.write({ 'meli_id': '' })

            product.meli_status = ML_status
            product.meli_permalink = ML_permalink
            product.meli_state = ML_state
        _logger.info("product_get_meli_update end")


    def _is_value_excluded(self, att_value ):
        company = self.env.user.company_id
        if (company.mercadolibre_exclude_attributes):
            for att in company.mercadolibre_exclude_attributes:
                if (att.attribute_id.name == att_value.attribute_id.name):
                    if (att.name == att_value.name):
                        return True
        return False


    def _conditions_ok(self):
        conditionok = False
        product = self
        product_tmpl = self.product_tmpl_id

        att_to_pub = []
        for line in product_tmpl.meli_pub_variant_attributes:
            att_to_pub.append(line.attribute_id.name)
        #_logger.info(att_to_pub)

        for att in product.attribute_value_ids:
            if (att.attribute_id.name in att_to_pub):
                conditionok = True
            if (self._is_value_excluded(att)):
                product.meli_pub = False
                return False

        if (conditionok):
            product.meli_pub = True

        return conditionok

    #return all combinations for this product variants, based on tamplate attributes selected
    def _combination(self):
        var_comb = False
        product = self
        product_tmpl = self.product_tmpl_id

        att_to_pub = []
        for line in product_tmpl.meli_pub_variant_attributes:
            att_to_pub.append(line.attribute_id.name)

        if (len(att_to_pub)==0):
            return False

        price = False
        if (product.meli_price):
            price = product.meli_price
        qty = product.meli_available_quantity

        if (product_tmpl.meli_pub_principal_variant.id and price==False):
            price = product_tmpl.meli_pub_principal_variant.meli_price

        if (product_tmpl.meli_pub_principal_variant.id and (qty==False or qty==0)):
            qty = product_tmpl.meli_pub_principal_variant.meli_available_quantity

        if price==False:
            price = product.lst_price

        if (qty<0):
            qty = 0

        var_comb = {
            "attribute_combinations": [],
            "price": price,
            "available_quantity": qty,
        }
        if (product_tmpl.meli_pub_principal_variant.meli_imagen_id):
            if (len(product_tmpl.meli_pub_principal_variant.meli_imagen_id)):
               var_comb["picture_ids"] = [ product_tmpl.meli_pub_principal_variant.meli_imagen_id]

        #customized attrs:
        customs = []
        for att in product.attribute_value_ids:
            if (att.attribute_id.name in att_to_pub):
                if (not att.attribute_id.meli_default_id_attribute.id):
                    customs.append(att)

        customs.sort(key=lambda x: x.attribute_id.name, reverse=True)
        sep = ""
        custom_name = ""
        custom_values = ""
        for att in customs:
            custom_name = custom_name + sep + att.attribute_id.name
            custom_values = custom_values + sep + att.name
            sep = "."

        if (len(customs)):
            att_combination = {
                "name": custom_name,
                "value_name": custom_values,
            }
            var_comb["attribute_combinations"].append(att_combination)

        for att in product.attribute_value_ids:
            if (att.attribute_id.name in att_to_pub):
                if (att.attribute_id.meli_default_id_attribute.id):
                    if (att.attribute_id.meli_default_id_attribute.variation_attribute):
                        att_combination = {
                            "name":att.attribute_id.meli_default_id_attribute.name,
                            "id": att.attribute_id.meli_default_id_attribute.att_id,
                            "value_name": att.name,
                        }
                        var_comb["attribute_combinations"].append(att_combination)

        return var_comb

    def _is_product_combination(self, variation ):

        var_comb = False
        product = self
        product_tmpl = self.product_tmpl_id

        _logger.info("_is_product_combination:")
        _logger.info(variation)

        _self_combinations = product._combination()
        _map_combinations = {}
        _logger.info('_self_combinations')
        _logger.info(_self_combinations)

        if 'attribute_combinations' in _self_combinations:
            for att in _self_combinations['attribute_combinations']:
                _logger.info(att)
                _map_combinations[att["name"]] = att["value_name"]

        _logger.info('_map_combinations')
        _logger.info(_map_combinations)

        _is_p_comb = True

        if ('attribute_combinations' in variation):
            #check if every att combination exist in this product
            for att in variation['attribute_combinations']:
                _logger.info("chech att:"+str(att["name"]))
                if ( att["name"] in _map_combinations):
                    if (_map_combinations[att["name"]]==att["value_name"]):
                        _is_p_comb = True
                        _logger.info(_is_p_comb)
                    else:
                        _is_p_comb = False
                        _logger.info(_is_p_comb)
                        break
                else:
                    _is_p_comb = False
                    _logger.info(_is_p_comb)
                    break

        return _is_p_comb

    def product_post_variant(self,variant_principal):

        _logger.debug('[DEBUG] product_post_variant, assign meli_id')
        #import pdb; pdb.set_trace()
        for product in self:
            product_tmpl = self.product_tmpl_id
            if (variant_principal):
                product.meli_id = variant_principal.meli_id

    def product_post(self):
        #import pdb;pdb.set_trace();
        #_logger.info('[DEBUG] product_post')
        company = self.env.user.company_id
        warningobj = self.env['warning']
        product_obj = self.env['product.product']
        product_tpl_obj = self.env['product.template']

        for product in self:
            product_tmpl = product.product_tmpl_id

            REDIRECT_URI = company.mercadolibre_redirect_uri
            CLIENT_ID = company.mercadolibre_client_id
            CLIENT_SECRET = company.mercadolibre_secret_key
            ACCESS_TOKEN = company.mercadolibre_access_token
            REFRESH_TOKEN = company.mercadolibre_refresh_token


            meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)

            if ACCESS_TOKEN=='':
                meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET)
                url_login_meli = meli.auth_url(redirect_URI=REDIRECT_URI)
                return {
                    "type": "ir.actions.act_url",
                    "url": url_login_meli,
                    "target": "new",
                }
            #return {}
            #description_sale =  product_tmpl.description_sale
            translation = self.env['ir.translation'].search([('res_id','=',product_tmpl.id),
                                                            ('name','=','product.template,description_sale'),
                                                            ('lang','=','es_AR')])
            if translation:
                #_logger.info("translation")
                #_logger.info(translation.value)
                description_sale = translation.value

            productjson = False
            if (product.meli_id):
                response = meli.get("/items/%s" % product.meli_id, {'access_token':meli.access_token})
                if (response):
                    productjson = response.json()

            #check from company's default
            if company.mercadolibre_listing_type and product_tmpl.meli_listing_type==False:
                product_tmpl.meli_listing_type = company.mercadolibre_listing_type

            if company.mercadolibre_currency and product_tmpl.meli_currency==False:
                product_tmpl.meli_currency = company.mercadolibre_currency

            if company.mercadolibre_condition and product_tmpl.meli_condition==False:
                product_tmpl.meli_condition = company.mercadolibre_condition

            if company.mercadolibre_warranty and product_tmpl.meli_warranty==False:
                product_tmpl.meli_warranty = company.mercadolibre_warranty

            if product_tmpl.meli_title==False:
                product_tmpl.meli_title = product_tmpl.name

            pl = False
            if company.mercadolibre_pricelist:
                pl = company.mercadolibre_pricelist

            if product_tmpl.meli_price==False or product_tmpl.meli_price==0:
                product_tmpl.meli_price = product_tmpl.list_price

            if product_tmpl.taxes_id:
                new_price = product_tmpl.meli_price
                if (pl):
                    return_val = pl.price_get(product.id,1.0)
                    if pl.id in return_val:
                        new_price = return_val[pl.id]
                else:
                    new_price = product_tmpl.list_price
                    if (product.lst_price):
                        new_price = product.lst_price

                new_price = new_price * ( 1 + ( product_tmpl.taxes_id[0].amount / 100) )
                new_price = round(new_price,2)
                product_tmpl.meli_price = new_price
                product.meli_price=product_tmpl.meli_price

            product_tmpl.meli_price = str(int(float(product_tmpl.meli_price)))
            product.meli_price = str(int(float(product.meli_price)))

            if company.mercadolibre_buying_mode and product_tmpl.meli_buying_mode==False:
                product_tmpl.meli_buying_mode = company.mercadolibre_buying_mode

            if product_tmpl.meli_description==False or len(product_tmpl.meli_description)==0:
                product_tmpl.meli_description = product_tmpl.description_sale


            if product.meli_title==False or len(product.meli_title)==0:
                # _logger.info( 'Assigning title: product.meli_title: %s name: %s' % (product.meli_title, product.name) )
                product.meli_title = product_tmpl.meli_title
                if len(product_tmpl.meli_pub_variant_attributes):
                    values = ""
                    for line in product_tmpl.meli_pub_variant_attributes:
                        for value in product.attribute_value_ids:
                            if (value.attribute_id.id==line.attribute_id.id):
                                values+= " "+value.name
                    if (not product_tmpl.meli_pub_as_variant):
                        product.meli_title = string.replace(product.meli_title,product.name,product.name+" "+values)




            force_template_title = False
            if (product_tmpl.meli_title and force_template_title):
                product.meli_title = product_tmpl.meli_title

            if ( product.meli_title and len(product.meli_title)>60 ):
                return warningobj.info( title='MELI WARNING', message="La longitud del título ("+str(len(product.meli_title))+") es superior a 60 caracteres.", message_html=product.meli_title )

            if product.meli_price==False or product.meli_price==0.0:
                if product_tmpl.meli_price:
                    _logger.info("Assign tmpl price:"+str(product_tmpl.meli_price))
                    product.meli_price = product_tmpl.meli_price

            if product.meli_description==False:
                product.meli_description = product_tmpl.meli_description

            if product_tmpl.meli_description:
                product.meli_description = product_tmpl.meli_description

            if product.meli_category==False:
                product.meli_category=product_tmpl.meli_category
            if product.meli_listing_type==False:
                product.meli_listing_type=product_tmpl.meli_listing_type

            if product_tmpl.meli_listing_type:
                product.meli_listing_type=product_tmpl.meli_listing_type

            if product.meli_buying_mode==False:
                product.meli_buying_mode=product_tmpl.meli_buying_mode

            if product_tmpl.meli_buying_mode:
                product.meli_buying_mode=product_tmpl.meli_buying_mode

            if product.meli_price==False:
                product.meli_price=product_tmpl.meli_price
            if product.meli_currency==False:
                product.meli_currency=product_tmpl.meli_currency
            if product.meli_condition==False:
                product.meli_condition=product_tmpl.meli_condition
            if product.meli_warranty==False:
                product.meli_warranty=product_tmpl.meli_warranty

            if product_tmpl.meli_warranty:
                product.meli_warranty=product_tmpl.meli_warranty

            if product.meli_brand==False or len(product.meli_brand)==0:
                product.meli_brand = product_tmpl.meli_brand
            if product.meli_model==False or len(product.meli_model)==0:
                product.meli_model = product_tmpl.meli_model
            if (product_tmpl.meli_brand):
                product.meli_brand = product_tmpl.meli_brand
            if (product_tmpl.meli_model):
                product.meli_model = product_tmpl.meli_model

            attributes = []
            variations_candidates = False
            if product_tmpl.attribute_line_ids:
                _logger.info(product_tmpl.attribute_line_ids)
                for at_line_id in product_tmpl.attribute_line_ids:
                    atname = at_line_id.attribute_id.name
                    #atributos, no variantes! solo con un valor...
                    if (len(at_line_id.value_ids)==1):
                        atval = at_line_id.value_ids.name
                        _logger.info(atname+":"+atval)
                        if (atname=="MARCA" or atname=="BRAND"):
                            attribute = { "id": "BRAND", "value_name": atval }
                            attributes.append(attribute)
                        if (atname=="MODELO" or atname=="MODEL"):
                            attribute = { "id": "MODEL", "value_name": atval }
                            attributes.append(attribute)

                        if (at_line_id.attribute_id.meli_default_id_attribute.id):
                            attribute = {
                                "id": at_line_id.attribute_id.meli_default_id_attribute.att_id,
                                "value_name": atval
                            }
                            attributes.append(attribute)
                    elif (len(at_line_id.value_ids)>1):
                        variations_candidates = True

                _logger.info(attributes)
                product.meli_attributes = str(attributes)

            if product.meli_brand==False or len(product.meli_brand)==0:
                product.meli_brand = product_tmpl.meli_brand
            if product.meli_model==False or len(product.meli_model)==0:
                product.meli_model = product_tmpl.meli_model

            if product.meli_brand and len(product.meli_brand) > 0:
                attribute = { "id": "BRAND", "value_name": product.meli_brand }
                attributes.append(attribute)
                _logger.info(attributes)
                product.meli_attributes = str(attributes)

            if product.meli_model and len(product.meli_model) > 0:
                attribute = { "id": "MODEL", "value_name": product.meli_model }
                attributes.append(attribute)
                _logger.info(attributes)
                product.meli_attributes = str(attributes)

            if product.public_categ_ids:
                for cat_id in product.public_categ_ids:
                    #_logger.info(cat_id)
                    if (cat_id.mercadolibre_category):
                        #_logger.info(cat_id.mercadolibre_category)
                        product.meli_category = cat_id.mercadolibre_category
                        product_tmpl.meli_category = cat_id.mercadolibre_category

            if product_tmpl.meli_category:
                product.meli_category=product_tmpl.meli_category


            if (product.virtual_available):
                if (product.virtual_available>0):
                    product.meli_available_quantity = product.virtual_available

            # Chequea si es fabricable

            if (1==2 and product.meli_available_quantity<=0 and product.route_ids):
                for route in product.route_ids:
                    if (route.name in ['Fabricar','Manufacture']):
                        #raise ValidationError("Fabricar")
                        product.meli_available_quantity = 1

            if (1==2 and product.meli_available_quantity<=10000):
                bom_id = self.env['mrp.bom'].search([('product_id','=',product.id)],limit=1)
                if bom_id and bom_id.type == 'phantom':
                    _logger.info(bom_id.type)
                    #chequear si el componente principal es fabricable
                    for bom_line in bom_id.bom_line_ids:
                        if (bom_line.product_id.default_code.find(product_tmpl.code_prefix)==0):
                            _logger.info(product_tmpl.code_prefix)
                            _logger.info(bom_line.product_id.default_code)
                            for route in bom_line.product_id.route_ids:
                                if (route.name in ['Fabricar','Manufacture']):
                                    _logger.info("Fabricar")
                                    product.meli_available_quantity = 1
                                if (route.name in ['Comprar','Buy']):
                                    _logger.info("Comprar")
                                    product.meli_available_quantity = bom_line.product_id.virtual_available




            body = {
                "title": product.meli_title or '',
                "category_id": product.meli_category.meli_category_id or '0',
                "listing_type_id": product.meli_listing_type or '0',
                "buying_mode": product.meli_buying_mode or '',
                "price": product.meli_price  or '0',
                "currency_id": product.meli_currency  or '0',
                "condition": product.meli_condition  or '',
                "available_quantity": product.meli_available_quantity  or '0',
                "warranty": product.meli_warranty or '',
                #"pictures": [ { 'source': product.meli_imagen_logo} ] ,
                "video_id": product.meli_video  or '',
            }

            bodydescription = {
                "plain_text": product.meli_description or '',
            }
            # _logger.info( body )
            assign_img = False and product.meli_id

            #publicando imagen cargada en OpenERP
            if product.image_1920==None:
                return warningobj.info( title='MELI WARNING', message="Debe cargar una imagen de base en el producto.", message_html="" )
            else:
                # _logger.info( "try uploading image..." )
                resim = product.product_meli_upload_image()
                if "status" in resim:
                    if (resim["status"]=="error" or resim["status"]=="warning"):
                        error_msg = 'MELI: mensaje de error:   ', resim
                        _logger.error(error_msg)
                        if (resim["status"]=="error"):
                            return warningobj.info( title='MELI WARNING', message="Problemas cargando la imagen principal.", message_html=error_msg )
                    else:
                        assign_img = True and product.meli_imagen_id

            #modificando datos si ya existe el producto en MLA
            if (product.meli_id):
                body = {
                    "title": product.meli_title or '',
                    #"buying_mode": product.meli_buying_mode or '',
                    "price": product.meli_price or '0',
                    #"condition": product.meli_condition or '',
                    "available_quantity": product.meli_available_quantity or '0',
                    "warranty": product.meli_warranty or '',
                    "pictures": [],
                    "video_id": product.meli_video or '',
                }
                if (productjson):
                    if ("attributes" in productjson):
                        if (len(attributes)):
                            dicatts = {}
                            for att in attributes:
                                dicatts[att["id"]] = att
                            attributes_ml =  productjson["attributes"]
                            x = 0
                            for att in attributes_ml:
                                if (att["id"] in dicatts):
                                    attributes_ml[x] = dicatts[att["id"]]
                                else:
                                    attributes.append(att)
                                x = x + 1

                            body["attributes"] =  attributes
                        else:
                            attributes =  productjson["attributes"]
                            body["attributes"] =  attributes
            else:
                body["description"] = bodydescription

            #publicando multiples imagenes
            multi_images_ids = {}
            if (product.product_variant_image_ids):
                multi_images_ids = product.product_meli_upload_multi_images()
                if 'status' in multi_images_ids:
                    _logger.error(multi_images_ids)
                    return warningobj.info( title='MELI WARNING', message="Error publicando imagenes", message_html="Error: "+str(multi_images_ids["error"])+" Status:"+str(multi_images_ids["status"]) )

            if product.meli_imagen_id:
                if 'pictures' in body.keys():
                    body["pictures"]+= [ { 'id': product.meli_imagen_id } ]
                else:
                    body["pictures"] = [ { 'id': product.meli_imagen_id } ]

                if (multi_images_ids):
                    if 'pictures' in body.keys():
                        body["pictures"]+= multi_images_ids
                    else:
                        body["pictures"] = multi_images_ids

                if product.meli_imagen_logo:
                    if 'pictures' in body.keys():
                        body["pictures"]+= [ { 'source': product.meli_imagen_logo} ]
                    else:
                        body["pictures"] = [ { 'source': product.meli_imagen_logo} ]
            else:
                imagen_producto = ""

            if len(attributes):
                body["attributes"] =  attributes

            if (not variations_candidates):
                #SKU ?
                if (product.default_code):
                    #TODO: flag for publishing SKU as attribute in single variant mode?? maybe
                    #attribute = { "id": "SELLER_SKU", "value_name": product.default_code }
                    #attributes.append(attribute)
                    #product.meli_attributes = str(attributes)
                    body["seller_custom_field"] = product.default_code


            if (product_tmpl.meli_pub_as_variant):
                #es probablemente la variante principal
                if (product_tmpl.meli_pub_principal_variant.id):
                    #esta definida la variante principal, veamos si es esta
                    if (product_tmpl.meli_pub_principal_variant.id == product.id):
                        #esta es la variante principal, si aun el producto no se publico
                        #preparamos las variantes

                        if ( productjson and len(productjson["variations"]) ):
                            varias = {
                                "title": body["title"],
                                "pictures": body["pictures"],
                                "variations": []
                            }
                            var_pics = []
                            if (len(body["pictures"])):
                                for pic in body["pictures"]:
                                    var_pics.append(pic['id'])
                            _logger.info("Variations already posted, must update them only")
                            for ix in range(len(productjson["variations"]) ):
                                _logger.info("Variation to update!!")
                                _logger.info(productjson["variations"][ix])
                                var_product = product
                                for pvar in product_tmpl.product_variant_ids:
                                    if (pvar._is_product_combination(productjson["variations"][ix])):
                                        var_product = pvar
                                        var_product.meli_available_quantity = var_product.virtual_available
                                var = {
                                    "id": str(productjson["variations"][ix]["id"]),
                                    "price": str(product_tmpl.meli_price),
                                    "available_quantity": var_product.meli_available_quantity,
                                    "picture_ids": var_pics
                                }
                                varias["variations"].append(var)
                            #variations = product_tmpl._variations()
                            #varias["variations"] = variations

                            _logger.info(varias)
                            responsevar = meli.put("/items/"+product.meli_id, varias, {'access_token':meli.access_token})
                            _logger.info(responsevar.json())
                            #_logger.debug(responsevar.json())
                            resdes = meli.put("/items/"+product.meli_id+"/description", bodydescription, {'access_token':meli.access_token})
                            #_logger.debug(resdes.json())
                            del body['price']
                            del body['available_quantity']
                            resbody = meli.put("/items/"+product.meli_id, body, {'access_token':meli.access_token})
                            #_logger.debug(resbody.json())
                             #responsevar = meli.put("/items/"+product.meli_id, {"initial_quantity": product.meli_available_quantity, "available_quantity": product.meli_available_quantity }, {'access_token':meli.access_token})
                             #_logger.debug(responsevar)
                             #_logger.debug(responsevar.json())
                            return {}
                        else:
                            variations = product_tmpl._variations()
                            _logger.info("Variations:")
                            _logger.info(variations)
                            if (variations):
                                body["variations"] = variations
                    else:
                        _logger.debug("Variant not able to post, variant principal.")
                        return {}
                else:
                    _logger.debug("Variant principal not defined yet. Cannot post.")
                    return {}
            else:
                if ( productjson and len(productjson["variations"])==1 ):
                    varias = {
                        "title": body["title"],
                        "pictures": body["pictures"],
                        "variations": []
                    }
                    var_pics = []
                    if (len(body["pictures"])):
                        for pic in body["pictures"]:
                            var_pics.append(pic['id'])
                    _logger.info("Singl variation already posted, must update it")
                    for ix in range(len(productjson["variations"]) ):
                        _logger.info("Variation to update!!")
                        _logger.info(productjson["variations"][ix])
                        var = {
                            "id": str(productjson["variations"][ix]["id"]),
                            "price": str(product_tmpl.meli_price),
                            "available_quantity": product.meli_available_quantity,
                            "picture_ids": var_pics
                        }
                        varias["variations"].append(var)

                        #WARNING: only for single variation
                        product.meli_id_variation = productjson["variations"][ix]["id"]
                    #variations = product_tmpl._variations()
                    #varias["variations"] = variations

                    _logger.info(varias)
                    responsevar = meli.put("/items/"+product.meli_id, varias, {'access_token':meli.access_token})
                    _logger.info(responsevar.json())
                    #_logger.debug(responsevar.json())
                    resdes = meli.put("/items/"+product.meli_id+"/description", bodydescription, {'access_token':meli.access_token})
                    #_logger.debug(resdes.json())
                    del body['price']
                    del body['available_quantity']
                    resbody = meli.put("/items/"+product.meli_id, body, {'access_token':meli.access_token})
                    return {}

            #check fields
            if product.meli_description==False:
                return warningobj.info(title='MELI WARNING', message="Debe completar el campo 'description' (en html)", message_html="")

            if product.meli_id:
                _logger.info(body)
                response = meli.put("/items/"+product.meli_id, body, {'access_token':meli.access_token})
                resdescription = meli.put("/items/"+product.meli_id+"/description", bodydescription, {'access_token':meli.access_token})
                rjsondes = resdescription.json()
            else:
                assign_img = True and product.meli_imagen_id
                response = meli.post("/items", body, {'access_token':meli.access_token})

            #check response
            # _logger.info( response.content )
            rjson = response.json()
            _logger.info(rjson)

            #check error
            if "error" in rjson:
                #_logger.info( "Error received: %s " % rjson["error"] )
                error_msg = 'MELI: mensaje de error:  %s , mensaje: %s, status: %s, cause: %s ' % (rjson["error"], rjson["message"], rjson["status"], rjson["cause"])
                _logger.error(error_msg)

                missing_fields = error_msg

                #expired token
                if "message" in rjson and (rjson["message"]=='invalid_token' or rjson["message"]=="expired_token"):
                    meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET)
                    url_login_meli = meli.auth_url(redirect_URI=REDIRECT_URI)
                    return warningobj.info( title='MELI WARNING', message="Debe iniciar sesión en MELI.  ", message_html="")
                else:
                     #Any other errors
                    return warningobj.info( title='MELI WARNING', message="Completar todos los campos!  ", message_html="<br><br>"+missing_fields )

            #last modifications if response is OK
            if "id" in rjson:
                product.write( { 'meli_id': rjson["id"]} )

            posting_fields = {'posting_date': str(datetime.now()),'meli_id':rjson['id'],'product_id':product.id,'name': 'Post: ' + product.meli_title }

            posting = self.env['mercadolibre.posting'].search( [('meli_id','=',rjson['id'])])
            posting_id = posting.id

            if not posting_id:
                posting_id = self.env['mercadolibre.posting'].create((posting_fields)).id
            else:
                posting.write(( { 'product_id':product.id, 'name': 'Post: ' + product.meli_title }))

        return {}

    def product_post_stock(self):
        company = self.env.user.company_id
        warningobj = self.env['warning']

        product_obj = self.env['product.product']
        product = self
        product_tmpl = self.product_tmpl_id

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token
        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)

        try:
            self.product_update_stock()

            #if (product.virtual_available>=0):
            product.meli_available_quantity = product.virtual_available


            if product.meli_available_quantity<0:
                product.meli_available_quantity = 0

            fields = {
                "available_quantity": product.meli_available_quantity
            }
        #if (product.meli_available_quantity<=0):
        #    product.meli_available_quantity = 50

            _logger.info("post stock:"+str(product.meli_available_quantity))
            _logger.info("product_tmpl.meli_pub_as_variant:"+str(product_tmpl.meli_pub_as_variant))
            _logger.info(product_tmpl.meli_pub_principal_variant.id)
            if (product_tmpl.meli_pub_as_variant):
                productjson = False
                if (product_tmpl.meli_pub_principal_variant.id==False and len(product_tmpl.product_variant_ids)):
                    product_tmpl.meli_pub_principal_variant = product_tmpl.product_variant_ids[0]

                if (product_tmpl.meli_pub_principal_variant.id):
                    base_meli_id = product_tmpl.meli_pub_principal_variant.meli_id
                    if (base_meli_id):
                        response = meli.get("/items/%s" % base_meli_id, {'access_token':meli.access_token})
                        if (response):
                            productjson = response.json()

                #chequeamos la variacion de este producto
                if ( productjson and len(productjson["variations"]) ):
                    varias = {
                        "variations": []
                    }
                    _logger.info("product_post_stock > Update variations stock")
                    found_comb = False
                    pictures_v = []
                    same_price = False
                    for ix in range(len(productjson["variations"]) ):
                        #check if combination is related to this product
                        if 'picture_ids' in productjson["variations"][ix]:
                            if (len(productjson["variations"][ix]["picture_ids"])>len(pictures_v)):
                                pictures_v = productjson["variations"][ix]["picture_ids"]
                        same_price = productjson["variations"][ix]["price"]
                        if (self._is_product_combination(productjson["variations"][ix])):
                            _logger.info("_is_product_combination! Post stock to variation")
                            _logger.info(productjson["variations"][ix])
                            found_comb = True
                            product.meli_id_variation = productjson["variations"][ix]["id"]
                            var = {
                                #"id": str( product.meli_id_variation ),
                                "available_quantity": product.meli_available_quantity,
                                #"picture_ids": ['806634-MLM28112717071_092018', '928808-MLM28112717068_092018', '643737-MLM28112717069_092018', '934652-MLM28112717070_092018']
                            }
                            varias["variations"].append(var)
                            #_logger.info(varias)
                            _logger.info(var)
                            responsevar = meli.put("/items/"+product.meli_id+'/variations/'+str( product.meli_id_variation ), var, {'access_token':meli.access_token})
                            _logger.info(responsevar.json())

                    if found_comb==False:
                        #add combination!!
                        addvar = self._combination()
                        if ('picture_ids' in addvar):
                            if len(pictures_v)>=len(addvar["picture_ids"]):
                                addvar["picture_ids"] = pictures_v
                        addvar["seller_custom_field"] = product.default_code
                        addvar["price"] = same_price
                        _logger.info("Add variation!")
                        _logger.info(addvar)
                        responsevar = meli.post("/items/"+product.meli_id+"/variations", addvar, {'access_token':meli.access_token})
                        _logger.info(responsevar.json())
                _logger.info("Available:"+str(product_tmpl.virtual_available))
                best_available = 0
                for vr in product_tmpl.product_variant_ids:
                    sum = vr.virtual_available
                    if (sum<0):
                        sum = 0
                    best_available+= sum
                if (best_available>0 and product.meli_status=="paused"):
                    _logger.info("Active!")
                    product.product_meli_status_active()
                elif (best_available<=0 and product.meli_status=="active"):
                    _logger.info("Pause!")
                    product.product_meli_status_pause()
            else:
                response = meli.put("/items/"+product.meli_id, fields, {'access_token':meli.access_token})
                if (response.content):
                    rjson = response.json()
                    if ('available_quantity' in rjson):
                        _logger.info( "Posted ok:" + str(rjson['available_quantity']) )
                    else:
                        _logger.info( "Error posting stock" )
                        _logger.info(response.content)

                if (product.meli_available_quantity<=0 and product.meli_status=="active"):
                    product.product_meli_status_pause()
                elif (product.meli_available_quantity>0 and product.meli_status=="paused"):
                    product.product_meli_status_active()

        except Exception as e:
            _logger.info("product_post_stock > exception error")
            _logger.info(e, exc_info=True)
            pass

    def product_update_stock(self, stock=False):
        product = self
        uomobj = self.env['uom.uom']
        _stock = product.virtual_available

        if (stock!=False):
            _stock = stock
            if (_stock<0):
                _stock = 0

        if (product.default_code):
            product.set_bom()

        if (product.meli_default_stock_product):
            _stock = product.meli_default_stock_product.virtual_available
            if (_stock<0):
                _stock = 0

        if (_stock>=0 and product.virtual_available!=_stock):
            _logger.info("Updating stock for variant." + str(_stock) )
            wh = self.env['stock.location'].search([('usage','=','internal')]).id
            product_uom_id = uomobj.search([('name','=','Unidad(es)')])
            if (product_uom_id.id==False):
                product_uom_id = 1
            else:
                product_uom_id = product_uom_id.id

            stock_inventory_fields = {
                "product_id": product.id,
                "filter": "product",
                "location_id": wh,
                "name": "INV: "+ product.name
            }
            #_logger.info("stock_inventory_fields:")
            #_logger.info(stock_inventory_fields)
            StockInventory = self.env['stock.inventory'].create(stock_inventory_fields)
            #_logger.info("StockInventory:")
            #_logger.info(StockInventory)
            if (StockInventory):
                stock_inventory_field_line = {
                    "product_qty": _stock,
                    'theoretical_qty': 0,
                    "product_id": product.id,
                    "product_uom_id": product_uom_id,
                    "location_id": wh,
                    'inventory_location_id': wh,
                    "inventory_id": StockInventory.id,
                    #"name": "INV "+ nombre
                    #"state": "confirm",
                }
                StockInventoryLine = self.env['stock.inventory.line'].create(stock_inventory_field_line)
                #print "StockInventoryLine:", StockInventoryLine, stock_inventory_field_line
                #_logger.info("StockInventoryLine:")
                #_logger.info(stock_inventory_field_line)
                if (StockInventoryLine):
                    #return_id = StockInventory.action_done()
                    return_id = StockInventory.post_inventory()
                    return_id = StockInventory.action_start()
                    return_id = StockInventory.action_validate()
                    #_logger.info("action_done:"+str(return_id))


    def product_post_price(self):
        company = self.env.user.company_id
        warningobj = self.env['warning']

        product_obj = self.env['product.product']
        product = self
        product_tmpl = self.product_tmpl_id

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token
        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)


        pl = False
        if company.mercadolibre_pricelist:
            pl = company.mercadolibre_pricelist

        if product_tmpl.meli_price==False or product_tmpl.meli_price==0:
            product_tmpl.meli_price = product_tmpl.list_price

        #if (product_tmpl.meli_currency=="COP"):
        product_tmpl.meli_price = str(int(float(product_tmpl.meli_price)))

        if product_tmpl.taxes_id:
            new_price = product_tmpl.meli_price
            if (pl):
                return_val = pl.price_get(product.id,1.0)
                if pl.id in return_val:
                    new_price = return_val[pl.id]
            else:
                new_price = product_tmpl.list_price
                if (product.lst_price):
                    new_price = product.lst_price

            new_price = new_price * ( 1 + ( product_tmpl.taxes_id[0].amount / 100) )
            new_price = round(new_price,2)
            product_tmpl.meli_price = new_price
            product.meli_price=product_tmpl.meli_price

        if product_tmpl.meli_price==False or product_tmpl.meli_price==0:
            product_tmpl.meli_price = product_tmpl.standard_price

        if product.meli_price==False or product.meli_price==0.0:
            if product_tmpl.meli_price:
                product.meli_price = product_tmpl.meli_price

        #if (product_tmpl.meli_currency=="COP"):
        product.meli_price = str(int(float(product.meli_price)))
        _logger.info(product.meli_price)
        _logger.info(product_tmpl.meli_price)

        fields = {
            "price": product.meli_price
        }
        response = meli.put("/items/"+product.meli_id, fields, {'access_token':meli.access_token})

    #typical values
    meli_title = fields.Char(string='Nombre del producto en Mercado Libre',size=256)
    meli_description = fields.Text(string='Descripción')
    meli_category = fields.Many2one("mercadolibre.category","Categoría de MercadoLibre")
    meli_price = fields.Char(string='Precio de venta', size=128)
    meli_dimensions = fields.Char( string="Dimensiones del producto", size=128)
    meli_pub = fields.Boolean('Meli Publication',help='MELI Product',index=True)

    meli_buying_mode = fields.Selection( [("buy_it_now","Compre ahora"),("classified","Clasificado")], string='Método de compra')
    meli_currency = fields.Selection([("ARS","Peso Argentino (ARS)"),
    ("MXN","Peso Mexicano (MXN)"),
    ("COP","Peso Colombiano (COP)"),
    ("PEN","Sol Peruano (PEN)"),
    ("BOB","Boliviano (BOB)"),
    ("BRL","Real (BRL)"),
    ("CLP","Peso Chileno (CLP)")],string='Moneda')
    meli_condition = fields.Selection([ ("new", "Nuevo"), ("used", "Usado"), ("not_specified","No especificado")],'Condición del producto')
    meli_warranty = fields.Char(string='Garantía', size=256)
    meli_listing_type = fields.Selection([("free","Libre"),("bronze","Bronce"),("silver","Plata"),("gold","Oro"),("gold_premium","Gold Premium"),("gold_special","Gold Special/Clásica"),("gold_pro","Oro Pro")], string='Tipo de lista')

    #post only fields
    meli_post_required = fields.Boolean(string='Este producto es publicable en Mercado Libre')
    meli_id = fields.Char( string='Id del item asignado por Meli', size=256, index=True)
    meli_description_banner_id = fields.Many2one("mercadolibre.banner","Banner")
    meli_buying_mode = fields.Selection( [("buy_it_now","Compre ahora"),("classified","Clasificado")], string='Método de compra')
    meli_price = fields.Char(string='Precio de venta', size=128)
    meli_price_fixed = fields.Boolean(string='Price is fixed')
    meli_available_quantity = fields.Integer(string='Cantidad disponible')
    meli_imagen_logo = fields.Char(string='Imagen Logo', size=256)
    meli_imagen_id = fields.Char(string='Imagen Id', size=256)
    meli_imagen_link = fields.Char(string='Imagen Link', size=256)
    meli_multi_imagen_id = fields.Char(string='Multi Imagen Ids', size=512)
    meli_video = fields.Char( string='Video (id de youtube)', size=256)

    meli_permalink = fields.Char( compute=product_get_meli_update, size=256, string='PermaLink in MercadoLibre', store=False )
    meli_state = fields.Boolean( compute=product_get_meli_update, string="Inicio de sesión requerida", store=False )
    meli_status = fields.Char( compute=product_get_meli_update, size=128, string="Estado del producto en ML", store=False )

    meli_attributes = fields.Text(string='Atributos')

    meli_model = fields.Char(string="Modelo",size=256)
    meli_brand = fields.Char(string="Marca",size=256)
    meli_default_stock_product = fields.Many2one("product.product","Producto de referencia para stock")
    meli_id_variation = fields.Char( string='Id de Variante de Meli', size=256)

    _defaults = {
        'meli_imagen_logo': 'None',
        'meli_video': ''
    }

product_product()
