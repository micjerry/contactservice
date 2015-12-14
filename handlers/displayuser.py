import tornado.web
import tornado.gen
import tornado.httpclient

import json
import io
import logging

import motor
from mickey.basehandler import BaseHandler

class DispayUserHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        coll      = self.application.db.users
        data      = json.loads(self.request.body.decode("utf-8"))
        userid    = data.get("id", "")

        #begin to logging user
        logging.info("%s begin to display" % (userid))

            
        #get remark
        remark = ""
        star = ""
        result = yield coll.find_one({"id":self.p_userid})
        userinfo = {}

        if result:
            userinfo["tp_info"] = result.get("tp_info", {})
 

        self.write(userinfo)

        self.finish()
