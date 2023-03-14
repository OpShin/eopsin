"""
A more complicated example of a program
This program will loop through all the numbers from 0 to n
and compute the fibonacci numbers on the way.

Try it out!

```bash
(venv) $ eopsin eval examples/a_introduction/d_fib_iter.py '{"int": 3}'
> Starting execution
> ------------------
> 0
> 1
> 2
> ------------------
> 2
```
"""


def fib(n: int) -> int:
    if n == 0:
        res = 0
    elif n == 1:
        res = 1
    else:
        res = fib(n - 1) + fib(n - 2)
    return res


def validator(n: int) -> int:
    return fib(n)
