import tornado.web
import tornado.gen
import json
import io
import logging

import motor
import uuid

import mickey.userfetcher
from mickey.basehandler import BaseHandler

import libcontact

class AcceptBindHandler(BaseHandler):

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        coll = self.application.db.users
        publish = self.application.publish
        token = self.request.headers.get("Authorization", "")

        #get parameters of request
        data         = json.loads(self.request.body.decode("utf-8"))
        deviceid     = data.get("deviceid", "")

        logging.info("begin to accept bind request, user = %s, device = %s" % (self.p_userid, deviceid))
        
        if not deviceid:
            logging.error("invalid parameter")
            self.set_status(403)
            self.finish()
            return

        result = yield libcontact.check_bindcount(deviceid, 1)
        if not result:
            logging.error("forbiden no right")
            self.set_status(403)
            self.write({"code":"1008", "desc":"too much binders"})
            self.finish()
            return

        modresult = yield coll.find_and_modify({"id":deviceid},
                                               {
                                                 "$pull":{"binders":self.p_userid},
                                                 "$unset": {"garbage": 1}
                                               })

        if not modresult:
            logging.error("invalid device id")
            self.set_status(404)
            self.finish()
            return

        binders = modresult.get("binders", [])
        if not self.p_userid in binders:
            logging.error("you are not invited")
            self.set_status(403)
            self.finish()
            return

        #get current binders
        already_binders = yield libcontact.get_binders(deviceid)


        #do bind
        bind_rst = yield mickey.userfetcher.bindboxtouser(self.p_userid, deviceid, 'USER')

        if bind_rst != 200:
            logging.error("bind failed")
            self.set_status(500)
            self.finish()
            return

        if not already_binders:
            self.set_status(200)
            self.finish()
            return

        #send notify to the exist binders
        username = ""
        devicename = ""
        res_device = yield mickey.userfetcher.getcontact(deviceid, token)
        res_user = yield mickey.userfetcher.getcontact(self.p_userid, token)

        if res_user:
            username = res_user.get("commName", "")

        if res_device:
            devicename = res_device.get("commName", "")
            

        notify = {
              "name": "mx.contact.newbinder",
              "deviceid": deviceid,
              "devicename": devicename,
              "userid": self.p_userid,
              "username": username,
              "pub_type": "any",
              "nty_type": "app",
              "msg_type": "other"
            }

        publish.publish_multi(already_binders, notify)

        self.set_status(200)
        self.finish()



