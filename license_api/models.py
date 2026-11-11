from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,field_validator
from license_tokens import APP_PATTERN


class LicenseRequest(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    app_id:str=Field(pattern='^'+APP_PATTERN+'$')
    tipo_licencia:Literal['mensual','anual','perpetua']
    hwid:str|None=Field(default=None,max_length=256)

    @field_validator('hwid')
    @classmethod
    def valid_hwid(cls,value):
        if value is not None and (not value or value!=value.strip() or any(ord(c)<33 or ord(c)>126 for c in value)):
            raise ValueError('Omita hwid para una licencia sin vinculación; si lo envía debe ser un identificador válido.')
        return value


class LicenseResponse(BaseModel):
    licencia_key:str
    fecha_expiracion:str|None
    estado:Literal['exito']='exito'
