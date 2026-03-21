# pyrusult

Rust's `std::result<T, E>` ported to python

## Why?

- I hate exception
- You know which error a function can return
- You know if a function can return an error

## How to use
```python
from pyrusult import Ok, Err, Result, ResultStatus

# Exception based error to store more information
# You can also use an enum like zig
class ExpeditionFailedError(BaseException):
    def __init__(self):
        super().__init__("Expedition Failed")


class ExpeditionAlmostSuccessError(BaseException):
    def __init__(self):
        super().__init__("Expedition almost succeeded")

def test_fn(
    i: int,
) -> Result[int, ExpeditionFailedError | ExpeditionAlmostSuccessError]:
    """A function that can fail in multiple way."""
    if i == 33:
        return Ok(i)
    if i == 60:
        return Err(ExpeditionAlmostSuccessError())
    return Err(ExpeditionFailedError())


def test() -> Result[str, ExpeditionFailedError | ExpeditionAlmostSuccessError]:
    res = test_fn(33)
    if res.status == ResultStatus.Err:
        # Quick check and return
        return res.into() # Have to use .into() here to convert from Err[int, ...] to Err[str, ...]
    res = res.map_err(lambda x: RuntimeError()).map(lambda x: x * 2)
    # res's type is Result[int, RuntimeError]
    res_ok = res.ok()
    assert res_ok is not None and res_ok == 66

    res = test_fn(16)
    # Pattern matching
    match res:
        case Ok(x):
            print("Ok", x)
            assert False
        case Err(e):
            print("Err", e)

    res = test_fn(32)
    # More pattern matching
    match res:
        case Ok(x):
            print("Ok", x)
            assert False
        case Err(ExpeditionFailedError()):
            print("Err 0", res.value)
        case Err(ExpeditionAlmostSuccessError()):
            print("Err 1", res.value)
            assert False

    return Ok("The greatest expedition in the history!")
```

## Why `ResultStatus` but not `bool`?

At first, I used a boolean field `is_err`, when testing, I encountered this:
```
res = test_fn(11)

# res.is_err is a boolean, so naturally you will do this
if res.is_err:
    res.into() #<-- The lsp will scream at you
# The correct way is
if res.is_err == True:
    res.into()
```
I decided to make it an Enum, so you can't use it the wrong way
