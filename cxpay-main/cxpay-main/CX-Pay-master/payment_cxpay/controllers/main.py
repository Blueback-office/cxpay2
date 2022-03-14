# -*- coding: utf-8 -*-
import pprint
import logging
from werkzeug import urls, utils

from odoo import http, _
from odoo.http import request
from odoo.exceptions import ValidationError, UserError
from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.addons.website_sale.controllers.main import WebsiteSale

from odoo.addons.payment_cxpay.models.authorize_request import CXPay as AuthorizeAPI

_logger = logging.getLogger(__name__)


class AuthorizeController(http.Controller):

    @http.route(['/payment/cx_pay/approve/<int:payment_id>'], type='http', auth='public', csrf=False)
    def cx_pay_paymment_approve(self, payment_id=False, token_id=False, **kwargs):
        payment_id = request.env['payment.transaction'].sudo().browse(payment_id)
        if kwargs.get('token-id'):
            payment_id.token_id = kwargs.get('token-id') 
        payment_id.cxpay_s2s_do_transaction_verify()
        payment_id.payment_token_id.cvv_no = False
        PaymentProcessing.add_payment_transaction(payment_id)
        return http.redirect_with_hash('/payment/process')

    
    @http.route(['/payment/cx_pay/s2s/create_json_3ds'], type='json', auth='public', csrf=False)
    def cxpay_s2s_create_json_3ds(self, verify_validity=False, **kwargs):
        token = False
        acquirer = request.env['payment.acquirer'].browse(int(kwargs.get('acquirer_id')))
        try:
            if not kwargs.get('partner_id'):
                kwargs = dict(kwargs, partner_id=request.env.user.partner_id.id)
            token = acquirer.s2s_process(kwargs)
        except ValidationError as e:
            message = e.args[0]
            if isinstance(message, dict) and 'missing_fields' in message:
                if request.env.user._is_public():
                    message = _("Please sign in to complete the payment.")
                    # update message if portal mode = b2b
                    if request.env['ir.config_parameter'].sudo().get_param('auth_signup.allow_uninvited', 'False').lower() == 'false':
                        message += _(" If you don't have any account, ask your salesperson to grant you a portal access. ")
                else:
                    msg = _("The transaction cannot be processed because some contact details are missing or invalid: ")
                    message = msg + ', '.join(message['missing_fields']) + '. '
                    message += _("Please complete your profile. ")

            return {
                'error': message
            }
        except UserError as e:
            return {
                'error': e.name,
            }

        if not token:
            res = {
                'result': False,
            }
            return res
        res = {
            'result': True,
            'id': token.id,
            'short_name': token.short_name,
            '3d_secure': False,
            'verified': True
        }
        return res

    @http.route(["/payment_method/add"], type="http", auth="public", website=True)
    def add_new_credit_card(self, url=False, token=False, **kwargs):
        payment_token = request.env["payment.token"].sudo().browse(int(token))
        if not url or not payment_token:
            return request.redirect('/shop/payment')
        values = {
            "url" :  url,
            "cc_number" : payment_token.card_number,
            "exp_date":  payment_token.exp_date,
            "cvv_no":  payment_token.cvv_no,
        }
        return request.render("payment_cxpay.pay_with_confirmation", values)
    
class WebsiteSale(WebsiteSale):

    @http.route('/shop/payment/token', type='http', auth='public', website=True, sitemap=False)
    def payment_token(self, pm_id=None, **kwargs):
        """ Method that handles payment using saved tokens

        :param int pm_id: id of the payment.token that we want to use to pay.
        """
        order = request.website.sale_get_order()
        # do not crash if the user has already paid and try to pay again
        if not order:
            return request.redirect('/shop/?error=no_order')

        assert order.partner_id.id != request.website.partner_id.id

        try:
            pm_id = int(pm_id)
        except ValueError:
            return request.redirect('/shop/?error=invalid_token_id')

        # We retrieve the token the user want to use to pay
        if not request.env['payment.token'].sudo().search_count([('id', '=', pm_id)]):
            return request.redirect('/shop/?error=token_not_found')
    
        # Create transaction
        vals = {'payment_token_id': pm_id, 'return_url': '/shop/payment/validate'}
    
        tx = order._create_payment_transaction(vals)
        pm_ids = request.env['payment.token'].browse(pm_id)
        if pm_ids.acquirer_id.provider == 'cxpay':
            if isinstance(tx, dict):
                url = '/payment_method/add?url=' + tx.get('url') + '&token=' +  str(pm_id)
                return request.redirect(url)
        PaymentProcessing.add_payment_transaction(tx)
        return request.redirect('/payment/process')


