import unittest

from main import normalize_detected_state


class StateTransitionGuardTests(unittest.TestCase):
    def test_out_of_match_rewards_are_ignored_until_lobby_was_seen(self):
        for state in ("prestige_reward", "trophy_reward"):
            with self.subTest(state=state):
                self.assertEqual(
                    normalize_detected_state(
                        state,
                        previous_state="match",
                        lobby_seen_since_match=False,
                    ),
                    "match",
                )

    def test_out_of_match_rewards_are_allowed_after_lobby_was_seen(self):
        for state in ("prestige_reward", "trophy_reward"):
            with self.subTest(state=state):
                self.assertEqual(
                    normalize_detected_state(
                        state,
                        previous_state="lobby",
                        lobby_seen_since_match=True,
                    ),
                    state,
                )

    def test_out_of_match_rewards_are_blocked_after_lobby_start_press(self):
        for state in ("prestige_reward", "trophy_reward"):
            with self.subTest(state=state):
                self.assertEqual(
                    normalize_detected_state(
                        state,
                        previous_state="lobby",
                        lobby_seen_since_match=True,
                        match_launch_pending=True,
                    ),
                    "match",
                )

    def test_other_states_pass_through(self):
        self.assertEqual(
            normalize_detected_state(
                "lobby",
                previous_state="match",
                lobby_seen_since_match=False,
            ),
            "lobby",
        )


if __name__ == "__main__":
    unittest.main()
