import unittest

from main import normalize_detected_state


class StateTransitionGuardTests(unittest.TestCase):
    def test_out_of_match_rewards_are_ignored_until_result_or_lobby_was_seen(self):
        for state in ("prestige_reward", "trophy_reward"):
            with self.subTest(state=state):
                self.assertEqual(
                    normalize_detected_state(
                        state,
                        previous_state="match",
                        lobby_seen_since_match=False,
                        match_result_seen=False,
                    ),
                    "match",
                )

    def test_out_of_match_rewards_are_allowed_after_result_screen(self):
        for state in ("prestige_reward", "trophy_reward"):
            with self.subTest(state=state):
                self.assertEqual(
                    normalize_detected_state(
                        state,
                        previous_state="end_3rd",
                        lobby_seen_since_match=False,
                        match_result_seen=True,
                    ),
                    state,
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

    def test_out_of_match_rewards_are_blocked_after_lobby_start_press_without_result(self):
        for state in ("prestige_reward", "trophy_reward"):
            with self.subTest(state=state):
                self.assertEqual(
                    normalize_detected_state(
                        state,
                        previous_state="lobby",
                        lobby_seen_since_match=True,
                        match_launch_pending=True,
                        match_result_seen=False,
                    ),
                    "match",
                )

    def test_out_of_match_rewards_are_allowed_after_result_even_if_launch_pending(self):
        for state in ("prestige_reward", "trophy_reward"):
            with self.subTest(state=state):
                self.assertEqual(
                    normalize_detected_state(
                        state,
                        previous_state="end_3rd",
                        lobby_seen_since_match=False,
                        match_launch_pending=True,
                        match_result_seen=True,
                    ),
                    state,
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
