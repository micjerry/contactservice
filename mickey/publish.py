import os
import json
import tornado.httpclient


def handle_response(response):
    pass
 
def publish_one(receiver, notify):

    print("publish_one start")
    if not receiver or not notify:
        return
    
    publish_body = {}
    publish_body["receivers"] = [
     {"id":receiver}   
    ]
    publish_body["notify"] = notify

    str_body = json.dumps(publish_body)
    http_client = tornado.httpclient.AsyncHTTPClient()
    http_client.fetch("http://localhost:8081/push", handle_response, method='POST', headers=None, body=str_body) 

def publish_one_tmp(receiver, notify):
    print("publish_onetmp start")
    if not receiver or not notify:
        return

    publish_body = {}
    publish_body["receivers"] = [
     {"id":receiver}
    ]
    publish_body["notify"] = notify

    str_body = json.dumps(publish_body)
    http_client = tornado.httpclient.AsyncHTTPClient()
    http_client.fetch("http://localhost:8081/tmppush", handle_response, method='POST', headers=None, body=str_body)

def publish_multi(receivers, notify):
    print("publish multi")
    if not receivers or not notify:
        return

    publish_body = {}
    pub_recs = []
    for item in receivers:
        pub_recs.append({"id":item})

    publish_body["receivers"] = pub_recs
    publish_body["notify"] = notify

    str_body = json.dumps(publish_body)
    http_client = tornado.httpclient.AsyncHTTPClient()
    http_client.fetch("http://localhost:8081/push", handle_response, method='POST', headers=None, body=str_body)
