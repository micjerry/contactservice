import tornado.web
import tornado.gen
import json
import io
import logging

import tornado_mysql

from mickey.mysqlcon import get_mysqlcon

import mickey.userfetcher
from mickey.basehandler import BaseHandler


_getmydevice_sql = """
    SELECT a.userID, a.commName, a.name, b.name as sn FROM userentity a JOIN account b WHERE a.userID = b.userEntity_userID and a.owner = %s AND b.type = %s;
"""
_getdevice_sql = """
  SELECT a.combo, DATE_FORMAT(a.st_time,'%s') as st_time, DATE_FORMAT(DATE_ADD(a.st_time, INTERVAL a.month MONTH), '%s') AS end_time, 
         b.rec_name, b.rec_phone, b.rec_address ,c.name FROM devices a JOIN dispatch_bills b LEFT JOIN combs c ON (a.combo = c.com_id) WHERE a.dis_id = b.sid AND a.sn = '%s';
"""

class ListDeviceHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        userid = data.get("id", "invalid")

        logging.info("list contact for %s" % userid)

        if self.p_userid != userid:
            logging.error("you can not query other user info")
            self.set_status(403)
            self.finish()
            return

        devices = yield self.get_mydevices(self.p_userid)
        if devices:
            rs_devices = []
            for item in devices:
                device = {}
                device["id"] = device_id = str(item.get("userID", ""))
                device["nickname"] = item.get("commName", "")
                device["name"] = item.get("name", "")

                sn_id = item.get("sn", "")
                c_deviceinfo = yield self.fetch_device(sn_id)
                if c_deviceinfo:
                    device["address"] = c_deviceinfo.get("rec_address", "")
                    device["receiver"] = c_deviceinfo.get("rec_name", "")
                    device["receiver_phone"] = c_deviceinfo.get("rec_phone", "")
                    device["st_time"] = c_deviceinfo.get("st_time", "")
                    device["end_time"] = c_deviceinfo.get("end_time", "")
                    device["combo_id"] = c_deviceinfo.get("combo", "")
                    device["combo_name"] = c_deviceinfo.get("name", "")

                rs_devices.append(device)

            self.write({"devices": rs_devices})

        else:
            logging.error("user %s was not found" % userid)
            self.set_status(404)
            self.write({"error":"not found"});
        self.finish()

    @tornado.gen.coroutine
    def get_mydevices(self, userid):
        conn = yield get_mysqlcon('mxsuser')
        if not conn:
            logging.error("connect to mysql failed")
            return []
        try:
            cur = conn.cursor(tornado_mysql.cursors.DictCursor)
            yield cur.execute(_getmydevice_sql, (userid, 'TerminalAccount'))
            rows = cur.fetchall()
            cur.close()
            return rows
        except Exception as e:
            logging.error("db oper failed {0}".format(e))
            return []
        finally:
            conn.close()

        
    @tornado.gen.coroutine
    def fetch_device(self, deviceid):
        conn = yield get_mysqlcon()
        if not conn:
            logging.error("connect to mysql failed")
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
