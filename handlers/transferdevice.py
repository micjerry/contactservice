import tornado.web
import tornado.gen
import json
import io
import logging

from mickey.mysqlcon import get_mysqlcon

import mickey.userfetcher
from mickey.basehandler import BaseHandler

_transfer_sql = """
  UPDATE deviceusermap set userEntity_userID = %s WHERE device_userID = %s AND userEntity_userID = %s AND role = %s;
"""

class TransferDeviceHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        devices = data.get("devices", [])
        userid = data.get("userid", "")

        logging.info("%s transfer device %r to %s" % (self.p_userid, devices, userid))
        if not devices or not userid:
            logging.error("invalid parameter")
            self.set_status(403)
            self.finish()
            return

        result = yield self.transfer_devices(devices, userid, self.p_userid)
        
        if not result:
            logging.error("transfer failed remove failure")
            self.set_status(500)
            self.finish()
            return

        self.set_status(200)
        self.finish()

    @tornado.gen.coroutine
    def transfer_devices(self, devices, new_userid, old_userid):
        conn = yield get_mysqlcon('mxsuser')
        if not conn:
            logging.error("connect to mysql failed")
            return False

        try:
            cur = conn.cursor()
            for item in devices:
                yield cur.execute(_transfer_sql, (new_userid, item, old_userid, 'ADMIN'))

            cur.close()
            yield conn.commit()
        except Exception as e:
            logging.error("oper db failed {0}".format(e))
            return False
        finally:
            conn.close()

        return True

