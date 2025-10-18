from src.shared.dtos.base import Field, BaseDTO

from . import vn_moh

from enum import Enum
from typing import (
    Any,
    Union,
    Literal,
    Annotated,
    TypeAlias,
)

from fhir.resources.bundle import Bundle
from fhir.resources.medication import Medication


class EHRFormat(str, Enum):
    custom_json = "custom_json"
    fhir = "fhir"
    vn_moh = "vn_moh"


class InputEHR_CustomJSON(BaseDTO):
    type: Literal[EHRFormat.custom_json]
    custom_json: dict[str, Any]


class InputEHR_FHIR(BaseDTO):
    type: Literal[EHRFormat.fhir]
    fhir: Bundle


class InputEHR_VN_MOH(BaseDTO):
    type: Literal[EHRFormat.vn_moh]
    vn_moh: vn_moh.VN_MOH


InputEHR = Annotated[
    Union[InputEHR_CustomJSON, InputEHR_FHIR, InputEHR_VN_MOH],
    Field(discriminator="type"),
]


class InputPrescription_CustomJSON(BaseDTO):
    type: Literal[EHRFormat.custom_json]
    custom_json: list[dict[str, Any]]


class InputPrescription_FHIR(BaseDTO):
    type: Literal[EHRFormat.fhir]
    fhir: list[Medication]


class InputPrescription_VN_MOH(BaseDTO):
    type: Literal[EHRFormat.vn_moh]
    vn_moh: list[vn_moh.ChiTietThuoc]


InputPrescription: TypeAlias = Annotated[
    Union[
        InputPrescription_CustomJSON,
        InputPrescription_FHIR,
        InputPrescription_VN_MOH,
    ],
    Field(discriminator="type"),
]
