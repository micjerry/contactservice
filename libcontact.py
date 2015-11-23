import logging
import tornado.gen

import tornado_mysql
from mickey.mysqlcon import get_mysqlcon
from bson.objectid import ObjectId

_logger = logging.getLogger(__name__)

_checkadmin_sql = """
  SELECT userEntity_userID FROM deviceusermap WHERE device_userID = %s AND role = %s;
"""

_addbind_sql = """
  INSERT INTO deviceusermap(role, searchKey, device_userID) VALUES(%s, %s, %s);
"""

_unbind_sql = """
  DELETE FROM deviceusermap WHERE searchKey = %s AND role = %s AND device_userID = %s;
"""

_querybindphone_sql = """
  SELECT name FROM account WHERE userEntity_userID = %s and type = '%s';
"""

_querybinduser_sql = """
  SELECT a.userEntity_userID FROM account a JOIN deviceusermap b WHERE a.name = b.searchKey AND b.device_userID = %s AND b.role = %s;
"""

_queryadmin_sql = """
  SELECT c.commName AS nickname, c.userID AS id FROM deviceusermap a JOIN account b LEFT JOIN userentity c ON (b.userEntity_userID = c.userID) WHERE 
    a.userEntity_userID = b.userEntity_userID AND a.device_userID = %s AND b.type = %s AND a.role = %s;
"""

_queryusers_sql = """
  SELECT c.commName as nickname, c.userID as id FROM deviceusermap a JOIN account b LEFT JOIN userentity c ON (b.userEntity_userID = c.userID) WHERE 
    a.searchKey = b.name AND a.device_userID = %s AND a.role = %s;
"""

_getmydevice_sql = """
    SELECT a.userID, a.commName, a.name, b.name as sn FROM userentity a JOIN account b LEFT JOIN deviceusermap c ON (c.device_userID=a.userID) WHERE a.userID = b.userEntity_userID AND
      c.userEntity_userID = %s AND
      b.type = %s AND c.role = %s;
"""

_getmyusedevice_sql = """
    SELECT b.name as sn, c.commName, c.userID, c.name FROM deviceusermap a JOIN account b LEFT JOIN userentity c ON (a.device_userID = c.userID) WHERE a.device_userID = b.userEntity_userID  
      AND a.searchKey = %s AND a.role = %s AND b.type = %s;
"""

_getdevice_sql = """
  SELECT a.combo, DATE_FORMAT(a.st_time,'%s') as st_time, DATE_FORMAT(DATE_ADD(a.st_time, INTERVAL a.month MONTH), '%s') AS end_time,
         b.rec_name, b.rec_phone, b.rec_address, b.express_id, b.express_name, c.name, d.oid FROM devices a JOIN dispatch_bills b LEFT JOIN combs c ON (a.combo = c.com_id) LEFT JOIN order_bills d ON (b.order_id = d.sid)
         WHERE a.dis_id = b.sid AND a.sn = '%s';
"""

@tornado.gen.coroutine
def get_binders(deviceid):
    conn = yield get_mysqlcon('mxsuser')
    if not conn:
        logging.error("connect to mysql failed")
        return []

    try:
        cur = conn.cursor(tornado_mysql.cursors.DictCursor)
        yield cur.execute(_querybinduser_sql, (deviceid, 'USER'))
        rows = cur.fetchall()
        cur.close()

        bind_ids = [x.get("userEntity_userID", "") for x in rows]
        return bind_ids

    except Exception as e:
        logging.error("oper db failed {0}".format(e))
        return []
    finally:
        conn.close()

    return []


@tornado.gen.coroutine
def check_admin(userid, deviceid):
    conn = yield get_mysqlcon('mxsuser')
    if not conn:
        logging.error("connect to mysql failed")
        return False

    try:
        cur = conn.cursor(tornado_mysql.cursors.DictCursor)
        yield cur.execute(_checkadmin_sql, (deviceid, 'ADMIN'))
        admin = cur.fetchone()
        cur.close()
        if not admin:
            logging.error("device %s not found" % deviceid)
            return False

        adminid = str(admin.get("userEntity_userID", ""));
        if userid != adminid:
            logging.error("the user %s is not the owner of %s it is %s" % (userid, deviceid, adminid))
            return False

        return True
    except Exception as e:
        logging.error("oper db failed {0}".format(e))
        return False
    finally:
        conn.close()

    return False


