import tornado.web
import tornado.gen
import json
import io
import logging

import motor
from redis.sentinel import Sentinel

import tornado_mysql
from mickey.mysqlcon import get_mysqlcon

import mickey.userfetcher
from mickey.basehandler import BaseHandler

_sentinel = Sentinel([('localhost', 26379)], socket_timeout = 1)
_sentinel_salve = _sentinel.slave_for('master', socket_timeout = 0.5)
_sentinel_master = _sentinel.master_for('master', socket_timeout = 0.5)

_retry_flag = 'fetchdevice_%s'

_getdevice_sql = """
  SELECT u_id FROM devices WHERE order_tag = %s;
"""

_unset_sql = """
  UPDATE devices SET order_tag = %s WHERE order_tag = %s;
"""

_unused_sql = """
  DELETE FROM order_seqs WHERE order_tag = %s;
"""

class FetchDeviceHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        coll = self.application.db.users
        data = json.loads(self.request.body.decode("utf-8"))
        order_tag = data.get("order_seq", "").lower()
        logging.info("%s fetch device %s" % (self.p_userid, order_tag))

        if not order_tag:
            self.set_status(403)
            self.finish()
            return        

        retry_times = self.check_retry(self.p_userid)
        if retry_times > 5:
            logging.error("retry too many times %s" % self.p_userid)
            self.set_status(403)
            self.finish()
            return
                
        devices = yield self.get_devices(order_tag)
        if not devices:
            self.set_retry(self.p_userid, retry_times + 1)
            logging.error("no device to fetch %s" % order_tag)
            self.set_status(403)
            self.finish()
            return

        result = yield self.unset_flag(order_tag)
        if not result:
            logging.error("unset flag failed")
            self.set_status(500)
            self.finish()
            return

        #update devices
        yield coll.find_and_modify({"id":self.p_userid},
                                   {
                                     "$addToSet":{"devices":{"$each": devices}},
                                     "$unset": {"garbage": 1}
                                   })

        self.finish()

    def check_retry(self, userid):
        retry_times = 0
        retrys = None
        try:
            retrys = _sentinel_salve.get(_retry_flag % userid)
        except Exception as e:
            logging.error("can not get cached information {0}".format(e))

        if retrys:
            retry_times = int(retrys.decode("utf-8"))

        return retry_times

    def set_retry(self, userid, retry_times):
        try:
            rs_key = _retry_flag % userid
            _sentinel_master.set(rs_key, str(retry_times))
            _sentinel_master.expire(rs_key, 900)
        except Exception as e:
            _logger.error("can not cach user information {0}".format(e))

    @tornado.gen.coroutine
    def get_devices(self, order_tag):
        conn = yield get_mysqlcon()
        if not conn:
            logging.error("connect to mysql failed")
            return []
        
        try:
            cur = conn.cursor(tornado_mysql.cursors.DictCursor)
            yield cur.execute(_getdevice_sql, (order_tag))
            rows = cur.fetchall()
            devices = [x.get("u_id", "") for x in rows]  
            cur.close()

            return devices
        except Exception as e:
            logging.error("db oper failed {0}".format(e))
            return []
        finally:
            conn.close()

    @tornado.gen.coroutine
    def unset_flag(self, order_tag):
        conn = yield get_mysqlcon()
        if not conn:
            logging.error("connect to mysql failed")
            return False
        
        unused_tag = order_tag + "_un"
        try:
            cur = conn.cursor()
            yield cur.execute(_unset_sql, (unused_tag, order_tag))
            yield cur.execute(_unused_sql,(order_tag))
            yield conn.commit()
        except Exception as e:
            logging.error("insert db failed {0}".format(e))
            return False

        return True
            
