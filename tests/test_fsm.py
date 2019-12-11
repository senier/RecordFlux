import unittest

from rflx.fsm import FSM, State, StateMachine, StateName, Transition
from rflx.model import ModelError


class TestFSM(unittest.TestCase):
    def setUp(self) -> None:
        self.maxDiff = None  # pylint: disable=invalid-name

    def assert_parse_exception_string(self, string: str, regex: str) -> None:
        with self.assertRaisesRegex(ModelError, regex):
            FSM().parse_string("fsm", string)

    def test_simple_fsm(self) -> None:
        f = FSM()
        f.parse_string(
            "fsm",
            """
                initial: START
                final: END
                states:
                  - name: START
                    transitions:
                      - target: END
                  - name: END
            """,
        )
        expected = StateMachine(
            initial=StateName("START"),
            final=StateName("END"),
            states=[
                State(name=StateName("START"), transitions=[Transition(target=StateName("END"))]),
                State(name=StateName("END")),
            ],
        )
        self.assertEqual(f.fsms["fsm"], expected)

    def test_missing_initial(self) -> None:
        self.assert_parse_exception_string(
            """
                final: END
                states:
                  - name: START
                    transitions:
                      - target: END
                  - name: END
            """,
            "^missing initial state",
        )

    def test_missing_final(self) -> None:
        self.assert_parse_exception_string(
            """
                initial: START
                states:
                  - name: START
                    transitions:
                      - target: END
                  - name: END
            """,
            "^missing final state",
        )

    def test_missing_states(self) -> None:
        self.assert_parse_exception_string(
            """
                initial: START
                final: END
            """,
            "^missing states",
        )

    def test_empty_states(self) -> None:
        with self.assertRaisesRegex(ModelError, "^empty states"):
            StateMachine(initial=StateName("START"), final=StateName("END"), states=[])
