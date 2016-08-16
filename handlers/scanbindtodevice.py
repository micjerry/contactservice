import tornado.web
import tornado.gen
import json
import io
import logging

import motor
import uuid

import mickey.userfetcher
from mickey.basehandler import BaseHandler
import tornado_mysql
from mickey.mysqlcon import get_mysqlcon

import libcontact

class ScanBindToDeviceHandler(BaseHandler):

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        coll = self.application.db.users
        publish = self.application.publish

        #get parameters of request
        data         = json.loads(self.request.body.decode("utf-8"))
        deviceid     = data.get("deviceid", "")

        logging.info("begin to handle bind request, user = %s, deviceid = %s" % (self.p_userid, deviceid))
        
        if not deviceid:
            logging.error("invalid parameter")
            self.set_status(403)
            self.finish()
            return

        result = yield libcontact.check_bindcount(deviceid, 1)
        if not result:
            logging.error("forbiden no right")
            self.set_status(423)
            self.finish()
            return

        bind_rst = yield mickey.userfetcher.bindboxtouser(self.p_userid, deviceid, 'USER')

        if bind_rst != 200:
            logging.error("bind failed")
            self.set_status(500)
            self.finish()
            return


        self.set_status(200)
        self.finish()



