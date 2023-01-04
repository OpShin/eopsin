Eopsin
======

This is a prototypical implementation of smart contracts
for Cardano which are written in a very strict subset of valid Python.
The general philosphy of this project is to write a compiler that 
ensure the following:

If the program compiles then:
1. it is a valid Python program
2. the output running it with python is the same as running it on-chain.

This specificially means that _not every valid python program is a valid smart contract_.
Not all language features of python will or can be supported.
The reasons are mainly of practical nature (i.e. we can't infer types when functions like `eval` are allowed).

Specifically, only a pure subset of python is allowed.
Further, only immutable objects may be generated.

For your program to be accepted, make sure to only make use of language constructs supported by the compiler.
You will be notified of which constructs are not supported when trying to compile.

## Architecture

This program consists of a few independent components:
1. An aggressive static type inferencer
2. Rewriting tools to simplify complex python expressions
3. A compiler from a subset of python into UPLC

## Running

Write your program in python. You may start with the `example.py`.
Then run 
```bash
python3 -m eopsin compile example.py
```

> Note: this is the final desired state. I am currently too lazy to both with setting up the module so just put your code into the string at `test.py` and run `python3 test.py`


## Name

> Eopsin (Korean: 업신; Hanja: 業神) is the goddess of the storage and wealth in Korean mythology and shamanism. [[1]](https://en.wikipedia.org/wiki/Eopsin)

Since this tries to merge Python (a large serpent) and Pluto/Plutus (Greek wealth gods), the name appears fitting.
Also there are no naming conflicts.