import tornado.web
import tornado.gen
import json
import io
import logging

import motor
import uuid

import mickey.userfetcher
import mickey.users
from mickey.basehandler import BaseHandler

from mickey.commonconf import REDIS_TPKEY_PREFIX

class ListContactHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        coll = self.application.db.users
        data = json.loads(self.request.body.decode("utf-8"))
        userid = data.get("id", "invalid")
        client_flag = data.get("flag", "")
        server_flag = None
        token = self.request.headers.get("Authorization", "")

        logging.info("list contact for %s flag = %s" % (userid, client_flag))

        if self.p_userid != userid:
            logging.error("you can not query other user info")
            self.set_status(403)
            self.finish()
            return

        user = yield coll.find_one({"id":userid})
        if user:
            server_flag = user.get("flag", "")
            if client_flag and client_flag == server_flag:
                self.set_status(304)
                self.finish()
                return

            contacts = user.get("contacts", [])
            appends = user.get("appendings", [])

            rs_contacts = []
            for item in contacts:
                contact = {}
                c_id = item.get("id", "")
                contact["id"] = c_id
                contact["remark"] = item.get("remark", "")
                contact["star"] = item.get("star", "")
                c_userinfo = yield mickey.userfetcher.getcontact(c_id, token)
                if c_userinfo:
                    contact["nickname"] = c_userinfo.get("commName", "")
                    contact["sign"] = c_userinfo.get("sign", "")
                    contact["type"] = c_userinfo.get("type", "")
                    contact["name"] = c_userinfo.get("name", "")

                tp_userid = yield mickey.users.get_tpuserid_o(c_id)
                contact["tp_userid"] = tp_userid
                    
                rs_contacts.append(contact)

            self.write({"contacts": rs_contacts,"appendings":appends, "flag": server_flag})

        else:
            logging.error("user %s was not found" % userid)
            self.set_status(404)
            self.write({"error":"not found"});
        self.finish()

                
