from typing import Any, Dict, List, Optional, Sequence

import yaml
from pyparsing import ParseFatalException

from rflx.expression import (
    TRUE,
    Channel,
    Declaration,
    Expr,
    PrivateDeclaration,
    Renames,
    Subprogram,
    ValidationError,
    VariableDeclaration,
)
from rflx.fsm_parser import FSMParser
from rflx.model import Base, ModelError
from rflx.statement import Statement


class StateName(Base):
    def __init__(self, name: str):
        self.__name = name

    @property
    def name(self) -> str:
        return self.__name


class Transition(Base):
    def __init__(self, target: StateName, condition: Expr = TRUE):
        self.__target = target
        self.__condition = condition

    @property
    def target(self) -> StateName:
        return self.__target

    @property
    def condition(self) -> Expr:
        return self.__condition

    def validate(self, declarations: Dict[str, Declaration]) -> None:
        self.__condition.simplified().validate(declarations)


class State(Base):
    def __init__(
        self,
        name: StateName,
        transitions: Optional[Sequence[Transition]] = None,
        actions: Optional[Sequence[Statement]] = None,
        declarations: Optional[Dict[str, Declaration]] = None,
    ):
        self.__name = name
        self.__transitions = transitions or []
        self.__actions = actions or []
        self.__declarations = declarations or {}

    @property
    def name(self) -> StateName:
        return self.__name

    @property
    def transitions(self) -> Sequence[Transition]:
        return self.__transitions or []

    @property
    def declarations(self) -> Dict[str, Declaration]:
        return self.__declarations

    @property
    def actions(self) -> Sequence[Statement]:
        return self.__actions


class StateMachine(Base):
    def __init__(
        self,
        name: str,
        initial: StateName,
        final: StateName,
        states: Sequence[State],
        declarations: Dict[str, Declaration],
    ):  # pylint: disable=too-many-arguments
        self.__name = name
        self.__initial = initial
        self.__final = final
        self.__states = states
        self.__declarations = declarations

        if not states:
            raise ModelError("empty states")

        self.__validate_state_existence()
        self.__validate_duplicate_states()
        self.__validate_state_reachability()
        self.__validate_conditions()
        self.__validate_actions()
        self.__validate_declarations()

    def __validate_conditions(self) -> None:
        for s in self.__states:
            declarations = s.declarations
            for index, t in enumerate(s.transitions):
                try:
                    t.validate({**self.__declarations, **declarations})
                except ValidationError as e:
                    raise ModelError(f"{e} in transition {index} of state {s.name.name}")

    def __validate_actions(self) -> None:
        for s in self.__states:
            declarations = s.declarations
            for index, a in enumerate(s.actions):
                try:
                    a.validate({**self.__declarations, **declarations})
                except ValidationError as e:
                    raise ModelError(f"{e} in action {index} of state {s.name.name}")

    def __validate_state_existence(self) -> None:
        state_names = [s.name for s in self.__states]
        if self.__initial not in state_names:
            raise ModelError(
                f'initial state "{self.__initial.name}" does not exist in' f' "{self.__name}"'
            )
        if self.__final not in state_names:
            raise ModelError(
                f'final state "{self.__final.name}" does not exist in' f' "{self.__name}"'
            )
        for s in self.__states:
            for t in s.transitions:
                if t.target not in state_names:
                    raise ModelError(
                        f'transition from state "{s.name.name}" to non-existent state'
                        f' "{t.target.name}" in "{self.__name}"'
                    )

    def __validate_duplicate_states(self) -> None:
        state_names = [s.name for s in self.__states]
        seen: Dict[str, int] = {}
        duplicates: List[str] = []
        for n in [x.name for x in state_names]:
            if n not in seen:
                seen[n] = 1
            else:
                if seen[n] == 1:
                    duplicates.append(n)
                seen[n] += 1

        if duplicates:
            raise ModelError("duplicate states {dups}".format(dups=", ".join(sorted(duplicates))))

    def __validate_state_reachability(self) -> None:
        inputs: Dict[str, List[str]] = {}
        for s in self.__states:
            for t in s.transitions:
                if t.target.name in inputs:
                    inputs[t.target.name].append(s.name.name)
                else:
                    inputs[t.target.name] = [s.name.name]
        unreachable = [
            s.name.name
            for s in self.__states
            if s.name != self.__initial and s.name.name not in inputs
        ]
        if unreachable:
            raise ModelError("unreachable states {states}".format(states=", ".join(unreachable)))

        detached = [
            s.name.name for s in self.__states if s.name != self.__final and not s.transitions
        ]
        if detached:
            raise ModelError("detached states {states}".format(states=", ".join(detached)))

    @classmethod
    def __entity_name(cls, declaration: Declaration) -> str:
        if isinstance(declaration, Subprogram):
            return "subprogram"
        if isinstance(declaration, VariableDeclaration):
            return "variable"
        if isinstance(declaration, Renames):
            return "renames"
        if isinstance(declaration, Channel):
            return "channel"
        if isinstance(declaration, PrivateDeclaration):
            return "private declaration"
        raise ModelError(f"Unsupported entity {type(declaration).__name__}")

    def __validate_declarations(self) -> None:
        declarations = self.__declarations
        for s in self.__states:
            for decl in s.declarations:
                if decl in declarations:
                    raise ModelError(
                        f"local variable {decl} shadows global declaration in state {s.name.name}"
                    )
                if not s.declarations[decl].is_referenced:
                    raise ModelError(f"unused local variable {decl} in state {s.name.name}")
        for k, d in declarations.items():
            if k.upper() in ["READ", "WRITE", "CALL", "DATA_AVAILABLE", "APPEND", "EXTEND"]:
                raise ModelError(
                    f"{self.__entity_name(d)} declaration shadows builtin subprogram {k.upper()}"
                )
            try:
                d.validate(declarations)
            except ValidationError as e:
                raise ModelError(f"{e} in global {self.__entity_name(d)} {k}")
        for k, d in declarations.items():
            # pylint: disable=fixme
            # FIXME: We do not validate variable declarations at the moment
            if isinstance(d, PrivateDeclaration):
                return
            if not d.is_referenced:
                raise ModelError(f"unused {self.__entity_name(d)} {k}")

    @property
    def name(self) -> str:
        return self.__name

    @property
    def initial(self) -> StateName:
        return self.__initial

    @property
    def final(self) -> StateName:
        return self.__final

    @property
    def states(self) -> Sequence[State]:
        return self.__states


