import unittest
from src.models.policy_network import PolicyNetwork
from src.models.value_network import ValueNetwork
import torch

class TestNeuralNetworks(unittest.TestCase):

    def setUp(self):
        self.policy_net = PolicyNetwork(input_dim=4, output_dim=2, hidden_layers=[64, 64])
        self.value_net = ValueNetwork(input_dim=4, hidden_layers=[64, 64])

    def test_policy_network_forward(self):
        state = torch.randn(1, 4)
        action_probs = self.policy_net(state)
        self.assertEqual(action_probs.shape, (1, 2), "Policy network output shape is incorrect.")

    def test_value_network_forward(self):
        state = torch.randn(1, 4)
        value = self.value_net(state)
        self.assertEqual(value.shape, (1, 1), "Value network output shape is incorrect.")

    def test_policy_network_training(self):
        state = torch.randn(1, 4)
        action = torch.tensor([[1]])
        reward = torch.tensor([[1.0]])
        next_state = torch.randn(1, 4)
        loss = self.policy_net.train_on_batch(state, action, reward, next_state)
        self.assertIsNotNone(loss, "Loss should not be None after training.")

    def test_value_network_training(self):
        state = torch.randn(1, 4)
        reward = torch.tensor([[1.0]])
        loss = self.value_net.train_on_batch(state, reward)
        self.assertIsNotNone(loss, "Loss should not be None after training.")

if __name__ == '__main__':
    unittest.main()