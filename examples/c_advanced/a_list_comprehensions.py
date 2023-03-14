"""
We can branch the control flow using if/else
Also you can write more efficient loops with so-called list comprehensions

Try it out!

```bash
(venv) $ eopsin eval examples/a_introduction/a_list_comprehensions.py '{"int": 3}' '{"int": 0}'
> Starting execution
> ------------------
> ------------------
> [0, 1, 4]
```
"""
from eopsin.prelude import *


def validator(n: int, even: bool) -> List[int]:
    if even:
        # generate even squares
        res = [k * k for k in range(n) if k % 2 == 0]
    else:
        # generate all squares
        res = [k * k for k in range(n)]
    return res
