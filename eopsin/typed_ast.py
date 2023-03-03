import typing
from ast import *
from dataclasses import dataclass

from frozenlist import FrozenList

import pluthon as plt
import uplc.ast as uplc


def distinct(xs: list):
    """Returns true iff the list consists of distinct elements"""
    return len(xs) == len(set(xs))


def FrozenFrozenList(l: list):
    fl = FrozenList(l)
    fl.freeze()
    return fl


class Type:
    def constr_type(self) -> "InstanceType":
        """The type of the constructor for this class"""
        raise TypeInferenceError(
            f"Object of type {self.__class__} does not have a constructor"
        )

    def constr(self) -> plt.AST:
        """The constructor for this class"""
        raise NotImplementedError(f"Constructor of {self.__class__} not implemented")

    def attribute_type(self, attr) -> "Type":
        """The types of the named attributes of this class"""
        raise TypeInferenceError(
            f"Object of type {self.__class__} does not have attribute {attr}"
        )

    def attribute(self, attr) -> plt.AST:
        """The attributes of this class. Needs to be a lambda that expects as first argument the object itself"""
        raise NotImplementedError(f"Attribute {attr} not implemented for type {self}")

    def cmp(self, op: cmpop, o: "Type") -> plt.AST:
        """The implementation of comparing this type to type o via operator op. Returns a lambda that expects as first argument the object itself and as second the comparison."""
        raise NotImplementedError(
            f"Comparison {type(op).__name__} for {self.__class__.__name__} and {o.__class__.__name__} is not implemented. This is likely intended because it would always evaluate to False."
        )


@dataclass(frozen=True, unsafe_hash=True)
class Record:
    name: str
    constructor: int
    fields: typing.Union[typing.List[typing.Tuple[str, Type]], FrozenList]


@dataclass(frozen=True, unsafe_hash=True)
class ClassType(Type):
    def __ge__(self, other):
        raise NotImplementedError("Comparison between raw classtypes impossible")


@dataclass(frozen=True, unsafe_hash=True)
class AnyType(ClassType):
    """The top element in the partial order on types"""

    def __ge__(self, other):
        return True


@dataclass(frozen=True, unsafe_hash=True)
class AtomicType(ClassType):
    def __ge__(self, other):
        # Can only substitute for its own type (also subtypes)
        return isinstance(other, self.__class__)


class PolymorphicFunction:
    def type_from_args(self, args: typing.List[Type]) -> FunctionType:
        raise NotImplementedError()

    def impl_from_args(self, args: typing.List[Type]) -> plt.AST:
        raise NotImplementedError()


@dataclass(frozen=True, unsafe_hash=True)
class PolymorphicFunctionType(ClassType):
    """A special type of builtin that may act differently on different parameters"""

    polymorphic_function: PolymorphicFunction


@dataclass(frozen=True, unsafe_hash=True)
class InstanceType(Type):
    typ: ClassType

    def constr_type(self) -> FunctionType:
        raise TypeInferenceError(f"Can not construct an instance {self}")

    def constr(self) -> plt.AST:
        raise NotImplementedError(f"Can not construct an instance {self}")

    def attribute_type(self, attr) -> Type:
        return self.typ.attribute_type(attr)

    def attribute(self, attr) -> plt.AST:
        return self.typ.attribute(attr)

    def cmp(self, op: cmpop, o: "Type") -> plt.AST:
        """The implementation of comparing this type to type o via operator op. Returns a lambda that expects as first argument the object itself and as second the comparison."""
        if isinstance(o, InstanceType):
            return self.typ.cmp(op, o.typ)
        return super().cmp(op, o)

    def __ge__(self, other):
        return isinstance(other, InstanceType) and self.typ >= other.typ


@dataclass(frozen=True, unsafe_hash=True)
class PolymorphicFunctionInstanceType(InstanceType):
    typ: FunctionType
    polymorphic_function: PolymorphicFunction


