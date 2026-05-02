import unittest
import numpy as np
import cv2

from state_finder import get_star_drop_type


class StarDropHandlingTests(unittest.TestCase):
    def test_daily_wins_green_reward_is_fast_tap_drop(self):
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        green_bgr = cv2.cvtColor(
            np.full((1, 1, 3), (58, 230, 230), dtype=np.uint8),
            cv2.COLOR_HSV2BGR,
        )[0, 0]
        image[110:850, 430:1330] = green_bgr
        image[30:100, 20:430] = (245, 245, 245)

        self.assertEqual(get_star_drop_type(image), "standard")


if __name__ == "__main__":
    unittest.main()
