import tornado.web
import tornado.gen
import tornado.httpclient

import json
import io
import logging

import motor
import mickey.userfetcher
from mickey.basehandler import BaseHandler

class DispayContactHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        coll      = self.application.db.users
        data      = json.loads(self.request.body.decode("utf-8"))
        userid    = data.get("id", "invalid")
        contactid = data.get("contactid", "invalid")

        #begin to logging user
        logging.info("%s begin to display %s" % (userid, contactid))

        res_body = yield mickey.userfetcher.getcontact(contactid)

        if not res_body:
            self.set_status(404)
            self.finish()
            return

        #get remark
        remark = ""
        star = ""
        result = yield coll.find_one({"id":userid})
        if result:
            contacts = list(filter(lambda x: x.get("id", "") == contactid, result.get("contacts", [])))
            for contact in contacts:
                remark =  contact.get("remark", "")
                star = contact.get("star", "")
                break
 
        userinfo = {}
        userinfo["id"] = contactid
        userinfo["remark"] = remark
        userinfo["star"] = star
        userinfo["nickname"] = res_body.get("commName", "")
        userinfo["contactInfos"] = res_body.get("contactInfos", [])
        userinfo["type"] = res_body.get("type", "")
        userinfo["sign"] = res_body.get("sign", "")
        userinfo["sex"] = res_body.get("sex", 0)

        self.write(userinfo)

        self.finish()
