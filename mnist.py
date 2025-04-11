# Based on: https://www.kaggle.com/code/joseguzman/pytorch-simple-ann-for-mnist

import time
import torch
from torch import nn
import torchvision.transforms as T
from torchvision import datasets
from torch.utils.data import DataLoader
from database import update_experiment

def run_experiment(job_id, lr, epochs, batch_size):
    transform = T.ToTensor()
    train_dataset = datasets.MNIST(root="./data", train=True, download=True, transform=transform)
    test_dataset = datasets.MNIST(root="./data", train=False, download=True, transform=transform)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=500, shuffle=False)

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.fc1 = nn.Linear(784, 120)
            self.fc2 = nn.Linear(120, 84)
            self.fc3 = nn.Linear(84, 10)
        def forward(self, x):
            x = torch.relu(self.fc1(x))
            x = torch.relu(self.fc2(x))
            return torch.log_softmax(self.fc3(x), dim=1)

    model = Net()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()

    start_time = time.time()
    for epoch in range(epochs):
        for img, label in train_loader:
            y_pred = model(img.view(img.shape[0], -1))
            loss = criterion(y_pred, label)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        update_experiment(job_id, current_epoch=epoch+1, loss=round(loss.item(), 4))
        # print(f"Epoch {epoch+1}/{epochs}, Loss: {loss.item()}")

    correct = 0
    with torch.no_grad():
        for img, label in test_loader:
            y_val = model(img.view(img.shape[0], -1))
            _, predicted = torch.max(y_val, 1)
            correct += (predicted == label).sum()

    accuracy = round(correct.item() / len(test_loader.dataset), 4)
    runtime = round(time.time() - start_time, 2)
    update_experiment(job_id, accuracy=accuracy, runtime=runtime, status='done')
    print(f"Experiment {job_id} completed with accuracy: {accuracy}, runtime: {runtime} seconds")
