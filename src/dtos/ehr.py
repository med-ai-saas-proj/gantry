from .base import BaseDTO, Field
from typing import Any, Literal, Union, Annotated, TypeAlias
from fhir.resources.bundle import Bundle
from fhir.resources.medication import Medication
from patient_record_processing.schemas.vn_moh import flat

SupportedEHRFormat = Literal["custom_json", "fhir", "vn_moh"]


class InputEHR_CustomJSON(BaseDTO):
    type: Literal["custom_json"]
    custom_json: dict[str, Any]


class InputEHR_FHIR(BaseDTO):
    type: Literal["fhir"]
    fhir: Bundle


class InputEHR_VN_MOH(BaseDTO):
    type: Literal["vn_moh"]
    vn_moh: flat.VN_MOH


InputEHR: TypeAlias = Annotated[
    Union[InputEHR_CustomJSON, InputEHR_FHIR, InputEHR_VN_MOH],
    Field(discriminator="type"),
]


class InputPrescription_CustomJSON(BaseDTO):
    type: Literal["custom_json"]
    custom_json: list[dict[str, Any]]


class InputPrescription_FHIR(BaseDTO):
    type: Literal["fhir"]
    fhir: list[Medication]


class InputPrescription_VN_MOH(BaseDTO):
    type: Literal["vn_moh"]
    vn_moh: list[flat.ChiTietThuoc]


InputPrescription: TypeAlias = Annotated[
    Union[
        InputPrescription_CustomJSON,
        InputPrescription_FHIR,
        InputPrescription_VN_MOH,
    ],
    Field(discriminator="type"),
]
