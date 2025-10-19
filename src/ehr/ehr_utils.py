from src.shared.utils import dict_utils
from src.shared.utils.logger import LOGGER

from .dtos import EHRFormat
from .vn_moh import toDateTime
from .custom_types import EHRDict

from typing import Any


def prune_and_preprocess_input_ehr(ehr_dict: EHRDict) -> EHRDict:
    """Prune empty values and do some preprocessing.

    - convert vn_moh datetime format to YYYY/MM/DD HH:MM
    """
    match ehr_dict.type:
        case EHRFormat.custom_json:
            pruned_ehr = dict_utils.remove_empty_and_none_recursive(
                ehr_dict.content
            )
        case EHRFormat.vn_moh:
            pruned_ehr = dict_utils.remove_empty_and_none_recursive(
                ehr_dict.content
            )
            convert_datetime(pruned_ehr)
        case EHRFormat.fhir:
            pruned_ehr = ehr_dict.content
    return EHRDict(type=ehr_dict.type, content=pruned_ehr)


def convert_datetime(d: dict[str, Any]):
    """Recursively find and convert value of datetime keys (start with or end with "ngay", but not "so_ngay") to YYYY/MM/DD HH:MM
    Modify inplace
    """
    d = d.copy()
    for k in d.keys():
        if isinstance(d[k], dict):
            d[k] = convert_datetime(d[k])
        elif isinstance(d[k], list) and d[k] and isinstance(d[k][0], dict):
            d[k] = [convert_datetime(it) for it in d[k]]
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
