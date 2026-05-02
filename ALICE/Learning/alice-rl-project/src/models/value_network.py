class ValueNetwork:
    def __init__(self, input_dim, hidden_layers, output_dim):
        self.input_dim = input_dim
        self.hidden_layers = hidden_layers
        self.output_dim = output_dim
        self.model = self.build_model()

    def build_model(self):
        import torch
        import torch.nn as nn

        layers = []
        previous_dim = self.input_dim
        for hidden_dim in self.hidden_layers:
            layers.append(nn.Linear(previous_dim, hidden_dim))
            layers.append(nn.ReLU())
            previous_dim = hidden_dim
        layers.append(nn.Linear(previous_dim, self.output_dim))
        
        return nn.Sequential(*layers)

    def forward(self, x):
        return self.model(x)

    def predict(self, state):
        import torch
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state)
            return self.forward(state_tensor).numpy()