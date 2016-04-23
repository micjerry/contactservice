import tornado.web
import tornado.gen
import json
import io
import logging

import tornado_mysql
from mickey.mysqlcon import get_mysqlcon

import mickey.userfetcher
from mickey.basehandler import BaseHandler

from mickey.commonconf import REDIS_FETCH_RETRY
import mickey.redis


_getdevice_sql = """
  SELECT sn FROM devices WHERE order_tag = %s;
"""

_getdevice_userid_sql = """
  SELECT userEntity_userID FROM account WHERE name IN %s;
"""

_fetch_sql = """
  INSERT INTO deviceusermap(role, device_userID, userEntity_userID) VALUES(%s, %s, %s);
"""

_unset_sql = """
  UPDATE devices SET order_tag = %s, fetchby = %s WHERE order_tag = %s;
"""
_unused_sql = """
  DELETE FROM order_seqs WHERE order_tag = %s;
"""

_valid_len = 6
_valid_iter = '0123456789abcdefghijklmnopqrstuvwxyz'

class FetchDeviceHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        order_tag = data.get("order_seq", "").lower()
        logging.info("%s fetch device %s" % (self.p_userid, order_tag))

        if not order_tag:
            self.set_status(403)
            self.finish()
            return        

        #check retry times
        retry_times = self.get_retry(self.p_userid)
        if retry_times > 5:
            logging.error("retry too many times %s" % self.p_userid)
            self.set_status(403)
            self.finish()
            return
                
        #check tag is valid
        if len(order_tag) != _valid_len:
            self.set_status(403)
            self.finish()
            return

        for item in order_tag:
            if item not in _valid_iter:
                logging.error('invlaid %s in tag' % item)
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

        self.set_retry(self.p_userid, 0)        
        
        #fetch devices
        fetch_result = yield self.fetch_devices(self.p_userid, devices)
        if not fetch_result:
            logging.error("fetch devices failed")
            self.set_status(500)
            self.finish()
            return

        #unset devices
        unset_result = yield self.unset_flag(order_tag, self.p_userid)
        if not unset_result:
            logging.error("unset flag failed")
            self.set_status(500)
            self.finish()
            return

        self.finish()

    def get_retry(self, userid):
        retry_times = 0
        retrys = mickey.redis.read_from_redis(REDIS_FETCH_RETRY + userid)

        if retrys:
            retry_times = int(retrys)

        return retry_times

    def set_retry(self, userid, retry_times):
        rs_key = REDIS_FETCH_RETRY + userid
        if retry_times == 0:
            mickey.redis.remove_from_redis(rs_key)
            return
        else:
            mickey.redis.write_to_redis(rs_key, str(retry_times), expire = 900)

    @tornado.gen.coroutine
    def get_devices(self, order_tag):
        devices = None
        conn = yield get_mysqlcon()
        if not conn:
            logging.error("connect to mysql failed")
            return []
        
        try:
            cur = conn.cursor(tornado_mysql.cursors.DictCursor)
            yield cur.execute(_getdevice_sql, (order_tag))
            rows = cur.fetchall()
            devices = [x.get("sn", "") for x in rows]  
            cur.close()

            #return devices
        except Exception as e:
            logging.error("db oper failed {0}".format(e))
            return []
        finally:
            conn.close()

        #get user id
        if not devices:
            return None

        list_sn = "("
        for item in devices:
            list_sn = list_sn + item + ','
        list_sn = list_sn[:-1]
        list_sn = list_sn + ")"

        format_sql = _getdevice_userid_sql % list_sn
        logging.info("format sql %s " % format_sql)

        conn = yield get_mysqlcon('mxsuser')
        if not conn:
            logging.error("connect to mysql failed")
            return []        

        try:
            cur = conn.cursor(tornado_mysql.cursors.DictCursor)
            yield cur.execute(format_sql)
            rows = cur.fetchall()
            device_ids = [x.get("userEntity_userID", "") for x in rows]
            cur.close()

            return device_ids
        except Exception as e:
            logging.error("db oper failed {0}".format(e))
            return []
        finally:
            conn.close()

    @tornado.gen.coroutine
    def fetch_devices(self, userid, devices):
        conn = yield get_mysqlcon('mxsuser')
        if not conn:
            logging.error("connect to mysql failed")
            return False

        try:
            cur = conn.cursor()
            for item in devices:
                yield cur.execute(_fetch_sql, ('ADMIN', item, userid))

            cur.close()
            yield conn.commit()
        except Exception as e:
            logging.error("oper db failed {0}".format(e))
            return False
        finally:
            conn.close()

        return True


    @tornado.gen.coroutine
    def unset_flag(self, order_tag, userid):
        conn = yield get_mysqlcon()
        if not conn:
            logging.error("connect to mysql failed")
            return False
        
        unused_tag = order_tag + "_" + userid
        try:
            cur = conn.cursor()
            yield cur.execute(_unset_sql, (unused_tag, self.p_userid, order_tag))
            yield cur.execute(_unused_sql,(order_tag))
            cur.close()
            yield conn.commit()
        except Exception as e:
            logging.error("insert db failed {0}".format(e))
            return False
        finally:
            conn.close()

        return True
            
