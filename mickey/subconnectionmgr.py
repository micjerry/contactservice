import logging
from mickey.subconnection import SubConnection

class SubConnectionMgr(object):
    connections = []
    amp_url = 'amqp://guest:guest@localhost:5672/%2F'
    initialized = False

    @classmethod 
    def initial(cls):
        logging.info("begin create connection pools")
        cls.initialized = True
        for i in range(10):
            pikaconnect = SubConnection(cls.amp_url)
            pikaconnect.start()
            cls.connections.append(pikaconnect)

    @classmethod
    def finalize(cls):
        logging.info("close all the connections")
        map(lambda x: x.stop(), cls.connections)

    @classmethod 
    def check(cls):
        logging.info("check all the connections, remove the unused consumer")
        map(lambda x: x.checkconsumers(), cls.connections)

    @classmethod 
    def connection(cls):
        """
        get one connection from the connection pool
        """
        if not cls.initialized:
            cls.initial()

        for item in cls.connections:
            if not item.islimited():
                return item

