import urllib
import urllib.request as ur
import json
from utils import utils
from decimal import *

grlcpriceurl = 'https://api.coingecko.com/api/v3/simple/price?ids=garlicoin&vs_currencies=usd'

utils = utils()
cursor = utils.get_mysql_cursor()

sql = "TRUNCATE TABLE rates"
cursor.execute(sql)

response = ur.urlopen(grlcpriceurl)
data = json.loads(response.read())
grlcprice = round(Decimal(data['garlicoin']['usd']),8)

sql = "INSERT INTO rates (pair,rate) VALUES (%s, %s)"
pair = "GRLC/USD"
rate = grlcprice
cursor.execute(sql, (pair,rate,))
