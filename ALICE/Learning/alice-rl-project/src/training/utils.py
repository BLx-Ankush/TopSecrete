def calculate_loss(predictions, targets):
    # Calculate the mean squared error loss
    return ((predictions - targets) ** 2).mean()

def update_weights(optimizer, model):
    # Update the model weights using the optimizer
    optimizer.step()
    optimizer.zero_grad()

def log_metrics(metrics, step):
    # Log the metrics for tracking training progress
    for key, value in metrics.items():
        print(f'Step {step}: {key} = {value}')