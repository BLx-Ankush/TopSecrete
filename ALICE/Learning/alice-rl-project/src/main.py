import gym
import numpy as np
from models.policy_network import PolicyNetwork
from models.value_network import ValueNetwork
from training.trainer import Trainer
from envs.alice_env import AliceEnv

def main():
    # Initialize the environment
    env = AliceEnv()

    # Initialize the neural networks
    policy_network = PolicyNetwork(input_dim=env.observation_space.shape[0], output_dim=env.action_space.n)
    value_network = ValueNetwork(input_dim=env.observation_space.shape[0])

    # Initialize the trainer
    trainer = Trainer(env, policy_network, value_network)

    # Start the training process
    trainer.train(episodes=1000)

if __name__ == "__main__":
    main()