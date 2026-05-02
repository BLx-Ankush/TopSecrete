def evaluate_agent(agent, env, num_episodes=100):
    total_rewards = 0
    for episode in range(num_episodes):
        state = env.reset()
        done = False
        episode_reward = 0
        
        while not done:
            action = agent.act(state)
            state, reward, done, _ = env.step(action)
            episode_reward += reward
        
        total_rewards += episode_reward
        print(f"Episode {episode + 1}: Reward = {episode_reward}")
    
    average_reward = total_rewards / num_episodes
    print(f"Average Reward over {num_episodes} episodes: {average_reward}")
    return average_reward

def evaluate_model(model, env, num_episodes=100):
    total_rewards = 0
    for episode in range(num_episodes):
        state = env.reset()
        done = False
        episode_reward = 0
        
        while not done:
            action = model.predict(state)
            state, reward, done, _ = env.step(action)
            episode_reward += reward
        
        total_rewards += episode_reward
        print(f"Episode {episode + 1}: Reward = {episode_reward}")
    
    average_reward = total_rewards / num_episodes
    print(f"Average Reward over {num_episodes} episodes: {average_reward}")
    return average_reward

if __name__ == "__main__":
    import sys
    from src.envs.alice_env import AliceEnv
    from src.models.policy_network import PolicyNetwork
    from src.models.value_network import ValueNetwork

    env = AliceEnv()
    policy_model = PolicyNetwork()
    value_model = ValueNetwork()

    evaluate_agent(policy_model, env)
    evaluate_model(value_model, env)