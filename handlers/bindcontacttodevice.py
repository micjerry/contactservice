import tornado.web
import tornado.gen
import json
import io
import logging

import motor

import mickey.userfetcher
from mickey.basehandler import BaseHandler

import libcontact

class BindContactToDeviceHandler(BaseHandler):

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        coll = self.application.db.users
        publish = self.application.publish

        #get parameters of request
        data         = json.loads(self.request.body.decode("utf-8"))
        deviceid     = data.get("deviceid", "")
        comment      = data.get("comment", "")
        contacts     = data.get("contacts", [])
        token = self.request.headers.get("Authorization", "")

        logging.info("begin to handle add contact request, deviceid = %s, contact = %r" % (deviceid, contacts))
        
        if not deviceid or not contacts:
            logging.error("invalid parameter")
            self.set_status(403)
            self.finish()
            return

        bind_self = False
        authen_binders = []
        for item in contacts:
            if item == self.p_userid:
                bind_self = True
                continue

            authen_binders.append(item)


        result = yield libcontact.check_admin(self.p_userid, deviceid)
        if not result:
            logging.error("forbiden no right")
            self.set_status(403)
            self.finish()
            return

        result = yield libcontact.check_bindcount(deviceid, len(contacts))
        if not result:
            logging.error("forbiden no right")
            self.set_status(423, reason = "too many user was bound")
            self.finish()
            return

        # fetch user and device info
        username = ""
        devicename = ""
        res_device = yield mickey.userfetcher.getcontact(deviceid, token)
        res_user = yield mickey.userfetcher.getcontact(self.p_userid, token)

        if res_device:
            devicename = res_device.get("commName", "")

        if res_user:
            username = res_user.get("commName", "")

        if bind_self:

            already_binders = yield libcontact.get_binders(deviceid)

            #bind user to device
            bind_rst = yield mickey.userfetcher.bindboxtouser(self.p_userid, deviceid, 'USER')

            if bind_rst != 200:
                logging.error("bind failed")
                self.set_status(500)
                self.finish()
                return

            #send notify to other binders
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

            if already_binders:
                publish.publish_multi(already_binders, notify)

        if authen_binders:
            result = yield coll.find_and_modify({"id":deviceid},
                                            {
                                              "$addToSet":{"binders":{"$each": authen_binders}},
                                              "$unset": {"garbage": 1}
                                            })

            if not result:
                logging.error("bind failed")
                self.set_status(500)
                self.finish()
                return

            notify = {
              "name": "mx.contact.bind_todevice",
              "deviceid": deviceid,
              "devicename": devicename,
              "userid": self.p_userid,
              "username": username,
              "comment": comment,
              "pub_type": "any",
              "nty_type": "app",
              "msg_type": "other"
            }

            publish.publish_multi(authen_binders, notify)



        self.set_status(200)
        self.finish()



