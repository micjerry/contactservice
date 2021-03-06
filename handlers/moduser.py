import tornado.web
import tornado.gen
import tornado.httpclient

import json
import io
import logging

from mickey.basehandler import BaseHandler
import mickey.users
import mickey.tp

class ModUserHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        coll      = self.application.db.users
        publish   = self.application.publish
        data      = json.loads(self.request.body.decode("utf-8"))
        userid    = data.get("id", "")
        userinfo  = data.get("user", "")

        #begin to logging user
        logging.info("%s begin to mod %r" % (userid, userinfo))
        if not userid or not userinfo:
            self.set_status(403)
            self.finish()
            return
            
        can_modify = False
        if userid == self.p_userid:
            can_modify = True
         
        if not can_modify:
            can_modify = yield mickey.users.check_ismydevice(self.p_userid, userid)

        if not can_modify:
            logging.error("user %s can not modify %s" % (self.p_userid, userid))
            self.set_status(403)
            self.finish()
            return

        result = yield mickey.users.update_user(userid, userinfo)
        if not result:
            logging.error("modify failed userid = %s modsuer = %s" % (self.p_userid, userid))
            self.set_status(500)
            self.finish()
            return

        #update uerinfo of third party
        tpuserinfo = {"id":userid}
        username = userinfo.get("name", "")
        nickname = userinfo.get("nickname", "")
        sign = userinfo.get("sign", "")
        
        if username:
            tpuserinfo["name"] = username
        if nickname:
            tpuserinfo["nickname"] = nickname
        if sign:
            tpuserinfo["remark"] = sign

        mickey.tp.moduser(tpuserinfo)

        notify = {
          "name":"mx.contact.user_updated",
          "userid":userid,
          "modby":self.p_userid,
          "pub_type": "any",
          "nty_type": "app"
        }

        publish.broadcast_one(userid, notify)

        self.finish()
