from enum import Enum
from ast import parse

from .type_inference import *
from .rewrite_tuple_assign import RewriteTupleAssign
from .rewrite_augassign import RewriteAugAssign
from .rewrite_import_plutusdata import RewriteImportPlutusData
from .rewrite_import_dataclasses import RewriteImportDataclasses
from .rewrite_import_typing import RewriteImportTyping
from .rewrite_import import RewriteImport
from .rewrite_in import RewriteIn

import pluthon as plt

STATEMONAD = "s"


BinOpMap = {
    Add: {
        IntegerInstanceType: {
            IntegerInstanceType: plt.AddInteger,
        },
        ByteStringInstanceType: {
            ByteStringInstanceType: plt.AppendString,
        },
    },
    Sub: {
        IntegerInstanceType: {
            IntegerInstanceType: plt.SubtractInteger,
        }
    },
    Mult: {
        IntegerInstanceType: {
            IntegerInstanceType: plt.MultiplyInteger,
        }
    },
    Div: {
        IntegerInstanceType: {
            IntegerInstanceType: plt.DivideInteger,
        }
    },
    Mod: {
        IntegerInstanceType: {
            IntegerInstanceType: plt.ModInteger,
        }
    },
}

CmpMap = {
    Eq: {
        IntegerInstanceType: {
            IntegerInstanceType: plt.EqualsInteger,
        },
        ByteStringInstanceType: {
            ByteStringInstanceType: plt.EqualsByteString,
        },
        StringInstanceType: {
            StringInstanceType: plt.EqualsString,
        },
        BoolInstanceType: {
            BoolInstanceType: plt.EqualsBool,
        },
    },
    Lt: {
        IntegerInstanceType: {
            IntegerInstanceType: plt.LessThanInteger,
        },
        ByteStringInstanceType: {
            ByteStringInstanceType: plt.LessThanByteString,
        },
    },
}

TransformExtParamsMap = {
    IntegerInstanceType: lambda x: plt.UnIData(x),
    ByteStringInstanceType: lambda x: plt.UnBData(x),
    StringInstanceType: lambda x: plt.DecodeUtf8(plt.UnBData(x)),
    UnitInstanceType: lambda x: plt.Lambda(["_"], plt.Unit()),
    BoolInstanceType: lambda x: plt.NotEqualsInteger(x, plt.Integer(0)),
}


def transform_ext_params_map(p: Type):
    assert isinstance(
        p, InstanceType
    ), "Can only transform instances, not classes as input"
    if p in TransformExtParamsMap:
        return TransformExtParamsMap[p]
    if isinstance(p.typ, ListType):
        list_int_typ = p.typ.typ
        return lambda x: plt.MapList(
            plt.UnListData(x),
            plt.Lambda(["x"], transform_ext_params_map(list_int_typ)(plt.Var("x"))),
        )
    if isinstance(p.typ, DictType):
        # TODO also remap in the style the list is mapped (but on pairs)
        return plt.UnMapData
    return lambda x: x


TransformOutputMap = {
    StringInstanceType: lambda x: plt.BData(plt.EncodeUtf8(x)),
    IntegerInstanceType: lambda x: plt.IData(x),
    ByteStringInstanceType: lambda x: plt.BData(x),
    UnitInstanceType: lambda x: plt.Lambda(["_"], plt.Unit()),
    BoolInstanceType: lambda x: plt.IData(
        plt.IfThenElse(x, plt.Integer(1), plt.Integer(0))
    ),
}


def transform_output_map(p: Type):
    assert isinstance(
        p, InstanceType
    ), "Can only transform instances, not classes as input"
    if p in TransformOutputMap:
        return TransformOutputMap[p]
    if isinstance(p.typ, ListType):
        list_int_typ = p.typ.typ
        return lambda x: plt.ListData(
            plt.MapList(
                x, plt.Lambda(["x"], transform_output_map(list_int_typ)(plt.Var("x")))
            ),
        )
    if isinstance(p.typ, DictType):
        # TODO also remap in the style the list is mapped as input
        return plt.MapData
    return lambda x: x