@dataclass(frozen=True, unsafe_hash=True)
class RecordType(ClassType):
    record: Record

    def constr_type(self) -> InstanceType:
        return InstanceType(
            FunctionType([f[1] for f in self.record.fields], InstanceType(self))
        )

    def constr(self) -> plt.AST:
        # wrap all constructor values to PlutusData
        build_constr_params = plt.EmptyDataList()
        for n, t in reversed(self.record.fields):
            build_constr_params = plt.MkCons(
                transform_output_map(t)(plt.Var(n)), build_constr_params
            )
        # then build a constr type with this PlutusData
        return plt.Lambda(
            [n for n, _ in self.record.fields] + ["_"],
            plt.ConstrData(plt.Integer(self.record.constructor), build_constr_params),
        )

    def attribute_type(self, attr: str) -> Type:
        """The types of the named attributes of this class"""
        if attr == "CONSTR_ID":
            return IntegerInstanceType
        for n, t in self.record.fields:
            if n == attr:
                return t
        raise TypeInferenceError(
            f"Type {self.record.name} does not have attribute {attr}"
        )

    def attribute(self, attr: str) -> plt.AST:
        """The attributes of this class. Need to be a lambda that expects as first argument the object itself"""
        if attr == "CONSTR_ID":
            # access to constructor
            return plt.Lambda(
                ["self"],
                plt.Constructor(plt.Var("self")),
            )
        attr_typ = self.attribute_type(attr)
        pos = next(i for i, (n, _) in enumerate(self.record.fields) if n == attr)
        # access to normal fields
        return plt.Lambda(
            ["self"],
            transform_ext_params_map(attr_typ)(
                plt.NthField(
                    plt.Var("self"),
                    plt.Integer(pos),
                ),
            ),
        )

    def cmp(self, op: cmpop, o: "Type") -> plt.AST:
        """The implementation of comparing this type to type o via operator op. Returns a lambda that expects as first argument the object itself and as second the comparison."""
        # this will reject comparisons that will always be false - most likely due to faults during programming
        if (isinstance(o, RecordType) and o.record == self.record) or (
            isinstance(o, UnionType) and self in o.typs
        ):
            if isinstance(op, Eq):
                return plt.BuiltIn(uplc.BuiltInFun.EqualsData)
            if isinstance(op, NotEq):
                return plt.Lambda(
                    ["x", "y"],
                    plt.Not(
                        plt.Apply(
                            plt.BuiltIn(uplc.BuiltInFun.EqualsData),
                            plt.Var("x"),
                            plt.Var("y"),
                        )
                    ),
                )
        if (
            isinstance(o, ListType)
            and isinstance(o.typ, InstanceType)
            and o.typ.typ >= self
        ):
            if isinstance(op, In):
                return plt.Lambda(
                    ["x", "y"],
                    plt.EqualsData(
                        plt.Var("x"),
                        plt.FindList(
                            plt.Var("y"),
                            plt.Apply(
                                plt.BuiltIn(uplc.BuiltInFun.EqualsData), plt.Var("x")
                            ),
                            # this simply ensures the default is always unequal to the searched value
                            plt.ConstrData(
                                plt.AddInteger(
                                    plt.Constructor(plt.Var("x")), plt.Integer(1)
                                ),
                                plt.MkNilData(plt.Unit()),
                            ),
                        ),
                    ),
                )
        return super().cmp(op, o)

    def __ge__(self, other):
        # Can only substitute for its own type, records need to be equal
        # if someone wants to be funny, they can implement <= to be true if all fields match up to some point
        return isinstance(other, self.__class__) and other.record == self.record


@dataclass(frozen=True, unsafe_hash=True)
class UnionType(ClassType):
    typs: typing.List[RecordType]

    def attribute_type(self, attr) -> "Type":
        if attr == "CONSTR_ID":
            return IntegerInstanceType
        # iterate through all names/types of the unioned records by position
        for attr_names, attr_types in map(
            lambda x: zip(*x), zip(*(t.record.fields for t in self.typs))
        ):
            # need to have a common field with the same name, in the same position!
            if any(attr_name != attr for attr_name in attr_names):
                continue
            for at in attr_types:
                # return the maximum element if there is one
                if all(at >= at2 for at2 in attr_types):
                    return at
            # return the union type of all possible instantiations if all possible values are record types
            if all(
                isinstance(at, InstanceType) and isinstance(at.typ, RecordType)
                for at in attr_types
            ) and distinct([at.typ.record.constructor for at in attr_types]):
                return InstanceType(
                    UnionType(FrozenFrozenList([at.typ for at in attr_types]))
                )
            # return Anytype
            return InstanceType(AnyType())
        raise TypeInferenceError(
            f"Can not access attribute {attr} of Union type. Cast to desired type with an 'if isinstance(_, _):' branch."
        )

    def attribute(self, attr: str) -> plt.AST:
        if attr == "CONSTR_ID":
            # access to constructor
            return plt.Lambda(
                ["self"],
                plt.Constructor(plt.Var("self")),
            )
        # iterate through all names/types of the unioned records by position
        attr_typ = self.attribute_type(attr)
        pos = next(
            i
            for i, (ns, _) in enumerate(
                map(lambda x: zip(*x), zip(*(t.record.fields for t in self.typs)))
            )
            if all(n == attr for n in ns)
        )
        # access to normal fields
        return plt.Lambda(
            ["self"],
            transform_ext_params_map(attr_typ)(
                plt.NthField(
                    plt.Var("self"),
                    plt.Integer(pos),
                ),
            ),
        )

    def __ge__(self, other):
        if isinstance(other, UnionType):
            return all(any(t >= ot for ot in other.typs) for t in self.typs)
        return any(t >= other for t in self.typs)

    def cmp(self, op: cmpop, o: "Type") -> plt.AST:
        """The implementation of comparing this type to type o via operator op. Returns a lambda that expects as first argument the object itself and as second the comparison."""
        # this will reject comparisons that will always be false - most likely due to faults during programming
        # note we require that there is an overlapt between the possible types for unions
        if (isinstance(o, RecordType) and o in self.typs) or (
            isinstance(o, UnionType) and set(self.typs).intersection(o.typs)
        ):
            if isinstance(op, Eq):
                return plt.BuiltIn(uplc.BuiltInFun.EqualsData)
            if isinstance(op, NotEq):
                return plt.Lambda(
                    ["x", "y"],
                    plt.Not(
                        plt.Apply(
                            plt.BuiltIn(uplc.BuiltInFun.EqualsData),
                            plt.Var("x"),
                            plt.Var("y"),
                        )
                    ),
                )
        raise NotImplementedError(
            f"Can not compare {o} and {self} with operation {op.__class__}. Note that comparisons that always return false are also rejected."
        )


