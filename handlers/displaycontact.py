import tornado.web
import tornado.gen
import tornado.httpclient

import json
import io
import logging

import motor
import basehandler

class DispayContactHandler(basehandler.BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        coll = self.application.db.users
        data = json.loads(self.request.body.decode("utf-8"))
        userid = data.get("id", "invalid")
        contactid = data.get("contactid", "invalid")

        #begin to logging user
        logging.info("%s begin to display %s" % (userid, contactid))

        httpclient = tornado.httpclient.AsyncHTTPClient()
        url = "http://localhost:9080/cxf/security/contacts/%s" % contactid
        response = yield httpclient.fetch(url, None, method = "GET", headers = {}, body = None)
        
        if response.code != 200:
            logging.error("get contactinfo failed userid = %s" % userid)
            self.set_status(401)
            self.finish()
            return

        res_body = {}
        try:
            res_body = json.loads(response.body.decode("utf-8"))
        except Exception as e:
            logging.error("invalid body received")
            self.send_error(401)
            return

        #get remark
        remark = ""
        result = yield coll.find_one({"id":userid})
        if result:
            contacts = result.get("contacts", [])
            for contact in contacts:
                if (contact.get("id", "") == contactid):
                   remark =  contact.get("remark", "")
                   break
 
        userinfo = {}
        userinfo["id"] = contactid
        userinfo["remark"] = remark
        userinfo["nickname"] = res_body.get("commName", "")
        userinfo["contactInfos"] = res_body.get("contactInfos", [])

        self.write(userinfo)

        self.finish()
