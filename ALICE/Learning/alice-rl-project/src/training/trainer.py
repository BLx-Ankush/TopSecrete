class Trainer:
    def __init__(self, policy_network, value_network, replay_buffer, env, config):
        self.policy_network = policy_network
        self.value_network = value_network
        self.replay_buffer = replay_buffer
        self.env = env
        self.config = config
        self.total_steps = 0

    def train(self, num_episodes):
        for episode in range(num_episodes):
            state = self.env.reset()
            done = False
            while not done:
                action = self.policy_network.select_action(state)
                next_state, reward, done, _ = self.env.step(action)
                self.replay_buffer.add(state, action, reward, next_state, done)
                self.total_steps += 1

                if self.total_steps > self.config.batch_size:
                    self.update_networks()

                state = next_state

            self.log_episode(episode)

    def update_networks(self):
        states, actions, rewards, next_states, dones = self.replay_buffer.sample(self.config.batch_size)
        # Update policy network
        policy_loss = self.policy_network.update(states, actions, rewards, next_states, dones)
        # Update value network
        value_loss = self.value_network.update(states, rewards, dones)

    def log_episode(self, episode):
        print(f"Episode {episode} completed. Total steps: {self.total_steps}")