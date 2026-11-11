"""Supabase writes complete before a license is returned; retries reuse an order."""
import asyncio
import httpx


class StorageUnavailable(Exception):pass
class OrderConflict(Exception):pass


class MemoryStore:
    """For local/stateless use only. Supabase provides persistence across restarts."""
    def __init__(self):self.records={};self.lock=asyncio.Lock()

    async def find(self,key):return self.records.get(key) if key else None

    async def insert(self,record):
        async with self.lock:
            key=record['idempotency_key']
            if key and key in self.records:
                current=self.records[key]
                if current['request_hash']!=record['request_hash']:raise OrderConflict
                return current
            if key:self.records[key]=dict(record)
            return record


class SupabaseStore:
    def __init__(self,url,key,client):
        self.url=url.rstrip('/')+'/rest/v1/licencias';self.client=client
        self.headers={'apikey':key,'Prefer':'return=representation'}
        if not key.startswith('sb_secret_'):self.headers['Authorization']='Bearer '+key

    async def find(self,key):
        if not key:return None
        try:
            result=await self.client.get(self.url,params={'idempotency_key':'eq.'+key,'select':'*','limit':'1'},headers=self.headers)
            result.raise_for_status();rows=result.json()
            if not isinstance(rows,list):raise ValueError
            return rows[0] if rows else None
        except (httpx.HTTPError,ValueError,KeyError):raise StorageUnavailable from None

    async def insert(self,record):
        try:
            result=await self.client.post(self.url,json=record,headers=self.headers)
            if result.status_code==409 and record['idempotency_key']:
                existing=await self.find(record['idempotency_key'])
                if existing:
                    if existing['request_hash']!=record['request_hash']:raise OrderConflict
                    return existing
            result.raise_for_status();rows=result.json()
            if not isinstance(rows,list) or len(rows)!=1 or rows[0].get('id')!=record['id']:raise ValueError
            return rows[0]
        except (httpx.HTTPError,ValueError,KeyError):raise StorageUnavailable from None