@dataclass(frozen=True, unsafe_hash=True)
class TupleType(ClassType):
    typs: typing.List[Type]

    def __ge__(self, other):
        return isinstance(other, TupleType) and all(
            t >= ot for t, ot in zip(self.typs, other.typs)
        )


@dataclass(frozen=True, unsafe_hash=True)
class ListType(ClassType):
    typ: Type

    def __ge__(self, other):
        return isinstance(other, ListType) and self.typ >= other.typ


@dataclass(frozen=True, unsafe_hash=True)
class DictType(ClassType):
    key_typ: Type
    value_typ: Type

    def attribute_type(self, attr) -> "Type":
        if attr == "get":
            return InstanceType(
                FunctionType([self.key_typ, self.value_typ], self.value_typ)
            )
        if attr == "keys":
            return InstanceType(FunctionType([], InstanceType(ListType(self.key_typ))))
        if attr == "values":
            return InstanceType(
                FunctionType([], InstanceType(ListType(self.value_typ)))
            )
        raise TypeInferenceError(
            f"Type of attribute '{attr}' is unknown for type Dict."
        )

    def attribute(self, attr) -> plt.AST:
        if attr == "get":
            return plt.Lambda(
                ["self", "key", "default", "_"],
                transform_ext_params_map(self.value_typ)(
                    plt.SndPair(
                        plt.FindList(
                            plt.Var("self"),
                            plt.Lambda(
                                ["x"],
                                plt.EqualsData(
                                    transform_output_map(self.key_typ)(plt.Var("key")),
                                    plt.FstPair(plt.Var("x")),
                                ),
                            ),
                            # this is a bit ugly... we wrap - only to later unwrap again
                            plt.MkPairData(
                                transform_output_map(self.key_typ)(plt.Var("key")),
                                transform_output_map(self.value_typ)(
                                    plt.Var("default")
                                ),
                            ),
                        ),
                    ),
                ),
            )
        if attr == "keys":
            return plt.Lambda(
                ["self", "_"],
                plt.MapList(
                    plt.Var("self"),
                    plt.Lambda(
                        ["x"],
                        transform_ext_params_map(self.key_typ)(
                            plt.FstPair(plt.Var("x"))
                        ),
                    ),
                    empty_list(self.key_typ),
                ),
            )
        if attr == "values":
            return plt.Lambda(
                ["self", "_"],
                plt.MapList(
                    plt.Var("self"),
                    plt.Lambda(
                        ["x"],
                        transform_ext_params_map(self.value_typ)(
                            plt.SndPair(plt.Var("x"))
                        ),
                    ),
                    empty_list(self.value_typ),
                ),
            )
        raise NotImplementedError(f"Attribute '{attr}' of Dict is unknown.")

    def __ge__(self, other):
        return (
            isinstance(other, DictType)
            and self.key_typ >= other.key_typ
            and self.value_typ >= other.value_typ
        )


@dataclass(frozen=True, unsafe_hash=True)
class FunctionType(ClassType):
    argtyps: typing.List[Type]
    rettyp: Type

    def __ge__(self, other):
        return (
            isinstance(other, FunctionType)
            and all(a >= oa for a, oa in zip(self.argtyps, other.argtyps))
            and other.rettyp >= self.rettyp
        )


