"""
A very basic eopsin program
it does nothing, takes only one parameter and returns nothing

When executed, it will print "Hello World!" to the console!

Try it out!

```bash
(venv) $ eopsin eval examples/a_introduction/a_hello_world.py '{"int": 0}'
> Starting execution
> ------------------
> Hello world!
> ------------------
> None
```
"""


def validator(_: None) -> None:
    # print a string into the debug console
    print("Hello world!")
