"""
eopsin is strictly typed! Take care that your types match. The compiler will guide you there.

Try it out!

```bash
(venv) $ eopsin eval examples/a_introduction/g_strict_typing.py '{"int": 3}'
Traceback (most recent call last):
  File "/git/eopsin-lang/venv/bin/eopsin", line 33, in <module>
    sys.exit(load_entry_point('eopsin-lang', 'console_scripts', 'eopsin')())
  File "/git/eopsin-lang/eopsin/__main__.py", line 140, in main
    raise SyntaxError(
  File "examples/a_introduction/g_strict_typing.py", line 14
    if "s" == 4:
      ^
NotImplementedError: Comparison Eq for StringType and IntegerType is not implemented. This is likely intended because it would always evaluate to False.
Note that eopsin errors may be overly restrictive as they aim to prevent code with unintended consequences.

```
"""


def validator(value: int) -> bytes:
    # eopsin is strictly typed! This comparison is invalid, strings ant integers can not be compared
    if "s" == value:
        print("test")
    return b""
