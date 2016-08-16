import tornado.web
import tornado.gen
import json
import io
import logging

import motor

import tornado_mysql
from mickey.mysqlcon import get_mysqlcon

import mickey.userfetcher
import mickey.redis
from mickey.basehandler import BaseHandler

from mickey.commonconf import REDIS_FETCH_RETRY

_getdevice_sql = """
  SELECT sn, IFNULL(combo,"") as combo_id, IFNULL(u_id,"") as u_id, IFNULL(month, "") as month, UNIX_TIMESTAMP(st_time) as st_time, 
    b.express_id, b.express_name, b.rec_name, b.rec_phone, b.rec_address, c.name as combo_name FROM devices a JOIN dispatch_bills b 
    LEFT JOIN combs c ON (a.combo = c.com_id) 
    WHERE a.dis_id = b.sid AND order_tag = %s;
"""

_getorder_sql = """
  SELECT oid, user, mobile, UNIX_TIMESTAMP(otime) as otime, amount, a.rec_name, a.rec_address, a.rec_phone FROM order_bills a JOIN dispatch_bills b 
    LEFT JOIN devices c ON (c.dis_id = b.sid) WHERE a.sid=b.order_id AND c.order_tag = %s LIMIT 1;
"""

_valid_len = 6
_valid_iter = '0123456789abcdefghijklmnopqrstuvwxyz'

class FetchOrderHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        coll = self.application.db.users
        model_config = self.application.model_config
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

        #valid tag clear times
        self.set_retry(self.p_userid, 0)
        order_info = yield self.get_order(order_tag)

        if not order_info:
            logging.error("unset flag failed")
            self.set_status(500)
            self.finish()
            return

        #add model info
        for item in devices:
            sn_number = item.get("sn","")
            sn_flag = sn_number[0:2]
            
            item["model"] = model_config.get(sn_flag, "M1")

        #get total count info
        total_count = {}
        for item in devices:
            model = item.get("model", "")
            if total_count.get(model, ""):
               total_count[model] = total_count[model] + 1
            else:
               total_count[model] = 1

        for key, value in total_count.items():
            total_count[key] = str(value)

        result = {}
        result['order'] = order_info
        result['devices'] = devices
        result['total_count'] = total_count

        #update devices
        self.write(result)
        self.finish()

    def check_retry(self, userid):
        retry_times = mickey.redis.read_from_redis(REDIS_FETCH_RETRY + userid, 0)

        return int(retry_times)

    def set_retry(self, userid, retry_times):
        rs_key = REDIS_FETCH_RETRY + userid
        if retry_times == 0:
            mickey.redis.remove_from_redis(rs_key)
            return
        else:
            mickey.redis.write_to_redis(rs_key, str(retry_times), 900)

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
            cur.close()

            devices = []
            for item in rows:
                item["st_time"] = str(item["st_time"])
                item["month"] = str(item["month"])
                devices.append(item)
            return devices
        except Exception as e:
            logging.error("db oper failed {0}".format(e))
            return []
        finally:
            conn.close()

    @tornado.gen.coroutine
    def get_order(self, order_tag):
        conn = yield get_mysqlcon()
        if not conn:
            logging.error("connect to mysql failed")
            return []

        try:
            cur = conn.cursor(tornado_mysql.cursors.DictCursor)
            yield cur.execute(_getorder_sql, (order_tag))
            rows = cur.fetchall()
            cur.close()

            for item in rows:
                item["otime"] = str(item["otime"])
                item["amount"] = str(item["amount"])
                return item

        except Exception as e:
            logging.error("db oper failed {0}".format(e))
            return []
        finally:
            conn.close()
