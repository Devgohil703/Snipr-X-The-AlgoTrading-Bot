import MetaTrader5 as mt5

print('initialize:', mt5.initialize())
print('init_err:', mt5.last_error())
print('login:', mt5.login(login=12345678, password='xxxxxxxx', server='MetaQuotes-Demo'))
print('login_err:', mt5.last_error())
mt5.shutdown()