ConstantMap = {
    str: plt.Text,
    bytes: lambda x: plt.ByteString(x),
    int: lambda x: plt.Integer(x),
    bool: plt.Bool,
    type(None): lambda _: plt.NoneData(),
}


def extend_statemonad(
    names: typing.List[str],
    values: typing.List[plt.AST],
    old_statemonad: plt.FunctionalMap,
):
    return plt.FunctionalMapExtend(old_statemonad, [n.encode() for n in names], values)


class PythonBuiltIn(Enum):
    print = plt.Lambda(
        ["f", "x", STATEMONAD],
        plt.Trace(plt.Var("x"), plt.NoneData()),
    )
    range = plt.Lambda(
        ["f", "limit", STATEMONAD],
        plt.Range(plt.Var("limit")),
    )


INITIAL_STATE = plt.FunctionalMapExtend(
    plt.FunctionalMap(),
    [b.name for b in PythonBuiltIn],
    [b.value for b in PythonBuiltIn],
)


class UPLCCompiler(NodeTransformer):
    """
    Expects a TypedAST and returns UPLC/Pluto like code
    """

    def visit(self, node):
        """Visit a node."""
        node_class_name = node.__class__.__name__
        if node_class_name.startswith("Typed"):
            node_class_name = node_class_name[len("Typed") :]
        method = "visit_" + node_class_name
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def visit_sequence(self, node_seq: typing.List[typedstmt]) -> plt.AST:
        s = plt.Var(STATEMONAD)
        for n in node_seq:
            compiled_stmt = self.visit(n)
            s = plt.Apply(compiled_stmt, s)
        return plt.Lambda([STATEMONAD], s)

    def visit_BinOp(self, node: TypedBinOp) -> plt.AST:
        opmap = BinOpMap.get(type(node.op))
        if opmap is None:
            raise NotImplementedError(f"Operation {node.op} is not implemented")
        opmap2 = opmap.get(node.left.typ)
        if opmap2 is None:
            raise NotImplementedError(
                f"Operation {node.op} is not implemented for left type {node.left.typ}"
            )
        op = opmap2.get(node.right.typ)
        if opmap2 is None:
            raise NotImplementedError(
                f"Operation {node.op} is not implemented for left type {node.left.typ} and right type {node.right.typ}"
            )
        return plt.Lambda(
            [STATEMONAD],
            op(
                plt.Apply(self.visit(node.left), plt.Var(STATEMONAD)),
                plt.Apply(self.visit(node.right), plt.Var(STATEMONAD)),
            ),
        )

    def visit_Compare(self, node: Compare) -> plt.AST:
        assert len(node.ops) == 1, "Only single comparisons are supported"
        assert len(node.comparators) == 1, "Only single comparisons are supported"
        opmap = CmpMap.get(type(node.ops[0]))
        if opmap is None:
            raise NotImplementedError(f"Operation {node.ops[0]} is not implemented")
        opmap2 = opmap.get(node.left.typ)
        if opmap2 is None:
            raise NotImplementedError(
                f"Operation {node.ops[0]} is not implemented for left type {node.left.typ}"
            )
        op = opmap2.get(node.comparators[0].typ)
        if op is None:
            raise NotImplementedError(
                f"Operation {node.ops[0]} is not implemented for left type {node.left.typ} and right type {node.comparators[0].typ}"
            )
        return plt.Lambda(
            [STATEMONAD],
            op(
                plt.Apply(self.visit(node.left), plt.Var(STATEMONAD)),
                plt.Apply(self.visit(node.comparators[0]), plt.Var(STATEMONAD)),
            ),
        )

    def visit_Module(self, node: TypedModule) -> plt.AST:
        # find main function
        # TODO can use more sophisiticated procedure here i.e. functions marked by comment
        main_fun: typing.Optional[InstanceType] = None
        for s in node.body:
            if isinstance(s, FunctionDef) and s.name == "validator":
                main_fun = s
        assert main_fun is not None, "Could not find function named validator"
        main_fun_typ: FunctionType = main_fun.typ.typ
        assert isinstance(
            main_fun_typ, FunctionType
        ), "Variable named validator is not of type function"
        cp = plt.Program(
            "1.0.0",
            plt.Lambda(
                [f"p{i}" for i, _ in enumerate(main_fun_typ.argtyps)],
                transform_output_map(main_fun_typ.rettyp)(
                    plt.Let(
                        [
                            ("s", INITIAL_STATE),
                            (
                                "g",
                                plt.FunctionalMapAccess(
                                    plt.Apply(
                                        self.visit_sequence(node.body), plt.Var("s")
                                    ),
                                    plt.ByteString("validator".encode("utf8")),
                                    plt.TraceError("NameError"),
                                ),
                            ),
                        ],
                        plt.Apply(
                            plt.Var("g"),
                            plt.Var("g"),
                            *[
                                transform_ext_params_map(a)(plt.Var(f"p{i}"))
                                for i, a in enumerate(main_fun_typ.argtyps)
                            ],
                            plt.Var("s"),
                        ),
                    ),
                ),
            ),
        )
        return cp

    def visit_Constant(self, node: TypedConstant) -> plt.AST:
        plt_type = ConstantMap.get(type(node.value))
        if plt_type is None:
            raise NotImplementedError(
                f"Constants of type {type(node.value)} are not supported"
            )
        return plt.Lambda([STATEMONAD], plt_type(node.value))

    def visit_NoneType(self, _: typing.Optional[typing.Any]) -> plt.AST:
        return plt.Lambda([STATEMONAD], plt.NoneData())

    def visit_Assign(self, node: TypedAssign) -> plt.AST:
        assert (
            len(node.targets) == 1
        ), "Assignments to more than one variable not supported yet"
        assert isinstance(
            node.targets[0], Name
        ), "Assignments to other things then names are not supported"
        if isinstance(node.targets[0].typ, ClassType):
            # Assigning a class type to another class type is equivalent to a ClassDef - a nop
            return self.visit_sequence([])
        compiled_e = self.visit(node.value)
        # (\{STATEMONAD} -> (\x -> if (x ==b {self.visit(node.targets[0])}) then ({compiled_e} {STATEMONAD}) else ({STATEMONAD} x)))
        return plt.Lambda(
            [STATEMONAD],
            plt.FunctionalMapExtend(
                plt.Var(STATEMONAD),
                [node.targets[0].id],
                [plt.Apply(compiled_e, plt.Var(STATEMONAD))],
            ),
        )

    def visit_Name(self, node: TypedName) -> plt.AST:
        # depending on load or store context, return the value of the variable or its name
        if isinstance(node.ctx, Load):
            return plt.Lambda(
                [STATEMONAD],
                plt.FunctionalMapAccess(
                    plt.Var(STATEMONAD),
                    plt.ByteString(node.id.encode()),
                    plt.TraceError("NameError"),
                ),
            )
        raise NotImplementedError(f"Context {node.ctx} not supported")

    def visit_Expr(self, node: TypedExpr) -> plt.AST:
        # we exploit UPLCs eager evaluation here
        # the expression is computed even though its value is eventually discarded
        # Note this really only makes sense for Trace
        return plt.Lambda(
            [STATEMONAD],
            plt.Apply(
                plt.Lambda(["_"], plt.Var(STATEMONAD)),
                plt.Apply(self.visit(node.value), plt.Var(STATEMONAD)),
            ),
        )

    def visit_Call(self, node: TypedCall) -> plt.AST:
        # compiled_args = " ".join(f"({self.visit(a)} {STATEMONAD})" for a in node.args)
        # return rf"(\{STATEMONAD} -> ({self.visit(node.func)} {compiled_args})"
        return plt.Lambda(
            [STATEMONAD],
            plt.Let(
                [("g", plt.Apply(self.visit(node.func), plt.Var(STATEMONAD)))],
                plt.Apply(
                    plt.Var("g"),
                    # pass the function to itself for recursion
                    plt.Var("g"),
                    # pass in all arguments evaluated with the statemonad
                    *(plt.Apply(self.visit(a), plt.Var(STATEMONAD)) for a in node.args),
                    # eventually pass in the state monad as well
                    plt.Var(STATEMONAD),
                ),
            ),
        )

    def visit_FunctionDef(self, node: TypedFunctionDef) -> plt.AST:
        body = node.body.copy()
        if not isinstance(body[-1], Return):
            tr = Return(None)
            tr.typ = NoneInstanceType
            assert (
                node.typ.typ.rettyp == NoneInstanceType
            ), "Function has no return statement but is supposed to return not-None value"
            body.append(tr)
        compiled_body = self.visit_sequence(body[:-1])
        compiled_return = self.visit(body[-1].value)
        args_state = plt.FunctionalMapExtend(
            plt.Var(STATEMONAD),
            # under the name of the function, it can access itself
            [node.name] + [a.arg for a in node.args.args],
            [plt.Var("f")] + [plt.Var(f"p{i}") for i in range(len(node.args.args))],
        )
        return plt.Lambda(
            [STATEMONAD],
            plt.FunctionalMapExtend(
                plt.Var(STATEMONAD),
                [node.name],
                [
                    plt.Lambda(
                        # expect the statemonad again -> this is the basis for internally available values
                        ["f"]
                        + [f"p{i}" for i in range(len(node.args.args))]
                        + [STATEMONAD],
                        plt.Apply(
                            compiled_return,
                            plt.Apply(
                                compiled_body,
                                args_state,
                            ),
                        ),
                    )
                ],
            ),
        )

    def visit_While(self, node: TypedWhile) -> plt.AST:
        compiled_c = self.visit(node.test)
        compiled_s = self.visit_sequence(node.body)
        if node.orelse:
            # If there is orelse, transform it to an appended sequence (TODO check if this is correct)
            cn = copy(node)
            cn.orelse = []
            return self.visit_sequence([cn] + node.orelse)
        # return rf"(\{STATEMONAD} -> let g = (\s f -> if ({compiled_c} s) then f ({compiled_s} s) f else s) in (g {STATEMONAD} g))"
        return plt.Lambda(
            [STATEMONAD],
            plt.Let(
                bindings=[
                    (
                        "g",
                        plt.Lambda(
                            ["s", "f"],
                            plt.Ite(
                                plt.Apply(compiled_c, plt.Var("s")),
                                plt.Apply(
                                    plt.Var("f"),
                                    plt.Apply(compiled_s, plt.Var("s")),
                                    plt.Var("f"),
                                ),
                                plt.Var("s"),
                            ),
                        ),
                    ),
                ],
                term=plt.Apply(plt.Var("g"), plt.Var(STATEMONAD), plt.Var("g")),
            ),
        )

    def visit_For(self, node: TypedFor) -> plt.AST:
        if node.orelse:
            # If there is orelse, transform it to an appended sequence (TODO check if this is correct)
            cn = copy(node)
            cn.orelse = []
            return self.visit_sequence([cn] + node.orelse)
        assert isinstance(node.iter.typ, InstanceType)
        if isinstance(node.iter.typ.typ, ListType):
            assert isinstance(
                node.target, Name
            ), "Can only assign value to singleton element"
            return plt.Lambda(
                [STATEMONAD],
                plt.FoldList(
                    plt.Apply(self.visit(node.iter), plt.Var(STATEMONAD)),
                    plt.Lambda(
                        [STATEMONAD, "e"],
                        plt.Apply(
                            self.visit_sequence(node.body),
                            plt.FunctionalMapExtend(
                                plt.Var(STATEMONAD),
                                [node.target.id],
                                [plt.Var("e")],
                            ),
                        ),
                    ),
                    plt.Var(STATEMONAD),
                ),
            )
        raise NotImplementedError(
            "Compilation of for statements for anything but lists not implemented yet"
        )

    def visit_If(self, node: TypedIf) -> plt.AST:
        return plt.Lambda(
            [STATEMONAD],
            plt.Ite(
                plt.Apply(self.visit(node.test), plt.Var(STATEMONAD)),
                plt.Apply(self.visit_sequence(node.body), plt.Var(STATEMONAD)),
                plt.Apply(self.visit_sequence(node.orelse), plt.Var(STATEMONAD)),
            ),
        )

    def visit_Return(self, node: TypedReturn) -> plt.AST:
        raise NotImplementedError(
            "Compilation of return statements except for last statement in function is not supported."
        )

    def visit_Pass(self, node: TypedPass) -> plt.AST:
        return self.visit_sequence([])

    def visit_Subscript(self, node: TypedSubscript) -> plt.AST:
        assert isinstance(
            node.slice, Index
        ), "Only single index slices are currently supported"
        assert isinstance(
            node.value.typ, InstanceType
        ), "Can only access elements of instances, not classes"
        if isinstance(node.value.typ.typ, TupleType):
            assert isinstance(
                node.slice.value, Constant
            ), "Only constant index access for tuples is supported"
            assert isinstance(node.ctx, Load), "Tuples are read-only"
            return plt.Lambda(
                [STATEMONAD],
                plt.FunctionalTupleAccess(
                    plt.Apply(self.visit(node.value), plt.Var(STATEMONAD)),
                    node.slice.value.value,
                    len(node.value.typ.typs),
                ),
            )
        if isinstance(node.value.typ.typ, ListType):
            assert (
                node.slice.value.typ == IntegerInstanceType
            ), "Only single element list index access supported"
            return plt.Lambda(
                [STATEMONAD],
                plt.IndexAccessList(
                    plt.Apply(self.visit(node.value), plt.Var(STATEMONAD)),
                    plt.Apply(self.visit(node.slice.value), plt.Var(STATEMONAD)),
                ),
            )
        raise NotImplementedError(f"Could not implement subscript of {node}")

    def visit_Tuple(self, node: TypedTuple) -> plt.AST:
        return plt.Lambda(
            [STATEMONAD],
            plt.FunctionalTuple(
                *(plt.Apply(self.visit(e), plt.Var(STATEMONAD)) for e in node.elts)
            ),
        )

    def visit_ClassDef(self, node: ClassDef) -> plt.AST:
        # TODO add initializer to state monad
        return self.visit_sequence([])

    def visit_Attribute(self, node: TypedAttribute) -> plt.AST:
        if node.pos == -1:
            # access to constructor
            return plt.Lambda(
                [STATEMONAD],
                plt.Constructor(plt.Apply(self.visit(node.value), plt.Var(STATEMONAD))),
            )
        # access to normal fields
        return plt.Lambda(
            [STATEMONAD],
            transform_ext_params_map(node.typ)(
                plt.NthField(
                    plt.Apply(self.visit(node.value), plt.Var(STATEMONAD)),
                    plt.Integer(node.pos),
                ),
            ),
        )

    def visit_Assert(self, node: TypedAssert) -> plt.AST:
        return plt.Lambda(
            [STATEMONAD],
            plt.Ite(
                plt.Apply(self.visit(node.test), plt.Var(STATEMONAD)),
                plt.Var(STATEMONAD),
                plt.Apply(
                    plt.Error(),
                    plt.Trace(
                        plt.Apply(self.visit(node.msg), plt.Var(STATEMONAD)), plt.Unit()
                    )
                    if node.msg is not None
                    else plt.Unit(),
                ),
            ),
        )

    def generic_visit(self, node: AST) -> plt.AST:
        raise NotImplementedError(f"Can not compile {node}")


def compile(prog: AST):
    compiler_steps = [
        # Important to call this one first - it imports all further files
        RewriteImport,
        # The remaining order is almost arbitrary
        RewriteAugAssign,
        RewriteTupleAssign,
        RewriteIn,
        RewriteImportPlutusData,
        RewriteImportTyping,
        RewriteImportDataclasses,
        AggressiveTypeInferencer,
        UPLCCompiler,
    ]
    for s in compiler_steps:
        prog = s().visit(prog)
    return prog
