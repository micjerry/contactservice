import tornado.web
import tornado.gen
import json
import io
import logging

import motor
import uuid

import mickey.userfetcher
from mickey.basehandler import BaseHandler

from mickey.commonconf import SINGLE_MODE, REDIS_TPKEY_PREFIX

if SINGLE_MODE:
    import redis
    _sentinel         = redis.StrictRedis(host='localhost', port=6379, db=0, socket_timeout=5.0)
    _sentinel_salve   = _sentinel
    _sentinel_master  = _sentinel
else:
    from redis.sentinel import Sentinel
    _sentinel = Sentinel([('localhost', 26379)], socket_timeout = 1)
    _sentinel_salve = _sentinel.slave_for('master', socket_timeout = 0.5)
    _sentinel_master = _sentinel.master_for('master', socket_timeout = 0.5)


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

                tp_userid = yield self.get_tpuserid_of_contact(c_id)
                contact["tp_userid"] = tp_userid
                    
                rs_contacts.append(contact)

            self.write({"contacts": rs_contacts,"appendings":appends, "flag": server_flag})

        else:
            logging.error("user %s was not found" % userid)
            self.set_status(404)
            self.write({"error":"not found"});
        self.finish()

    @tornado.gen.coroutine
    def get_tpuserid_of_contact(self, contactid):
        coll = self.application.db.users
        redis_key = REDIS_TPKEY_PREFIX + contactid

        try:
            redis_tpid = _sentinel_salve.get(redis_key)
        except Exception as e:
            logging.error("can not get cached tp information {0}".format(e))

        if redis_tpid:
            return redis_tpid.decode("utf-8")

        # read from mongo
        tp_userid = None
        contact = yield coll.find_one({"id":contactid})
        if contact:
            tp_info = contact.get("tp_info", {})
            if tp_info:
                tp_userid = tp_info.get("tp_userid", "")
        
        # save tp_userid to redis
        if tp_userid:
            try:
                _sentinel_master.set(redis_key, tp_userid)
            except Exception as e:
                logging.error("save cached tp information {0}".format(e))

        return tp_userid
                
