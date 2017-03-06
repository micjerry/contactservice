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
import mickey.redis

from mickey.commonconf import REDIS_TPKEY_PREFIX, REDIS_CONTACT_PREFIX, REDIS_TPKEY_PREFIX

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

            contact_ids = [ x.get("id", "") for x in contacts ]
            contact_rediskeys = [REDIS_CONTACT_PREFIX + x for x in contact_ids ]
            tp_rediskeys = [ REDIS_TPKEY_PREFIX + x for x in contact_ids ]
            contact_cachinfos = mickey.redis.read_from_redis_pipeline(contact_rediskeys)
            tp_cachkeys = mickey.redis.read_from_redis_pipeline(tp_rediskeys)
            
            rs_contacts = []
            for idx, item in enumerate(contacts):
                contact = {}
                c_id = item.get("id", "")

                contact["id"] = c_id
                contact["remark"] = item.get("remark", "")
                contact["star"] = item.get("star", "")
                c_userinfo = None
                if not contact_cachinfos[idx]:
                    c_userinfo = yield mickey.userfetcher.getcontact(c_id, token)
                else:
                    c_userinfo = json.loads(contact_cachinfos[idx])

                if c_userinfo:
                    contact["nickname"] = c_userinfo.get("commName", "")
                    contact["sign"] = c_userinfo.get("sign", "")
                    contact["type"] = c_userinfo.get("type", "")
                    contact["name"] = c_userinfo.get("name", "")
                    contact["organization"] = c_userinfo.get("organization", "")

                tp_userid = tp_cachkeys[idx]
                if not tp_userid:
                    tp_userid = yield mickey.users.get_tpuserid_of_contact(c_id)

                contact["tp_userid"] = tp_userid
                    
                rs_contacts.append(contact)

            self.write({"contacts": rs_contacts,"appendings":appends, "flag": server_flag})

        else:
            logging.error("user %s was not found" % userid)
            self.set_status(404)
            self.write({"error":"not found"});
        self.finish()

                
