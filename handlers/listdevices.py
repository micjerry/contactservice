import tornado.web
import tornado.gen
import json
import io
import logging

import tornado_mysql

import mickey.userfetcher
from mickey.basehandler import BaseHandler
import libcontact

class ListDeviceHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        model_config = self.application.model_config
        data = json.loads(self.request.body.decode("utf-8"))
        userid = data.get("id", "invalid")

        logging.info("list contact for %s" % userid)

        if self.p_userid != userid:
            logging.error("you can not query other user info")
            self.set_status(403)
            self.finish()
            return

        devices = yield libcontact.get_mydevices(self.p_userid)
        rs_devices = []
        if devices:
            for item in devices:
                device = {}
                device["id"] = str(item.get("userID", ""))
                device["nickname"] = item.get("commName", "")
                device["name"] = item.get("name", "")

                sn_id = item.get("sn", "")
                device["sn"] = sn_id
                sn_flag = sn_id[0:2]
                device["model"] = model_config.get(sn_flag, "M1")

                c_deviceinfo = yield libcontact.fetch_device(sn_id)
                if c_deviceinfo:
                    device["address"] = c_deviceinfo.get("rec_address", "")
                    device["receiver"] = c_deviceinfo.get("rec_name", "")
                    device["receiver_phone"] = c_deviceinfo.get("rec_phone", "")
                    device["st_time"] = c_deviceinfo.get("st_time", "")
                    device["end_time"] = c_deviceinfo.get("end_time", "")
                    device["combo_id"] = c_deviceinfo.get("combo", "")
                    device["combo_name"] = c_deviceinfo.get("name", "")
                    device["oid"] = c_deviceinfo.get("oid", "")
                    device["express_id"] = c_deviceinfo.get("express_id", "")
                    device["express_name"] = c_deviceinfo.get("express_name", "")

                rs_devices.append(device)

        use_devices = yield libcontact.get_myusedevices(self.p_userid)

        rs_usedevices = []
        if use_devices:
            for item in use_devices:
                device = {}
                device["id"] = str(item.get("userID", ""))
                device["nickname"] = item.get("commName", "")
                device["name"] = item.get("name", "")

                sn_id = item.get("sn", "")
                device["sn"] = sn_id
                sn_flag = sn_id[0:2]
                device["model"] = model_config.get(sn_flag, "M1")
                c_deviceinfo = yield libcontact.fetch_device(sn_id)
                if c_deviceinfo:
                    device["address"] = c_deviceinfo.get("rec_address", "")
                    device["receiver"] = c_deviceinfo.get("rec_name", "")
                    device["receiver_phone"] = c_deviceinfo.get("rec_phone", "")
                    device["st_time"] = c_deviceinfo.get("st_time", "")
                    device["end_time"] = c_deviceinfo.get("end_time", "")
                    device["combo_id"] = c_deviceinfo.get("combo", "")
                    device["combo_name"] = c_deviceinfo.get("name", "")
                    device["oid"] = c_deviceinfo.get("oid", "")
                    device["express_id"] = c_deviceinfo.get("express_id", "")
                    device["express_name"] = c_deviceinfo.get("express_name", "")

                rs_usedevices.append(device)


        self.write({"devices": rs_devices, "usedevices": rs_usedevices})

        self.finish()


