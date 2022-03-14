# coding: utf-8
from werkzeug import urls

import hashlib
import hmac
import logging
import time
import datetime

from odoo import _, api, fields, models
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment_authorize.controllers.main import AuthorizeController
from odoo.tools.float_utils import float_compare, float_repr
from odoo.exceptions import UserError
from odoo.addons.payment_cxpay.models.authorize_request import CXPay as AuthorizeAPI

_logger = logging.getLogger(__name__)

class TxAuthorize(models.Model):
    _inherit = "payment.transaction"

    def cxpay_s2s_do_transaction(self, **data):
        self.ensure_one()
        transaction = AuthorizeAPI(self.acquirer_id)
        if self.currency_id.name == 'USD':
            amount = round(self.amount, self.currency_id.decimal_places)
        else:
            usd_id =self.env['res.currency'].search([(
                'name', '=', 'USD'
            )])
            amount = self.amount * self.env['res.currency']._get_conversion_rate(self.currency_id, usd_id, self.env.user.company_id, datetime.datetime.now())
        if not self.acquirer_id.capture_manually:
            res = transaction.auth_and_capture(
                self.payment_token_id,
                self,
                amount,
                self.reference,
                self,
            )
        else:
            res = transaction.authorize(
                self.payment_token_id,
                amount,
                self.reference,
            )
        if res.get("x_response_code") == "1":
            return res
        else:
            return self._cxpay_s2s_validate_tree(res)
