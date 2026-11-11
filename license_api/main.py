"""POST /generar-licencia: no GUI and no vendor secrets in client applications."""
from contextlib import asynccontextmanager
from datetime import datetime,timezone
import hmac,re
import httpx
from fastapi import FastAPI,Request,HTTPException,Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.security import APIKeyHeader,HTTPBearer
from .config import Settings
from .models import LicenseRequest,LicenseResponse
from .signing import issue,response,request_hash
from .store import MemoryStore,SupabaseStore,StorageUnavailable,OrderConflict

key_header=APIKeyHeader(name='X-API-Key',auto_error=False)
bearer_header=HTTPBearer(auto_error=False)


def create_app(settings=None,store=None,transport=None,clock=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.settings=settings or Settings.from_env()
        async with httpx.AsyncClient(timeout=12,follow_redirects=False,transport=transport) as client:
            config=app.state.settings
            app.state.store=store or (SupabaseStore(config.supabase_url,config.supabase_service_key,client) if config.supabase_url else MemoryStore())
            yield

    app=FastAPI(title='API de licencias comerciales',version='1.0.0',lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)

    @app.middleware('http')
    async def private_response(request,call_next):
        if request.method=='POST':
            try:
                if int(request.headers.get('content-length','0'))>8192:return JSONResponse({'estado':'error','detalle':'Petición demasiado grande.'},status_code=413)
            except ValueError:return JSONResponse({'estado':'error','detalle':'Tamaño de petición inválido.'},status_code=400)
            content=bytearray()
            async for chunk in request.stream():
                content.extend(chunk)
                if len(content)>8192:return JSONResponse({'estado':'error','detalle':'Petición demasiado grande.'},status_code=413)
            request._body=bytes(content)
        result=await call_next(request)
        result.headers['Cache-Control']='no-store';result.headers['X-Content-Type-Options']='nosniff'
        return result

    async def authenticate(request:Request,key=Depends(key_header),bearer=Depends(bearer_header)):
        expected=request.app.state.settings.api_key
        supplied=[v for v in (key,bearer.credentials if bearer else None) if v is not None]
        if not supplied or any(not hmac.compare_digest(v.encode(),expected.encode()) for v in supplied):
            raise HTTPException(401,'API_KEY o Bearer Token no válido.',headers={'WWW-Authenticate':'Bearer'})

    @app.exception_handler(HTTPException)
    async def http_error(request,exc):return JSONResponse({'estado':'error','detalle':exc.detail},status_code=exc.status_code,headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request,exc):
        return JSONResponse({'estado':'error','detalle':'Revise app_id, tipo_licencia y hwid. No se admiten campos adicionales.'},status_code=422)

    @app.get('/health')
    async def health():return {'estado':'ok'}

    @app.get('/openapi.json',dependencies=[Depends(authenticate)],include_in_schema=False)
    async def schema():return app.openapi()

    @app.post('/generar-licencia',response_model=LicenseResponse,dependencies=[Depends(authenticate)])
    async def generate(body:LicenseRequest,request:Request):
        config=request.app.state.settings;ledger=request.app.state.store
        if body.app_id not in config.apps:raise HTTPException(404,'app_id no registrado en el catálogo del vendedor.')
        order=request.headers.get('Idempotency-Key')
        if order is not None and not re.fullmatch(r'[A-Za-z0-9._:-]{8,128}',order):raise HTTPException(422,'Idempotency-Key debe identificar el pedido con entre 8 y 128 caracteres.')
        try:
            existing=await ledger.find(order)
            if existing:
                if existing['request_hash']!=request_hash(body):raise OrderConflict
                return response(existing)
            record=issue(body,config,order,clock() if clock else datetime.now(timezone.utc))
            return response(await ledger.insert(record))
        except StorageUnavailable:raise HTTPException(503,'No se pudo confirmar el guardado de la licencia. Reintente con el mismo Idempotency-Key.') from None
        except OrderConflict:raise HTTPException(409,'Este Idempotency-Key ya corresponde a otro pedido.') from None

    @app.get('/actualizaciones/{app_id}')
    async def update(app_id:str,request:Request):
        config=request.app.state.settings
        if app_id not in config.apps or app_id not in config.updates:raise HTTPException(404,'No hay una actualización publicada para esta aplicación.')
        from actualizaciones import sign_manifest
        return sign_manifest({**config.updates[app_id],'app_id':app_id},config.private_key)

    return app


app=create_app()
