from pymemcache.client import base

client = base.Client(('localhost',11211))

client.set('id','{"id":"sas"}')

print(client.get('id').decode("utf-8"))