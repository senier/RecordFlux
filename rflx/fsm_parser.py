from typing import Any, List

from pyparsing import (
    Forward,
    Keyword,
    Literal,
    StringEnd,
    Suppress,
    Token,
    delimitedList,
    infixNotation,
    oneOf,
    opAssoc,
)

from rflx.expression import (
    FALSE,
    TRUE,
    Add,
    And,
    Div,
    Equal,
    Expr,
    Greater,
    Length,
    Less,
    Mul,
    NotEqual,
    Or,
    Sub,
    Variable,
)
from rflx.fsm_expression import (
    Binding,
    Comprehension,
    Contains,
    Field,
    ForAll,
    ForSome,
    FunctionCall,
    Head,
    MessageAggregate,
    NotContains,
    Present,
    Valid,
)
from rflx.parser import Parser
from rflx.statement import Assignment


class InternalError(Exception):
    pass


class FSMParser:
    @classmethod
    def __parse_quantifier(cls, tokens: List[Expr]) -> Expr:
        if not isinstance(tokens[1], Variable):
            raise TypeError("quantifier not of type Variable")
        if tokens[0] == "all":
            return ForAll(tokens[1], tokens[2], tokens[3])
        return ForSome(tokens[1], tokens[2], tokens[3])

    @classmethod
    def __parse_comprehension(cls, tokens: List[Expr]) -> Expr:
        if not isinstance(tokens[0], Variable):
            raise TypeError("quantifier not of type Variable")
        return Comprehension(tokens[0], tokens[1], tokens[2], tokens[3])

    @classmethod
    def __parse_function_call(cls, tokens: List[Expr]) -> Expr:
        if not isinstance(tokens[0], Variable):
            raise TypeError("target not of type Variable")
        return FunctionCall(tokens[0], tokens[1:])

    @classmethod
    def __identifier(cls) -> Token:
        identifier = Parser.qualified_identifier()
        identifier.setParseAction(lambda t: Variable(".".join(t)))
        return identifier

    @classmethod
    def __parse_op_comp(cls, tokens: List[Expr]) -> Expr:
        if tokens[1] == "<":
            return Less(tokens[0], tokens[2])
        if tokens[1] == ">":
            return Greater(tokens[0], tokens[2])
        if tokens[1] == "=":
            return Equal(tokens[0], tokens[2])
        if tokens[1] == "/=":
            return NotEqual(tokens[0], tokens[2])
        raise InternalError(f"Unsupported comparison operator {tokens[1]}")

    @classmethod
    def __parse_op_set(cls, tokens: List[Expr]) -> Expr:
        if tokens[1] == "not in":
            return NotContains(tokens[0], tokens[2])
        if tokens[1] == "in":
            return Contains(tokens[0], tokens[2])
        raise InternalError(f"Unsupported set operator {tokens[1]}")

    @classmethod
    def __parse_op_add_sub(cls, tokens: List[Expr]) -> Expr:
        result = tokens[0]
        for op, right in zip(tokens[1::2], tokens[2::2]):
            if op == "+":
                result = Add(result, right)
            elif op == "-":
                result = Sub(result, right)
            else:
                raise InternalError(f"Unsupported add/sub operator {op}")
        return result

    @classmethod
    def __parse_op_mul_div(cls, tokens: List[Expr]) -> Expr:
        result = tokens[0]
        for op, right in zip(tokens[1::2], tokens[2::2]):
            if op == "*":
                result = Mul(result, right)
            elif op == "/":
                result = Div(result, right)
            else:
                raise InternalError(f"Unsupported mul/div operator {op}")
        return result

    @classmethod
    def __parse_suffix(cls, data: List[Any]) -> Expr:
        result = data[0][0]
        for suffix in data[0][1:]:
            if suffix[0] == "Head":
                result = Head(result)
            if suffix[0] == "Valid":
                result = Valid(result)
            if suffix[0] == "Present":
                result = Present(result)
            if suffix[0] == "Length":
                result = Length(result)
            if suffix[0] == "Field":
                result = Field(result, suffix[1])
            if suffix[0] == "Binding":
                result = Binding(result, suffix[1])
            if suffix[0] == "Aggregate":
                result = MessageAggregate(result, suffix[1])

        return result

    @classmethod
    def expression(cls) -> Token:  # pylint: disable=too-many-locals

        boolean_literal = Parser.boolean_literal()
        boolean_literal.setParseAction(lambda t: TRUE if t[0] == "True" else FALSE)

        expression = Forward()

        parameters = delimitedList(expression, delim=",")

        lpar, rpar = map(Suppress, "()")
        function_call = cls.__identifier() + lpar + parameters + rpar
        function_call.setParseAction(cls.__parse_function_call)

        quantifier = (
            Keyword("for").suppress()
            - oneOf(["all", "some"])
            + cls.__identifier()
            - Keyword("in").suppress()
            + expression
            - Keyword("=>").suppress()
            + expression
        )
        quantifier.setParseAction(cls.__parse_quantifier)

        comprehension = (
            Literal("[").suppress()
            - Keyword("for").suppress()
            + cls.__identifier()
            - Keyword("in").suppress()
            + expression
            - Keyword("=>").suppress()
            + expression
            - Keyword("when").suppress()
            + expression
            - Literal("]").suppress()
        )
        comprehension.setParseAction(cls.__parse_comprehension)

        components = delimitedList(
            Parser.identifier() + Keyword("=>").suppress() + expression, delim=","
        )
        components.setParseAction(lambda t: dict(zip(t[0::2], t[1::2])))

        terms = delimitedList(Parser.identifier() + Keyword("=").suppress() + expression, delim=",")
        terms.setParseAction(lambda t: dict(zip(t[0::2], t[1::2])))

        atom = (
            Parser.numeric_literal()
            | boolean_literal
            | quantifier
            | comprehension
            | function_call
            | cls.__identifier()
        )

        attribute_designator = (
            Keyword("Valid") | Keyword("Present") | Keyword("Length") | Keyword("Head")
        )

        attribute = Literal("'").suppress() - attribute_designator
        attribute.setParseAction(lambda t: (t[0], None))

        field = Literal(".").suppress() - Parser.identifier()
        field.setParseAction(lambda t: ("Field", t[0]))

        binding = Keyword("where").suppress() + terms
        binding.setParseAction(lambda t: ("Binding", t[0]))

        aggregate = Literal("'").suppress() + lpar + components + rpar
        aggregate.setParseAction(lambda t: ("Aggregate", t[0]))

        suffix = binding ^ attribute ^ field ^ aggregate

        op_comp = Keyword("<") | Keyword(">") | Keyword("=") | Keyword("/=")

        op_add_sub = Keyword("+") | Keyword("-")

        op_mul_div = Keyword("*") | Keyword("/")

        op_set = (Keyword("not") + Keyword("in")).setParseAction(lambda t: ["not in"]) | Keyword(
            "in"
        )

        expression <<= infixNotation(
            atom,
            [
                (suffix, 1, opAssoc.LEFT, cls.__parse_suffix),
                (op_set, 2, opAssoc.LEFT, lambda t: cls.__parse_op_set(t[0])),
                (op_mul_div, 2, opAssoc.LEFT, lambda t: cls.__parse_op_mul_div(t[0])),
                (op_add_sub, 2, opAssoc.LEFT, lambda t: cls.__parse_op_add_sub(t[0])),
                (op_comp, 2, opAssoc.LEFT, lambda t: cls.__parse_op_comp(t[0])),
                (Keyword("and").suppress(), 2, opAssoc.LEFT, lambda t: And(*t[0])),
                (Keyword("or").suppress(), 2, opAssoc.LEFT, lambda t: Or(*t[0])),
            ],
        )

        expression.enablePackrat()
        return expression

    @classmethod
    def condition(cls) -> Token:
        return cls.expression() + StringEnd()

    @classmethod
    def action(cls) -> Token:
        action = cls.__identifier() + Keyword(":=").suppress() + cls.expression() + StringEnd()
        action.setParseAction(lambda t: Assignment(t[0], t[1]))
        return action