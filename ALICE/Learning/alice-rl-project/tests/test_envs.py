import unittest
from src.envs.alice_env import AliceEnv

class TestAliceEnv(unittest.TestCase):

    def setUp(self):
        self.env = AliceEnv()

    def test_reset(self):
        initial_state = self.env.reset()
        self.assertIsNotNone(initial_state)

    def test_step(self):
        self.env.reset()
        action = self.env.action_space.sample()  # Assuming action_space is defined
        next_state, reward, done, info = self.env.step(action)
        self.assertIsNotNone(next_state)
        self.assertIsInstance(reward, (int, float))
        self.assertIsInstance(done, bool)
        self.assertIsInstance(info, dict)

    def test_action_space(self):
        self.assertIsNotNone(self.env.action_space)
        self.assertGreater(self.env.action_space.n, 0)  # Assuming discrete action space

    def test_observation_space(self):
        self.assertIsNotNone(self.env.observation_space)

if __name__ == '__main__':
    unittest.main()