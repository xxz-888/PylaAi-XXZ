import unittest

from main import normalize_detected_state


class StateTransitionGuardTests(unittest.TestCase):
    def test_prestige_reward_is_ignored_until_lobby_was_seen(self):
        self.assertEqual(
            normalize_detected_state(
                "prestige_reward",
                previous_state="match",
                lobby_seen_since_match=False,
            ),
            "match",
        )

    def test_prestige_reward_is_allowed_after_lobby_was_seen(self):
        self.assertEqual(
            normalize_detected_state(
                "prestige_reward",
                previous_state="lobby",
                lobby_seen_since_match=True,
            ),
            "prestige_reward",
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
