"""HTTP contract, signing, calendar expiry and durable fulfillment retries."""
from contextlib import asynccontextmanager
from datetime import datetime,timedelta,timezone
from dataclasses import replace
import asyncio,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import httpx,jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
from license_api.config import Settings
from license_api.main import create_app
from license_api.models import LicenseRequest
from license_api.signing import issue,expiration
from license_tokens import verify_token
from licencias import OfflineLicensing


class ApiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.key=Ed25519PrivateKey.generate();self.api_key='test-api-key-'+'x'*48
        self.settings=Settings(self.api_key,self.key)
        self.public=self.key.public_key().public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo)
        self.now=datetime(2026,1,31,12,30,tzinfo=timezone.utc)
        self.body={'app_id':'registro','tipo_licencia':'mensual','hwid':'a'*64}

    @asynccontextmanager
    async def client(self,**kwargs):
        app=create_app(kwargs.pop('settings',self.settings),clock=lambda:self.now,**kwargs)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://api.test') as client:yield client

    def auth(self,**more):return {'X-API-Key':self.api_key,**more}

    async def test_auth_required_and_both_header_formats_supported(self):
        async with self.client() as c:
            for headers in ({},{'X-API-Key':'incorrecta'},{'Authorization':'Bearer incorrecta'},self.auth(Authorization='Bearer incorrecta')):
                self.assertEqual((await c.post('/generar-licencia',json=self.body,headers=headers)).status_code,401)
            for headers in (self.auth(),{'Authorization':'Bearer '+self.api_key}):
                r=await c.post('/generar-licencia',json=self.body,headers=headers)
                self.assertEqual(r.status_code,200);self.assertEqual(r.headers['Cache-Control'],'no-store')
            self.assertEqual((await c.get('/openapi.json')).status_code,401)
            self.assertEqual((await c.get('/health')).json(),{'estado':'ok'})

    async def test_monthly_yearly_perpetual_exact_output_and_optional_hwid(self):
        async with self.client() as c:
            for kind in ('mensual','anual','perpetua'):
                r=await c.post('/generar-licencia',json={'app_id':'registro','tipo_licencia':kind},headers=self.auth())
                self.assertEqual(r.status_code,200);data=r.json()
                self.assertEqual(set(data),{'licencia_key','fecha_expiracion','estado'})
                verified=verify_token(data['licencia_key'],self.public,'registro','otro-equipo',self.now)
                self.assertEqual(verified['tipo_licencia'],kind)
                self.assertEqual(data['fecha_expiracion'],expiration(self.now,kind).isoformat() if kind!='perpetua' else None)
        self.assertEqual(expiration(self.now,'mensual').day,28)
        self.assertEqual(expiration(datetime(2028,2,29,tzinfo=timezone.utc),'anual'),datetime(2029,2,28,tzinfo=timezone.utc))

    async def test_bad_input_unknown_apps_and_body_limits(self):
        async with self.client() as c:
            for body in ({'app_id':'registro','tipo_licencia':'gratis'},dict(self.body,hwid=''),dict(self.body,courses=['*']),dict(self.body,hwid=17)):
                self.assertEqual((await c.post('/generar-licencia',json=body,headers=self.auth())).status_code,422)
            self.assertEqual((await c.post('/generar-licencia',json=dict(self.body,app_id='no-vendida'),headers=self.auth())).status_code,404)
            self.assertEqual((await c.post('/generar-licencia',content='x'*9000,headers=self.auth())).status_code,413)

    async def test_retry_reuses_exact_token_and_different_order_data_conflicts(self):
        async with self.client() as c:
            headers=self.auth(**{'Idempotency-Key':'venta-000123'})
            first=await c.post('/generar-licencia',json=self.body,headers=headers)
            second=await c.post('/generar-licencia',json=self.body,headers=headers)
            self.assertEqual(first.json(),second.json())
            self.assertEqual((await c.post('/generar-licencia',json=dict(self.body,tipo_licencia='anual'),headers=headers)).status_code,409)

    async def test_supabase_is_written_before_success_and_errors_return_no_key(self):
        inserted=[]
        def handler(request):
            self.assertEqual(request.headers['apikey'],'sb_secret_test')
            self.assertNotIn('authorization',request.headers)
            self.assertEqual(request.url.path,'/rest/v1/licencias')
            if request.method=='GET':return httpx.Response(200,json=[])
            row=json.loads(request.content);inserted.append(row);return httpx.Response(201,json=[row])
        settings=replace(self.settings,supabase_url='https://example.supabase.co',supabase_service_key='sb_secret_test')
        async with self.client(settings=settings,transport=httpx.MockTransport(handler)) as c:
            r=await c.post('/generar-licencia',json=self.body,headers=self.auth())
            self.assertEqual(r.status_code,200);self.assertEqual(inserted[0]['licencia_key'],r.json()['licencia_key'])
        def failed(request):return httpx.Response(500,json={'message':'service-secret-must-not-leak'})
        async with self.client(settings=settings,transport=httpx.MockTransport(failed)) as c:
            r=await c.post('/generar-licencia',json=self.body,headers=self.auth())
            self.assertEqual(r.status_code,503);self.assertNotIn('licencia_key',r.json());self.assertNotIn('must-not-leak',r.text)

    async def test_supabase_race_returns_winning_order_after_duplicate_insert(self):
        record=issue(LicenseRequest(**self.body),self.settings,'pedido-0001',self.now);reads=[]
        def handler(request):
            if request.method=='POST':return httpx.Response(409,json={})
            reads.append(1);return httpx.Response(200,json=[] if len(reads)==1 else [record])
        settings=replace(self.settings,supabase_url='https://example.supabase.co',supabase_service_key='service-role-test')
        async with self.client(settings=settings,transport=httpx.MockTransport(handler)) as c:
            r=await c.post('/generar-licencia',json=self.body,headers=self.auth(**{'Idempotency-Key':'pedido-0001'}))
            self.assertEqual(r.status_code,200);self.assertEqual(r.json()['licencia_key'],record['licencia_key'])

    async def test_desktop_accepts_api_license_and_preserves_old_account_on_restart(self):
        async with self.client() as c:
            token=(await c.post('/generar-licencia',json=self.body,headers=self.auth())).json()['licencia_key']
        with tempfile.TemporaryDirectory() as folder:
            service=OfflineLicensing(folder,self.public,device='a'*64,clock=lambda:self.now,registry=False)
            service.register('Prueba','docente@example.com','ana','ClaveCliente123','secundaria:matematica')
            account=service.state['account_id'];service.import_license(token)
            self.assertTrue(service.can_edit('primaria:comunicacion'))
            restarted=OfflineLicensing(folder,self.public,device='a'*64,clock=lambda:self.now,registry=False)
            self.assertEqual(restarted.state['account_id'],account);self.assertEqual(restarted.status()['mode'],'licencia')
            self.now=datetime(2026,3,5,tzinfo=timezone.utc)
            self.assertNotEqual(restarted.status()['mode'],'licencia')

    async def test_signature_tampering_wrong_device_product_and_expiry_are_rejected(self):
        record=issue(LicenseRequest(**self.body),self.settings,now=self.now);token=record['licencia_key']
        for product,device,now in [('registro','b'*64,self.now),('otra-app','a'*64,self.now),('registro','a'*64,self.now+timedelta(days=40))]:
            with self.assertRaises(ValueError):verify_token(token,self.public,product,device,now)
        claims=jwt.decode(token,options={'verify_signature':False});claims['courses']=['*']
        fake=jwt.encode(claims,Ed25519PrivateKey.generate(),algorithm='EdDSA')
        with self.assertRaises(ValueError):verify_token(fake,self.public,'registro','a'*64,self.now)

    async def test_public_update_endpoint_is_signed_with_the_same_trusted_vendor_key(self):
        from actualizaciones import verify_manifest
        manifest=dict(schema=1,app_id='registro',version='2.4.0',edicion='comercial',plataforma='windows-x64',
            url='https://example.com/setup.exe',sha256='a'*64,bytes=1234)
        settings=replace(self.settings,updates={'registro':manifest})
        async with self.client(settings=settings) as c:
            result=await c.get('/actualizaciones/registro')
            self.assertEqual(result.status_code,200)
            self.assertEqual(verify_manifest(result.json(),self.public,'2.3.0'),manifest)
            self.assertEqual((await c.get('/actualizaciones/otra')).status_code,404)

    async def test_no_missing_secret_fallback_and_no_gui_imports(self):
        with self.assertRaises(ValueError):Settings('',self.key)
        with patch.dict('os.environ',{},clear=True),self.assertRaises(ValueError):Settings.from_env()
        with self.assertRaises(ValueError):replace(self.settings,supabase_url='http://unsafe.example',supabase_service_key='secret')
