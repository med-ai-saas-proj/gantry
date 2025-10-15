from typing import TypedDict, Union, Literal


class AddOp(TypedDict):
    op: Literal["add"]
    path: str
    value: object


class RemoveOp(TypedDict):
    op: Literal["remove"]
    path: str


class ReplaceOp(TypedDict):
    op: Literal["replace"]
    path: str
    value: object


MoveOp = TypedDict("MoveOp", {"op": Literal["move"], "from": str, "path": str})

CopyOp = TypedDict("CopyOp", {"op": Literal["copy"], "from": str, "path": str})


class TestOp(TypedDict):
    op: Literal["test"]
    path: str
    value: object


JsonPatchOp = Union[AddOp, RemoveOp, ReplaceOp, MoveOp, CopyOp, TestOp]
JsonPatch = list[JsonPatchOp]
