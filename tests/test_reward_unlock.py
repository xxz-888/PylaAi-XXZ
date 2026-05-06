import unittest

import cv2
import numpy as np

from state_finder import get_in_game_state, is_in_reward_unlock


class RewardUnlockTests(unittest.TestCase):
    @staticmethod
    def draw_reward_unlock_screen():
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        blue = cv2.cvtColor(
            np.full((1, 1, 3), (104, 210, 215), dtype=np.uint8),
            cv2.COLOR_HSV2BGR,
        )[0, 0]
        light_blue = cv2.cvtColor(
            np.full((1, 1, 3), (98, 70, 230), dtype=np.uint8),
            cv2.COLOR_HSV2BGR,
        )[0, 0]
        yellow = cv2.cvtColor(
            np.full((1, 1, 3), (28, 220, 245), dtype=np.uint8),
            cv2.COLOR_HSV2BGR,
        )[0, 0]
        image[:, :] = blue
        image[160:230, 760:1180] = (245, 245, 245)
        image[175:245, 750:1190] = (10, 10, 10)
        image[160:230, 760:1180] = (245, 245, 245)
        image[300:520, 780:1140] = light_blue
        image[520:620, 820:1100] = (0, 0, 0)
        image[650:730, 770:1160] = (0, 0, 0)
        image[630:710, 790:1140] = yellow
        return image

    def test_reward_unlock_detector_accepts_blue_unlocked_screen(self):
        image = self.draw_reward_unlock_screen()

        self.assertTrue(is_in_reward_unlock(image))
        self.assertEqual(get_in_game_state(image), "reward_unlock")

    def test_reward_unlock_detector_rejects_match_like_screen(self):
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        image[:, :] = (70, 60, 80)
        image[160:230, 760:1180] = (245, 245, 245)
        image[630:710, 790:1140] = (0, 220, 255)

        self.assertFalse(is_in_reward_unlock(image))
        self.assertNotEqual(get_in_game_state(image), "reward_unlock")


if __name__ == "__main__":
    unittest.main()
