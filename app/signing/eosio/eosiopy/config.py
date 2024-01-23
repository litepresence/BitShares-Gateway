from eosiopy.eosioapi import eosio_api_dict


class EosioConfig(object):
    def __init__(self, url="http://127.0.0.1", port=8888):
        self.url = url
        self.port = port
        self.MAX_NAME_IDX = 12
        self.expiration = 30
        for k, v in eosio_api_dict.items():
            setattr(self, k, v)

    def set_url(self, url):
        self.url = url

    def set_port(self, port):
        self.port = port

    @property
    def url_port(self):
        return self.url + ":" + str(self.port)


eosio_config = EosioConfig()
