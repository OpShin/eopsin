"""
A re-implementation of a * b, this time with a while loop.

Try it out!

```bash
(venv) $ eopsin eval examples/a_introduction/c_mult_while.py '{"int": 3}' '{"int": 4}'
> Starting execution
> ------------------
> ------------------
> 12
```
"""


def validator(a: int, b: int) -> int:
    # trivial implementation of c = a * b
    c = 0
    # in a while-loop we check the condition and execute the inner body while it evaluates to True
    while 0 < b:
        # we update the values of c and b here
        c += a
        b -= 1
    return c
