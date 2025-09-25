from src.dtos.ehr import EHRFormat, InputEHR, InputPrescription

from dataclasses import dataclass
from typing import Any, cast


# This type has to be kept in sync with src.dtos.ehr.InputEHR
@dataclass
class EHRDict:
    type: EHRFormat
    content: dict[str, Any]

    @staticmethod
    def from_input_ehr(input_ehr: InputEHR) -> "EHRDict":
        match input_ehr.type:
            case EHRFormat.custom_json:
                assert input_ehr.custom_json
                d = input_ehr.custom_json
            case EHRFormat.vn_moh:
                d = cast(dict[str, Any], input_ehr.vn_moh)
            case EHRFormat.fhir:
                d = input_ehr.fhir.model_dump()
        return EHRDict(type=input_ehr.type, content=d)


@dataclass
class PrescriptionDict:
    type: EHRFormat
    content: list[dict[str, Any]]

    @staticmethod
    def from_input_prescription(
        input_ehr: InputPrescription,
    ) -> "PrescriptionDict":
        match input_ehr.type:
            case EHRFormat.custom_json:
                assert input_ehr.custom_json
                d = input_ehr.custom_json
            case EHRFormat.vn_moh:
                d = cast(list[dict[str, Any]], input_ehr.vn_moh)
            case EHRFormat.fhir:
                d = [medication.model_dump() for medication in input_ehr.fhir]

        return PrescriptionDict(type=input_ehr.type, content=d)
