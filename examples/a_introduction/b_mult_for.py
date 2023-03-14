"""
A re-implementation of a * b
This program will loop through all the numbers from 0 to b
and sum the values up

Try it out!

```bash
(venv) $ eopsin eval examples/a_introduction/b_mult_for.py '{"int": 3}' '{"int": 4}'
> Starting execution
> Starting execution
> ------------------
> 0
> 1
> 2
> 3
> ------------------
> 12
```
"""


def validator(a: int, b: int) -> int:
    # trivial implementation of c = a * b

    # We initialize the variable with a default
    c = 0
    # Now loop through all numbers from 0 to b (range creates the list [0, 1, 2, ...])
    for i in range(b):
        # for debugging purposes, you can print the number
        # Note: we convert the `int` to a  `str` by calling `str(...)` - print only prints strings!
        print(str(i))
        # and we update the value of c in every iteration
        c += a
    return c
