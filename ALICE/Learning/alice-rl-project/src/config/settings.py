# Configuration settings for the reinforcement learning project

# Hyperparameters for the neural networks
HYPERPARAMS = {
    'learning_rate': 0.001,
    'batch_size': 64,
    'num_epochs': 1000,
    'discount_factor': 0.99,
    'policy_hidden_layers': [128, 128],
    'value_hidden_layers': [128, 128],
}

# Paths for saving models and logs
PATHS = {
    'model_save_path': './models/',
    'log_path': './logs/',
}

# Environment settings
ENV_SETTINGS = {
    'max_steps': 1000,
    'render': False,
}

# Seed for reproducibility
SEED = 42