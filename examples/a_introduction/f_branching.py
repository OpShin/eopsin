"""
We can branch the control flow using if/else
You can pass boolean values into the contract by passing integers with 0/1

Try it out!

```bash
(venv) $ eopsin eval examples/a_introduction/f_branching.py '{"int": 3}' '{"int": 0}'
> Starting execution
> ------------------
> ------------------
> 9
(venv) $ eopsin eval examples/a_introduction/f_branching.py '{"int": 3}' '{"int": 1}'
> Starting execution
> ------------------
> ------------------
> 6

```
"""


def validator(n: int, even: bool) -> int:
    if even:
        res = 2 * n
    else:
        res = 3 * n
    return res