class IntegerConstructor(PolymorphicFunction):
    def type_from_args(self, args: typing.List[Type]) -> FunctionType:
        if len(args) == 1 and args[0] in (StringInstanceType, BoolInstanceType):
            return FunctionType([args[0]], IntegerInstanceType)
        return super().type_from_args(args)

    def impl_from_args(self, args: typing.List[Type]) -> plt.AST:
        if len(args) == 1:
            if args[0] == BoolInstanceType:
                return plt.Lambda(
                    ["x", "_"],
                    plt.IfThenElse(plt.Var("x"), plt.Integer(1), plt.Integer(0)),
                )
            if args[0] == StringInstanceType:
                return plt.Lambda(
                    ["x", "_"],
                    plt.Let(
                        [
                            ("e", plt.EncodeUtf8(plt.Var("x"))),
                            (
                                "first_int",
                                plt.IndexByteString(plt.Var("e"), plt.Integer(0)),
                            ),
                            ("len", plt.LengthOfByteString(plt.Var("e"))),
                            (
                                "fold_start",
                                plt.Lambda(
                                    ["start"],
                                    plt.FoldList(
                                        plt.Range(plt.Var("len"), plt.Var("start")),
                                        plt.Lambda(
                                            ["s", "i"],
                                            plt.Let(
                                                [
                                                    (
                                                        "b",
                                                        plt.IndexByteString(
                                                            plt.Var("e"), plt.Var("i")
                                                        ),
                                                    )
                                                ],
                                                plt.Ite(
                                                    plt.EqualsInteger(
                                                        plt.Var("b"),
                                                        plt.Integer(ord("_")),
                                                    ),
                                                    plt.Var("s"),
                                                    plt.Ite(
                                                        plt.Or(
                                                            plt.LessThanInteger(
                                                                plt.Var("b"),
                                                                plt.Integer(ord("0")),
                                                            ),
                                                            plt.LessThanInteger(
                                                                plt.Integer(ord("9")),
                                                                plt.Var("b"),
                                                            ),
                                                        ),
                                                        plt.TraceError(
                                                            "ValueError: invalid literal for int() with base 10"
                                                        ),
                                                        plt.AddInteger(
                                                            plt.SubtractInteger(
                                                                plt.Var("b"),
                                                                plt.Integer(ord("0")),
                                                            ),
                                                            plt.MultiplyInteger(
                                                                plt.Var("s"),
                                                                plt.Integer(10),
                                                            ),
                                                        ),
                                                    ),
                                                ),
                                            ),
                                        ),
                                        plt.Integer(0),
                                    ),
                                ),
                            ),
                        ],
                        plt.Ite(
                            plt.Or(
                                plt.EqualsInteger(plt.Var("len"), plt.Integer(0)),
                                plt.EqualsInteger(
                                    plt.Var("first_int"),
                                    plt.Integer(ord("_")),
                                ),
                            ),
                            plt.TraceError(
                                "ValueError: invalid literal for int() with base 10"
                            ),
                            plt.Ite(
                                plt.EqualsInteger(
                                    plt.Var("first_int"),
                                    plt.Integer(ord("-")),
                                ),
                                plt.Negate(
                                    plt.Apply(plt.Var("fold_start"), plt.Integer(1)),
                                ),
                                plt.Apply(plt.Var("fold_start"), plt.Integer(0)),
                            ),
                        ),
                    ),
                )
        return super().type_from_args(args)


