# !/usr/bin/env python
# -*- coding:utf-8 -*-

import time
from urllib import urlencode
from cyclone import httpclient
from toughlib import utils, logger
from toughlib import apiutils
from twisted.internet import defer
from toughradius.manage.events.event_basic import BasicEvent
from toughradius.manage.settings import TOUGHCLOUD as toughcloud
from toughradius.common import tools
from toughlib.mail import send_mail as sendmail


class AccountInsufficientBalanceNotifyEvent(BasicEvent):
    """用户余额不足CLOUD通知服务EVENT"""

    MAIL_TPLNAME = 'tr_balance_notify'
    MAIL_APIURL = "%s/sendmail" % toughcloud.apiurl

    SMS_TPLNAME = 'tr_balance_notify'
    SMS_APIURL = "%s/sendsms" % toughcloud.apiurl

    @defer.inlineCallbacks
    def event_toughcloud_sms_account_insufficient_balance(self, userinfo):
        """ toughCloud sms api user balance is not enough notify event """
        if not userinfo:
            return

        if not userinfo.get('phone'):
            logger.error('user phone is None exit')
            return

        api_secret = self.get_param_value("toughcloud_license")
        api_token = yield tools.get_sys_token()
        params = dict(
            token=api_token.strip(),
            action='sms',
            tplname=self.SMS_TPLNAME,
            phone=userinfo.email,
            customer=utils.safestr(userinfo.realname),
            username=userinfo.account_number,
            balance=utils.fen2yuan(int(userinfo.balance)),
            product=utils.safestr(userinfo.product_name),
            nonce=str(int(time.time()))
        )
        params['sign'] = apiutils.make_sign(api_secret.strip(), params.values())
        try:
            resp = yield httpclient.fetch(self.SMS_APIURL, postdata=urlencode(params))
            logger.info(resp.body)
            logger.info('user next send short message success')
        except Exception as err:
            logger.exception(err)

    @defer.inlineCallbacks
    def event_toughcloud_mail_account_insufficient_balance(self, userinfo):
        """ toughCloud mail api user balance is not enough notify event """
        if not userinfo:
            return

        if not userinfo.get('email'):
            logger.error('user email is None exit')
            return

        try:
            api_secret = self.get_param_value("toughcloud_license")
            service_mail = self.get_param_value("toughcloud_service_mail")
            if not service_mail:
                return
            api_token = yield tools.get_sys_token()
            params = dict(
                token=api_token.strip(),
                action='email',
                mailto=userinfo.email,
                tplname=self.MAIL_TPLNAME,
                customer=utils.safestr(userinfo.realname),
                username=userinfo.account_number,
                balance=utils.fen2yuan(int(userinfo.balance)),
                product=utils.safestr(userinfo.product_name),
                service_call=self.get_param_value("toughcloud_service_call", ''),
                service_mail=service_mail,
                nonce=str(int(time.time()))
            )
            params['sign'] = apiutils.make_sign(api_secret.strip(), params.values())
            resp = yield httpclient.fetch(self.MAIL_APIURL, postdata=urlencode(params))
            logger.info(resp.body)
            logger.info('user next send email  success')
        except Exception as err:
            logger.exception(err)

    def event_smtp_account_insufficient_balance(self, userinfo):

        open_notify = u"""尊敬的 %customer% 您好:
                        您的账号 %username% 余额只有 %balance%，为保证您的服务，请您及时充值。"""

        ctx = open_notify.replace('%customer%', userinfo.realname)
        ctx = ctx.replace('%username%', userinfo.account_number)
        ctx = ctx.replace('%balance%', userinfo.balance)
        topic = ctx[:ctx.find('\n')]
        smtp_server = self.get_param_value("smtp_server", '127.0.0.1')
        from_addr = self.get_param_value("smtp_from")
        smtp_port = int(self.get_param_value("smtp_port", 25))
        smtp_sender = self.get_param_value("smtp_sender", None)
        smtp_user = self.get_param_value("smtp_user", None)
        smtp_pwd = self.get_param_value("smtp_pwd", None)
        return sendmail(
            server=smtp_server,
            port=smtp_port,
            user=smtp_user,
            password=smtp_pwd,
            from_addr=from_addr, mailto=userinfo.email,
            topic=utils.safeunicode(topic),
            content=utils.safeunicode(ctx),
            tls=False)


def __call__(dbengine=None, mcache=None, **kwargs):
    return AccountInsufficientBalanceNotifyEvent(dbengine=dbengine, mcache=mcache, **kwargs)