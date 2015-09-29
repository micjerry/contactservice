import tornado.web
import tornado.gen
import json
import io
import logging

import motor
import tornado_mysql

from mickey.mysqlcon import get_mysqlcon

import mickey.userfetcher
from mickey.basehandler import BaseHandler

_getdevice_sql = """
  SELECT a.combo, DATE_FORMAT(a.st_time,'%s') as st_time, DATE_FORMAT(DATE_ADD(a.st_time, INTERVAL a.month MONTH), '%s') AS end_time, 
         b.rec_name, b.rec_phone, b.rec_address FROM devices a JOIN dispatch_bills b WHERE a.dis_id = b.sid AND a.u_id = '%s';
"""

class ListDeviceHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        coll = self.application.db.users
        data = json.loads(self.request.body.decode("utf-8"))
        userid = data.get("id", "invalid")

        logging.info("list contact for %s" % userid)

        if self.p_userid != userid:
            logging.error("you can not query other user info")
            self.set_status(403)
            self.finish()
            return

        user = yield coll.find_one({"id":userid})
        if user:
            devices = user.get("devices", [])

            rs_devices = []
            for item in devices:
                device = {}
                device["id"] = item
                c_userinfo = yield mickey.userfetcher.getcontact(item)
                if c_userinfo:
                    device["nickname"] = c_userinfo.get("commName", "")
                    device["name"] = c_userinfo.get("name", "")

                c_deviceinfo = yield self.fetch_device(item)
                if c_deviceinfo:
                    device["address"] = c_deviceinfo.get("rec_address", "")
                    device["receiver"] = c_deviceinfo.get("rec_name", "")
                    device["receiver_phone"] = c_deviceinfo.get("rec_phone", "")
                    device["st_time"] = c_deviceinfo.get("st_time", "")
                    device["end_time"] = c_deviceinfo.get("end_time", "")
                    device["combo_id"] = c_deviceinfo.get("combo", "")

                rs_devices.append(device)

            self.write({"devices": rs_devices})

        else:
            logging.error("user %s was not found" % userid)
            self.set_status(404)
            self.write({"error":"not found"});
        self.finish()

    @tornado.gen.coroutine
    def fetch_device(self, deviceid):
        conn = yield get_mysqlcon()
        if not conn:
            logging.error("connect to mysql failed")
            self.set_status(403)
            self.finish()
            return {}

        try:
            cur = conn.cursor(tornado_mysql.cursors.DictCursor)
            qy_sql = _getdevice_sql % ('%Y-%m-%d', '%Y-%m-%d', deviceid)
            yield cur.execute(qy_sql)
            device = cur.fetchone()
            cur.close()
            return device
        except Exception as e:
            logging.error("db oper failed {0}".format(e))
            return {}
        finally:
            conn.close()