@tornado.gen.coroutine
def check_bindcount(deviceid, bindnum):
    conn = yield get_mysqlcon('mxsuser')
    if not conn:
        logging.error("connect to mysql failed")
        return False

    try:
        cur = conn.cursor(tornado_mysql.cursors.DictCursor)
        yield cur.execute(_checkadmin_sql, (deviceid, 'USER'))
        rows = cur.fetchall()
        cur.close()
        if not rows:
            logging.info("no user was bound to %s" % deviceid)
            return True

        if (len(rows) + bindnum) > 5:
            logging.info("too many user was bound to %s" % deviceid)
            return False

        return True

    except Exception as e:
        logging.error("oper db failed {0}".format(e))
        return False
    finally:
        conn.close()

    return False

@tornado.gen.coroutine
def get_bindphone(contact):
    conn = yield get_mysqlcon('mxsuser')
    if not conn:
        logging.error("connect to mysql failed")
        return None

    try:
        cur = conn.cursor(tornado_mysql.cursors.DictCursor)
        format_sql = _querybindphone_sql % (contact, 'MobileAccount')
        yield cur.execute(format_sql)
        user = cur.fetchone()
        cur.close()
        if user:
            return user.get("name", "")
        return None

    except Exception as e:
        logging.error("oper db failed {0}".format(e))
        return None
    finally:
        conn.close()

    return None

@tornado.gen.coroutine
def add_bind(deviceid, phone):
    conn = yield get_mysqlcon('mxsuser')
    if not conn:
        logging.error("connect to mysql failed")
        return False
    try:
        cur = conn.cursor()
        yield cur.execute(_addbind_sql, ('USER', phone, deviceid))

        cur.close()
        yield conn.commit()
        return True
    except Exception as e:
        logging.error("oper db failed {0}".format(e))
    finally:
        conn.close()

    return False

@tornado.gen.coroutine
def un_bind(deviceid, phone):
    conn = yield get_mysqlcon('mxsuser')
    if not conn:
        logging.error("connect to mysql failed")
        return False
    try:
        cur = conn.cursor()
        yield cur.execute(_unbind_sql, (phone, 'USER', deviceid))

        cur.close()
        yield conn.commit()
        return True
    except Exception as e:
        logging.error("oper db failed {0}".format(e))
    finally:
        conn.close()

    return False

@tornado.gen.coroutine
def get_admininfo(deviceid):
    conn = yield get_mysqlcon('mxsuser')
    if not conn:
        logging.error("connect to mysql failed")
        return None

    try:
        cur = conn.cursor(tornado_mysql.cursors.DictCursor)
        yield cur.execute(_queryadmin_sql, (deviceid, 'MobileAccount', 'ADMIN'))
        user = cur.fetchone()
        cur.close()
        return user

    except Exception as e:
        logging.error("oper db failed {0}".format(e))
        return None
    finally:
        conn.close()

    return None

@tornado.gen.coroutine
def get_userinfo(deviceid):
    conn = yield get_mysqlcon('mxsuser')
    if not conn:
        logging.error("connect to mysql failed")
        return None

    try:
        cur = conn.cursor(tornado_mysql.cursors.DictCursor)
        yield cur.execute(_queryadmin_sql, (deviceid, 'USER'))
        rows = cur.fetchall()
        cur.close()
        return rows

    except Exception as e:
        logging.error("oper db failed {0}".format(e))
        return None
    finally:
        conn.close()

    return None

@tornado.gen.coroutine
def get_mydevices(userid):
    conn = yield get_mysqlcon('mxsuser')
    if not conn:
        logging.error("connect to mysql failed")
        return []
    try:
        cur = conn.cursor(tornado_mysql.cursors.DictCursor)
        yield cur.execute(_getmydevice_sql, (userid, 'TerminalAccount', 'ADMIN'))
        rows = cur.fetchall()
        cur.close()
        return rows
    except Exception as e:
        logging.error("db oper failed {0}".format(e))
        return []
    finally:
        conn.close()

@tornado.gen.coroutine
def get_myusedevices(phone):
    conn = yield get_mysqlcon('mxsuser')
    if not conn:
        logging.error("connect to mysql failed")
        return []
    try:
        cur = conn.cursor(tornado_mysql.cursors.DictCursor)
        yield cur.execute(_getmyusedevice_sql, (phone, 'USER', 'TerminalAccount'))
        rows = cur.fetchall()
        cur.close()
        return rows
    except Exception as e:
        logging.error("db oper failed {0}".format(e))
        return []
    finally:
        conn.close()

@tornado.gen.coroutine
def fetch_device(deviceid):
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
