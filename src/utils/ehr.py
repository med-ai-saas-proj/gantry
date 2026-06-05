from .dict_utils import DictUtils
from .logger import LOGGER
from src.custom_types.ehr import EHRDict

from patient_record_processing import toDateTime
from typing import Any


class EHRUtils:

    @staticmethod
    def prune_and_preprocess_input_ehr(ehr_dict: EHRDict) -> EHRDict:
        """
        Prune empty values and do some preprocessing:
            - convert vn_moh datetime format to YYYY/MM/DD HH:MM
        """
        match ehr_dict.type:
            case "custom_json":
                pruned_ehr = DictUtils.remove_empty_and_none_recursive(
                    ehr_dict.content
                )
            case "vn_moh":
                pruned_ehr = DictUtils.remove_empty_and_none_recursive(
                    ehr_dict.content
                )
                EHRUtils.convert_datetime(pruned_ehr)
            case "fhir":
                pruned_ehr = ehr_dict.content
        return EHRDict(type=ehr_dict.type, content=pruned_ehr)

    @staticmethod
    def convert_datetime(d: dict[str, Any]):
        """
        Recursively find and convert value of datetime keys (start with or end with "ngay", but not "so_ngay") to YYYY/MM/DD HH:MM
        Modify inplace
        """
        d = d.copy()
        for k in d.keys():
            if isinstance(d[k], dict):
                d[k] = EHRUtils.convert_datetime(d[k])
            elif isinstance(d[k], list) and d[k] and isinstance(d[k][0], dict):
                d[k] = [EHRUtils.convert_datetime(it) for it in d[k]]
            elif (
                k.startswith("ngay") or k.endswith("ngay")
            ) and "so_ngay" not in k:
                try:
                    d[k] = toDateTime(d[k])
                except Exception as e:
                    LOGGER.debug(
                        "Error when trying to convert ehr's datetime",
                        error=str(e),
                    )
                    pass
