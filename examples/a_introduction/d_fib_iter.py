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


def validator(n: int) -> int:
    a, b = 0, 1
    for i in range(n):
        # due to strict typing, we need to first convert the integer to a string by calling str(..)
        print(str(i))
        # this updates and re-assigns values in a tuple-like fashion
        a, b = b, a + b
    return a
