class IllegalKey(Exception):
    pass


class CantFindRecId(Exception):
    pass


class CantFindResInPack(Exception):
    pass


class ErrInputParams(Exception):
    def __str__(self):
        return "Please check the input Should be like this 'eosio.token@active'"
