import tornado.gen

from mickey.domain import DomainMgr

# used for /contact/display/detail
# /contact/add/friend
@tornado.gen.coroutine
def default_relation_fetcher(userid, data):
    relations = []
    relations.append(userid)
    contactid = data.get("contactid", "")
    if contactid:
        relations.append(contactid)
    return (relations, None)

# /contact/user/display
@tornado.gen.coroutine
def id_relation_fetcher(userid, data):
    relations = []
    relations.append(userid)
    contactid = data.get("id", "")
    if contactid:
        relations.append(contactid)
    return (relations, None)

# /contact/device/addbinders
# /contact/device/acceptbind
# /contact/device/scanbind
@tornado.gen.coroutine
def device_relation_fetcher(userid, data):
    relations = []
    relations.append(userid)
    deviceid = data.get("deviceid", "")
    contacts = data.get("contacts", [])
    
    if deviceid:
        relations.append(deviceid)

    for item in contacts:
        relations.append(item)

    return (relations, None)

# /contact/user/queryname
@tornado.gen.coroutine
def users_relation_fetcher(userid, data):
    relations = []
    users = data.get("users", [])
    for item in users:
        relations.append(item)

    return (relations, None)


class DomainFilter(object):
    def __init__(self):
        self.fetchers = {}
        self.fetchers["/contact/display/detail"] = default_relation_fetcher
        self.fetchers["/contact/add/friend"] = default_relation_fetcher
        self.fetchers["/contact/user/display"] = id_relation_fetcher
        self.fetchers["/contact/device/addbinders"] = device_relation_fetcher
        self.fetchers["/contact/device/acceptbind"] = device_relation_fetcher
        self.fetchers["/contact/device/scanbind"] = device_relation_fetcher
        self.fetchers["/contact/user/queryname"] = users_relation_fetcher

    def getname(self):
        return "domain"

    @tornado.gen.coroutine
    def execfilter(self, url, userid, data):
        (result, req_obj) = yield DomainMgr.execfilter(self.fetchers, url, userid, data)
        return (result, req_obj)

