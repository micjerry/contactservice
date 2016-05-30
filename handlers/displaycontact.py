import tornado.web
import tornado.gen
import tornado.httpclient

import json
import io
import logging

import motor
import mickey.userfetcher

from mickey.basehandler import BaseHandler
from mickey.users import get_devicesn

import libcontact

_USER_FORMAT = "10010000000"
def formatuserid(userid):
    if not userid:
        return ""

    copy_len = len(_USER_FORMAT) - len(userid)
    if copy_len <= 0:
        return userid

    new_userid = _USER_FORMAT[0:copy_len] + userid
    return new_userid

def transfertouserid(chatid):
    if not chatid:
        return ""

    id_part = ""
    for item in chatid:
        if item.isdigit():
            id_part = id_part + item

    #return id_part
    return formatuserid(id_part)

class DispayContactHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        coll      = self.application.db.users
        data      = json.loads(self.request.body.decode("utf-8"))
        userid    = data.get("id", "invalid")
        contactid = data.get("contactid", "")
        tp_userid = data.get("tp_userid", "")

        #begin to logging user
        logging.info("%s begin to display %s" % (userid, contactid))
        if tp_userid:
            contactid =  transfertouserid(tp_userid)

        if not contactid:
            self.set_status(403)
            self.finish()
            return

        #force to get the data from database
        res_body = yield mickey.userfetcher.getcontact(contactid, None, forcedb = True)

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
        userinfo["phoneNumber"] = res_body.get("phoneNumber", "")
        userinfo["contactInfos"] = res_body.get("contactInfos", [])
        userinfo["type"] = res_body.get("type", "")
        userinfo["sign"] = res_body.get("sign", "")
        userinfo["name"] = res_body.get("name", "")
        userinfo["sex"] = res_body.get("sex", 0)

        contact_info = yield coll.find_one({"id":contactid})
        if contact_info:
            tp_info = contact_info.get("tp_info", {})
            if tp_info:
                userinfo["tp_userid"] = tp_info.get("tp_userid", "")

        if res_body.get("type", "") == "TERMINAL":
            admin_info = yield libcontact.get_admininfo(contactid)
            users = yield libcontact.get_userinfo(contactid)

            userinfo["admin"] = admin_info
            userinfo["users"] = users

            admin_user = False
            if admin_info and str(admin_info.get("id", "")) == userid:
                admin_user = True

            if not admin_user and users:
                for item in users:
                    if str(item.get("id", "")) == userid:
                        admin_user = True
                        break

            if admin_user:   
                snnumber = yield get_devicesn(contactid)
                if snnumber:
                    userinfo["sn"] = snnumber
            
        self.write(userinfo)

        self.finish()