class FSM:
    def __init__(self) -> None:
        self.__fsms: List[StateMachine] = []

    @classmethod
    def __parse_functions(cls, doc: Dict[str, Any], result: Dict[str, Declaration]) -> None:
        if "functions" not in doc:
            return
        for index, f in enumerate(doc["functions"]):
            try:
                name, declaration = FSMParser.declaration().parseString(f)[0]
            except Exception as e:
                raise ModelError(f"error parsing global function declaration {index} ({e})")
            if name in result:
                raise ModelError(f"conflicting function {name}")
            result[name] = declaration

    @classmethod
    def __parse_variables(cls, doc: Dict[str, Any], result: Dict[str, Declaration]) -> None:
        if "variables" not in doc:
            return
        for index, f in enumerate(doc["variables"]):
            try:
                name, declaration = FSMParser.declaration().parseString(f)[0]
            except Exception as e:
                raise ModelError(f"error parsing global variable declaration {index} ({e})")
            if name in result:
                raise ModelError(f"conflicting variable {name}")
            result[name] = declaration

    @classmethod
    def __parse_types(cls, doc: Dict[str, Any], result: Dict[str, Declaration]) -> None:
        if "types" not in doc:
            return
        for index, f in enumerate(doc["types"]):
            try:
                name, declaration = FSMParser.declaration().parseString(f)[0]
            except Exception as e:
                raise ModelError(f"error parsing private variable declaration {index} ({e})")
            if name in result:
                raise ModelError(f"conflicting type {name}")
            result[name] = declaration

    @classmethod
    def __parse_channels(cls, doc: Dict[str, Any], result: Dict[str, Declaration]) -> None:
        if "channels" not in doc:
            return
        for index, f in enumerate(doc["channels"]):
            if "name" not in f:
                raise ModelError(f"Channel {index} has no name")
            if "mode" not in f:
                raise ModelError(f"Channel {f['name']} has no mode")
            modes = {
                "Read": {"read": True, "write": False},
                "Write": {"read": False, "write": True},
                "Read_Write": {"read": True, "write": True},
            }
            if f["name"] in result:
                raise ModelError(f'conflicting channel {f["name"]}')
            mode = f["mode"]
            try:
                result[f["name"]] = Channel(modes[mode]["read"], modes[mode]["write"])
            except KeyError:
                raise ModelError(f"Channel {f['name']} has invalid mode {mode}")

    @classmethod
    def __parse_renames(cls, doc: Dict[str, Any], result: Dict[str, Declaration]) -> None:
        if "renames" not in doc:
            return
        for index, f in enumerate(doc["renames"]):
            try:
                name, declaration = FSMParser.declaration().parseString(f)[0]
            except Exception as e:
                raise ModelError(f"error parsing renames declaration {index} ({e})")
            if name in result:
                raise ModelError(f"conflicting renames {name}")
            result[name] = declaration

    @classmethod
    def __parse_declarations(cls, doc: Dict[str, Any]) -> Dict[str, Declaration]:
        result: Dict[str, Declaration] = {}
        cls.__parse_functions(doc, result)
        cls.__parse_variables(doc, result)
        cls.__parse_types(doc, result)
        cls.__parse_channels(doc, result)
        cls.__parse_renames(doc, result)
        return result

    @classmethod
    def __parse_transitions(cls, state: Dict) -> List[Transition]:
        transitions: List[Transition] = []
        sname = state["name"]
        if "transitions" in state:
            for index, t in enumerate(state["transitions"]):
                rest = t.keys() - ["condition", "target", "doc"]
                if rest:
                    elements = ", ".join(sorted(rest))
                    raise ModelError(
                        f"unexpected elements [{elements}] in transition {index} state {sname}"
                    )
                condition = TRUE
                if "condition" in t:
                    try:
                        condition = FSMParser.expression().parseString(t["condition"])[0]
                    except ParseFatalException as e:
                        tname = t["target"]
                        raise ModelError(
                            f"error parsing condition {index} from state "
                            f'"{sname}" to "{tname}" ({e})'
                        )
                transitions.append(Transition(target=StateName(t["target"]), condition=condition))
        return transitions

    def __parse_states(self, doc: Dict[str, Any]) -> List[State]:
        states: List[State] = []
        for s in doc["states"]:
            sname = s["name"]
            rest = s.keys() - ["name", "actions", "transitions", "variables", "doc"]
            if rest:
                elements = ", ".join(sorted(rest))
                raise ModelError(f"unexpected elements [{elements}] in state {sname}")
            actions: List[Statement] = []
            if "actions" in s and s["actions"]:
                for index, a in enumerate(s["actions"]):
                    try:
                        actions.append(FSMParser.action().parseString(a)[0])
                    except Exception as e:
                        raise ModelError(f"error parsing action {index} of state {sname} ({e})")
            declarations: Dict[str, Declaration] = {}
            if "variables" in s and s["variables"]:
                for index, v in enumerate(s["variables"]):
                    try:
                        dname, declaration = FSMParser.declaration().parseString(v)[0]
                    except Exception as e:
                        raise ModelError(f"error parsing variable {index} of state {sname} ({e})")
                    declarations[dname] = declaration
            states.append(
                State(
                    name=StateName(s["name"]),
                    transitions=self.__parse_transitions(s),
                    actions=actions,
                    declarations=declarations,
                )
            )
        return states

    def __parse(self, name: str, doc: Dict[str, Any]) -> None:
        if "initial" not in doc:
            raise ModelError("missing initial state")
        if "final" not in doc:
            raise ModelError("missing final state")
        if "states" not in doc:
            raise ModelError("missing states")

        rest = set(doc.keys()) - set(
            ["channels", "variables", "functions", "initial", "final", "states", "renames", "types"]
        )
        if rest:
            raise ModelError("unexpected elements [{}]".format(", ".join(sorted(rest))))

        fsm = StateMachine(
            name=name,
            initial=StateName(doc["initial"]),
            final=StateName(doc["final"]),
            states=self.__parse_states(doc),
            declarations=self.__parse_declarations(doc),
        )
        self.__fsms.append(fsm)

    def parse(self, name: str, filename: str) -> None:
        with open(filename, "r") as data:
            self.__parse(name, yaml.safe_load(data))

    def parse_string(self, name: str, string: str) -> None:
        self.__parse(name, yaml.safe_load(string))

    @property
    def fsms(self) -> List[StateMachine]:
        return self.__fsms