@dataclass(frozen=True, unsafe_hash=True)
class IntegerType(AtomicType):
    def constr_type(self) -> InstanceType:
        return InstanceType(FunctionType([StringInstanceType], InstanceType(self)))

    def constr(self) -> plt.AST:
        return plt.Lambda(
            ["x", "_"],
            plt.Let(
                [
                    ("e", plt.EncodeUtf8(plt.Var("x"))),
                    ("first_int", plt.IndexByteString(plt.Var("e"), plt.Integer(0))),
                    ("len", plt.LengthOfByteString(plt.Var("e"))),
                    (
                        "fold_start",
                        plt.Lambda(
                            ["start"],
                            plt.FoldList(
                                plt.Range(plt.Var("len"), plt.Var("start")),
                                plt.Lambda(
                                    ["s", "i"],
                                    plt.Let(
                                        [
                                            (
                                                "b",
                                                plt.IndexByteString(
                                                    plt.Var("e"), plt.Var("i")
                                                ),
                                            )
                                        ],
                                        plt.Ite(
                                            plt.EqualsInteger(
                                                plt.Var("b"), plt.Integer(ord("_"))
                                            ),
                                            plt.Var("s"),
                                            plt.Ite(
                                                plt.Or(
                                                    plt.LessThanInteger(
                                                        plt.Var("b"),
                                                        plt.Integer(ord("0")),
                                                    ),
                                                    plt.LessThanInteger(
                                                        plt.Integer(ord("9")),
                                                        plt.Var("b"),
                                                    ),
                                                ),
                                                plt.TraceError(
                                                    "ValueError: invalid literal for int() with base 10"
                                                ),
                                                plt.AddInteger(
                                                    plt.SubtractInteger(
                                                        plt.Var("b"),
                                                        plt.Integer(ord("0")),
                                                    ),
                                                    plt.MultiplyInteger(
                                                        plt.Var("s"), plt.Integer(10)
                                                    ),
                                                ),
                                            ),
                                        ),
                                    ),
                                ),
                                plt.Integer(0),
                            ),
                        ),
                    ),
                ],
                plt.Ite(
                    plt.Or(
                        plt.EqualsInteger(plt.Var("len"), plt.Integer(0)),
                        plt.EqualsInteger(
                            plt.Var("first_int"),
                            plt.Integer(ord("_")),
                        ),
                    ),
                    plt.TraceError(
                        "ValueError: invalid literal for int() with base 10"
                    ),
                    plt.Ite(
                        plt.EqualsInteger(
                            plt.Var("first_int"),
                            plt.Integer(ord("-")),
                        ),
                        plt.Negate(
                            plt.Apply(plt.Var("fold_start"), plt.Integer(1)),
                        ),
                        plt.Apply(plt.Var("fold_start"), plt.Integer(0)),
                    ),
                ),
            ),
        )

    def cmp(self, op: cmpop, o: "Type") -> plt.AST:
        """The implementation of comparing this type to type o via operator op. Returns a lambda that expects as first argument the object itself and as second the comparison."""
        if isinstance(o, BoolType):
            if isinstance(op, Eq):
                # 1 == True
                # 0 == False
                # all other comparisons are False
                return plt.Lambda(
                    ["x", "y"],
                    plt.Ite(
                        plt.Var("y"),
                        plt.EqualsInteger(plt.Var("x"), plt.Integer(1)),
                        plt.EqualsInteger(plt.Var("x"), plt.Integer(0)),
                    ),
                )
        if isinstance(o, IntegerType):
            if isinstance(op, Eq):
                return plt.BuiltIn(uplc.BuiltInFun.EqualsInteger)
            if isinstance(op, NotEq):
                return plt.Lambda(
                    ["x", "y"],
                    plt.Not(
                        plt.Apply(
                            plt.BuiltIn(uplc.BuiltInFun.EqualsInteger),
                            plt.Var("y"),
                            plt.Var("x"),
                        )
                    ),
                )
            if isinstance(op, LtE):
                return plt.BuiltIn(uplc.BuiltInFun.LessThanEqualsInteger)
            if isinstance(op, Lt):
                return plt.BuiltIn(uplc.BuiltInFun.LessThanInteger)
            if isinstance(op, Gt):
                return plt.Lambda(
                    ["x", "y"],
                    plt.Apply(
                        plt.BuiltIn(uplc.BuiltInFun.LessThanInteger),
                        plt.Var("y"),
                        plt.Var("x"),
                    ),
                )
            if isinstance(op, GtE):
                return plt.Lambda(
                    ["x", "y"],
                    plt.Apply(
                        plt.BuiltIn(uplc.BuiltInFun.LessThanEqualsInteger),
                        plt.Var("y"),
                        plt.Var("x"),
                    ),
                )
        if (
            isinstance(o, ListType)
            and isinstance(o.typ, InstanceType)
            and isinstance(o.typ.typ, IntegerType)
        ):
            if isinstance(op, In):
                return plt.Lambda(
                    ["x", "y"],
                    plt.EqualsInteger(
                        plt.Var("x"),
                        plt.FindList(
                            plt.Var("y"),
                            plt.Apply(
                                plt.BuiltIn(uplc.BuiltInFun.EqualsInteger), plt.Var("x")
                            ),
                            # this simply ensures the default is always unequal to the searched value
                            plt.AddInteger(plt.Var("x"), plt.Integer(1)),
                        ),
                    ),
                )
        return super().cmp(op, o)


@dataclass(frozen=True, unsafe_hash=True)
class StringType(AtomicType):
    def constr_type(self) -> InstanceType:
        return InstanceType(FunctionType([IntegerInstanceType], InstanceType(self)))

    def constr(self) -> plt.AST:
        # constructs a string representation of an integer
        return plt.Lambda(
            ["x", "_"],
            plt.DecodeUtf8(
                plt.Let(
                    [
                        (
                            "strlist",
                            plt.RecFun(
                                plt.Lambda(
                                    ["f", "i"],
                                    plt.Ite(
                                        plt.LessThanEqualsInteger(
                                            plt.Var("i"), plt.Integer(0)
                                        ),
                                        plt.EmptyIntegerList(),
                                        plt.MkCons(
                                            plt.AddInteger(
                                                plt.ModInteger(
                                                    plt.Var("i"), plt.Integer(10)
                                                ),
                                                plt.Integer(ord("0")),
                                            ),
                                            plt.Apply(
                                                plt.Var("f"),
                                                plt.Var("f"),
                                                plt.DivideInteger(
                                                    plt.Var("i"), plt.Integer(10)
                                                ),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                        (
                            "mkstr",
                            plt.Lambda(
                                ["i"],
                                plt.FoldList(
                                    plt.Apply(plt.Var("strlist"), plt.Var("i")),
                                    plt.Lambda(
                                        ["b", "i"],
                                        plt.ConsByteString(plt.Var("i"), plt.Var("b")),
                                    ),
                                    plt.ByteString(b""),
                                ),
                            ),
                        ),
                    ],
                    plt.Ite(
                        plt.EqualsInteger(plt.Var("x"), plt.Integer(0)),
                        plt.ByteString(b"0"),
                        plt.Ite(
                            plt.LessThanInteger(plt.Var("x"), plt.Integer(0)),
                            plt.ConsByteString(
                                plt.Integer(ord("-")),
                                plt.Apply(plt.Var("mkstr"), plt.Negate(plt.Var("x"))),
                            ),
                            plt.Apply(plt.Var("mkstr"), plt.Var("x")),
                        ),
                    ),
                )
            ),
        )

    def attribute_type(self, attr) -> Type:
        if attr == "encode":
            return InstanceType(FunctionType([], ByteStringInstanceType))
        return super().attribute_type(attr)

    def attribute(self, attr) -> plt.AST:
        if attr == "encode":
            # No codec -> only the default (utf8) is allowed
            return plt.Lambda(["x", "_"], plt.EncodeUtf8(plt.Var("x")))
        return super().attribute(attr)

    def cmp(self, op: cmpop, o: "Type") -> plt.AST:
        if isinstance(o, StringType):
            if isinstance(op, Eq):
                return plt.BuiltIn(uplc.BuiltInFun.EqualsString)
        return super().cmp(op, o)


@dataclass(frozen=True, unsafe_hash=True)
class ByteStringType(AtomicType):
    def constr_type(self) -> InstanceType:
        return InstanceType(
            FunctionType(
                [InstanceType(ListType(IntegerInstanceType))], InstanceType(self)
            )
        )

    def constr(self) -> plt.AST:
        return plt.Lambda(
            ["xs", "_"],
            plt.RFoldList(
                plt.Var("xs"),
                plt.Lambda(["a", "x"], plt.ConsByteString(plt.Var("x"), plt.Var("a"))),
                plt.ByteString(b""),
            ),
        )

    def attribute_type(self, attr) -> Type:
        if attr == "decode":
            return InstanceType(FunctionType([], StringInstanceType))
        return super().attribute_type(attr)

    def attribute(self, attr) -> plt.AST:
        if attr == "decode":
            # No codec -> only the default (utf8) is allowed
            return plt.Lambda(["x", "_"], plt.DecodeUtf8(plt.Var("x")))
        return super().attribute(attr)

    def cmp(self, op: cmpop, o: "Type") -> plt.AST:
        if isinstance(o, ByteStringType):
            if isinstance(op, Eq):
                return plt.BuiltIn(uplc.BuiltInFun.EqualsByteString)
            if isinstance(op, NotEq):
                return plt.Lambda(
                    ["x", "y"],
                    plt.Not(
                        plt.Apply(
                            plt.BuiltIn(uplc.BuiltInFun.EqualsByteString),
                            plt.Var("y"),
                            plt.Var("x"),
                        )
                    ),
                )
            if isinstance(op, Lt):
                return plt.BuiltIn(uplc.BuiltInFun.LessThanByteString)
            if isinstance(op, LtE):
                return plt.BuiltIn(uplc.BuiltInFun.LessThanEqualsByteString)
            if isinstance(op, Gt):
                return plt.Lambda(
                    ["x", "y"],
                    plt.Apply(
                        plt.BuiltIn(uplc.BuiltInFun.LessThanByteString),
                        plt.Var("y"),
                        plt.Var("x"),
                    ),
                )
            if isinstance(op, GtE):
                return plt.Lambda(
                    ["x", "y"],
                    plt.Apply(
                        plt.BuiltIn(uplc.BuiltInFun.LessThanEqualsByteString),
                        plt.Var("y"),
                        plt.Var("x"),
                    ),
                )
        if (
            isinstance(o, ListType)
            and isinstance(o.typ, InstanceType)
            and isinstance(o.typ.typ, ByteStringType)
        ):
            if isinstance(op, In):
                return plt.Lambda(
                    ["x", "y"],
                    plt.EqualsByteString(
                        plt.Var("x"),
                        plt.FindList(
                            plt.Var("y"),
                            plt.Apply(
                                plt.BuiltIn(uplc.BuiltInFun.EqualsByteString),
                                plt.Var("x"),
                            ),
                            # this simply ensures the default is always unequal to the searched value
                            plt.ConsByteString(plt.Integer(0), plt.Var("x")),
                        ),
                    ),
                )
        return super().cmp(op, o)


@dataclass(frozen=True, unsafe_hash=True)
class BoolType(AtomicType):
    def cmp(self, op: cmpop, o: "Type") -> plt.AST:
        if isinstance(o, IntegerType):
            if isinstance(op, Eq):
                # 1 == True
                # 0 == False
                # all other comparisons are False
                return plt.Lambda(
                    ["y", "x"],
                    plt.Ite(
                        plt.Var("y"),
                        plt.EqualsInteger(plt.Var("x"), plt.Integer(1)),
                        plt.EqualsInteger(plt.Var("x"), plt.Integer(0)),
                    ),
                )
        if isinstance(o, BoolType):
            if isinstance(op, Eq):
                return plt.Lambda(["x", "y"], plt.Iff(plt.Var("x"), plt.Var("y")))
        return super().cmp(op, o)


@dataclass(frozen=True, unsafe_hash=True)
class UnitType(AtomicType):
    def cmp(self, op: cmpop, o: "Type") -> plt.AST:
        if isinstance(o, UnitType):
            if isinstance(op, Eq):
                return plt.Lambda(["x", "y"], plt.Bool(True))
            if isinstance(op, NotEq):
                return plt.Lambda(["x", "y"], plt.Bool(False))
        return super().cmp(op, o)


IntegerInstanceType = InstanceType(IntegerType())
StringInstanceType = InstanceType(StringType())
ByteStringInstanceType = InstanceType(ByteStringType())
BoolInstanceType = InstanceType(BoolType())
UnitInstanceType = InstanceType(UnitType())

ATOMIC_TYPES = {
    int.__name__: IntegerType(),
    str.__name__: StringType(),
    bytes.__name__: ByteStringType(),
    "Unit": UnitType(),
    bool.__name__: BoolType(),
}


NoneInstanceType = UnitInstanceType


class InaccessibleType(ClassType):
    """A type that blocks overwriting of a function"""

    pass


class TypedAST(AST):
    typ: Type


class typedexpr(TypedAST, expr):
    pass


class typedstmt(TypedAST, stmt):
    # Statements always have type None
    typ = NoneInstanceType


class typedarg(TypedAST, arg):
    pass


class typedarguments(TypedAST, arguments):
    args: typing.List[typedarg]
    vararg: typing.Union[typedarg, None]
    kwonlyargs: typing.List[typedarg]
    kw_defaults: typing.List[typing.Union[typedexpr, None]]
    kwarg: typing.Union[typedarg, None]
    defaults: typing.List[typedexpr]


class TypedModule(typedstmt, Module):
    body: typing.List[typedstmt]


class TypedFunctionDef(typedstmt, FunctionDef):
    body: typing.List[typedstmt]
    args: arguments


class TypedIf(typedstmt, If):
    test: typedexpr
    body: typing.List[typedstmt]
    orelse: typing.List[typedstmt]


class TypedReturn(typedstmt, Return):
    value: typedexpr


class TypedExpression(typedexpr, Expression):
    body: typedexpr


class TypedCall(typedexpr, Call):
    func: typedexpr
    args: typing.List[typedexpr]


class TypedExpr(typedstmt, Expr):
    value: typedexpr


class TypedAssign(typedstmt, Assign):
    targets: typing.List[typedexpr]
    value: typedexpr


class TypedClassDef(typedstmt, ClassDef):
    class_typ: Type


class TypedAnnAssign(typedstmt, AnnAssign):
    target: typedexpr
    annotation: Type
    value: typedexpr


class TypedWhile(typedstmt, While):
    test: typedexpr
    body: typing.List[typedstmt]
    orelse: typing.List[typedstmt]


class TypedFor(typedstmt, For):
    target: typedexpr
    iter: typedexpr
    body: typing.List[typedstmt]
    orelse: typing.List[typedstmt]


class TypedPass(typedstmt, Pass):
    pass


class TypedName(typedexpr, Name):
    pass


class TypedConstant(TypedAST, Constant):
    pass


class TypedTuple(typedexpr, Tuple):
    pass


class TypedList(typedexpr, List):
    pass


class typedcomprehension(typedexpr, comprehension):
    target: typedexpr
    iter: typedexpr
    ifs: typing.List[typedexpr]


class TypedListComp(typedexpr, ListComp):
    generators: typing.List[typedcomprehension]
    elt: typedexpr


class TypedDict(typedexpr, Dict):
    pass


class TypedIfExp(typedstmt, IfExp):
    test: typedexpr
    body: typedexpr
    orelse: typedexpr


class TypedCompare(typedexpr, Compare):
    left: typedexpr
    ops: typing.List[cmpop]
    comparators: typing.List[typedexpr]


class TypedBinOp(typedexpr, BinOp):
    left: typedexpr
    right: typedexpr


class TypedBoolOp(typedexpr, BoolOp):
    values: typing.List[typedexpr]


class TypedUnaryOp(typedexpr, UnaryOp):
    operand: typedexpr


class TypedSubscript(typedexpr, Subscript):
    value: typedexpr


class TypedAttribute(typedexpr, Attribute):
    value: typedexpr
    pos: int


class TypedAssert(typedstmt, Assert):
    test: typedexpr
    msg: typedexpr


class RawPlutoExpr(typedexpr):
    typ: Type
    expr: plt.AST


class TypeInferenceError(AssertionError):
    pass


EmptyListMap = {
    IntegerInstanceType: plt.EmptyIntegerList(),
    ByteStringInstanceType: plt.EmptyByteStringList(),
    StringInstanceType: plt.EmptyTextList(),
    UnitInstanceType: plt.EmptyUnitList(),
    BoolInstanceType: plt.EmptyBoolList(),
}


def empty_list(p: Type):
    if p in EmptyListMap:
        return EmptyListMap[p]
    assert isinstance(p, InstanceType), "Can only create lists of instances"
    if isinstance(p.typ, ListType):
        el = empty_list(p.typ.typ)
        return plt.EmptyListList(uplc.BuiltinList([], el.sample_value))
    if isinstance(p.typ, DictType):
        plt.EmptyDataPairList()
    if isinstance(p.typ, RecordType):
        return plt.EmptyDataList()
    raise NotImplementedError(f"Empty lists of type {p} can't be constructed yet")


TransformExtParamsMap = {
    IntegerInstanceType: lambda x: plt.UnIData(x),
    ByteStringInstanceType: lambda x: plt.UnBData(x),
    StringInstanceType: lambda x: plt.DecodeUtf8(plt.UnBData(x)),
    UnitInstanceType: lambda x: plt.Apply(plt.Lambda(["_"], plt.Unit())),
    BoolInstanceType: lambda x: plt.NotEqualsInteger(plt.UnIData(x), plt.Integer(0)),
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
            empty_list(p.typ.typ),
        )
    if isinstance(p.typ, DictType):
        # there doesn't appear to be a constructor function to make Pair a b for any types
        # so pairs will always contain Data
        return lambda x: plt.UnMapData(x)
    return lambda x: x


TransformOutputMap = {
    StringInstanceType: lambda x: plt.BData(plt.EncodeUtf8(x)),
    IntegerInstanceType: lambda x: plt.IData(x),
    ByteStringInstanceType: lambda x: plt.BData(x),
    UnitInstanceType: lambda x: plt.Apply(plt.Lambda(["_"], plt.Unit()), x),
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
                x,
                plt.Lambda(["x"], transform_output_map(list_int_typ)(plt.Var("x"))),
            ),
        )
    if isinstance(p.typ, DictType):
        # there doesn't appear to be a constructor function to make Pair a b for any types
        # so pairs will always contain Data
        return lambda x: plt.MapData(x)
    return lambda x: x


class TypedNodeTransformer(NodeTransformer):
    def visit(self, node):
        """Visit a node."""
        node_class_name = node.__class__.__name__
        if node_class_name.startswith("Typed"):
            node_class_name = node_class_name[len("Typed") :]
        method = "visit_" + node_class_name
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)


class TypedNodeVisitor(NodeVisitor):
    def visit(self, node):
        """Visit a node."""
        node_class_name = node.__class__.__name__
        if node_class_name.startswith("Typed"):
            node_class_name = node_class_name[len("Typed") :]
        method = "visit_" + node_class_name
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)
