import pandas as pd
import numpy as np
from tqdm import tqdm
import click
import yaml

# import cli_args

import logging
import torchvision as tv
import torch
from pathlib import Path

from dataset import HCSData
from models import VGG16, VAE


logging.basicConfig(level=logging.INFO)

# Parameters
with open("./configs/params.yml", 'r') as f:
    p = yaml.load(f)


@click.command()
@click.option("--csv_file", type=click.Path(exists=True), default=p['csv_file'])
@click.option("--debug/--no-debug", default=p['debug'])
@click.option("-e", "--epochs", type=int, default=p['epochs'])
@click.option("-b", "--batch_size", type=int, default=p['batch_size'])
@click.option("-s", "--split", type=float, default=p['split'])
def train(csv_file, debug, epochs, batch_size, split):
    # Set up gpu/cpu device
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

    # Dataset
    data = HCSData.from_csv('data/mini.csv')  # Load dataset
    train, test = data.split(0.8)  # Split data into train and test

    train_loader = torch.utils.data.DataLoader(  # Generate a training data loader
        train, batch_size=batch_size, shuffle=False)
    test_loader = torch.utils.data.DataLoader(  # Generate a testing data loader
        test, batch_size=batch_size, shuffle=False)

    # Define Model
    net = VGG16()
    # Move Model to GPU
    if torch.cuda.device_count() > 1:  # If multiple gpu's
        net = torch.nn.DataParallel(net)  # Parallelize
    net.to(device)  # Move model to device

    # Define loss and optimizer
    criterion = torch.nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(net.parameters())
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, 'min')

    print("Training...")

    tr_correct = 0
    tr_total = 0
    correct = 0
    total = 0
    # Training
    for epoch in range(epochs):  # Iter through epochcs
        cum_loss = 0
        msg = f"Training epoch {epoch+1}: "
        ttl = len(train_loader)  # Iter through batches
        for batch_n, (X, Y) in enumerate(train_loader):
            x, y = X.to(device), Y.to(device)  # Move batch samples to gpu

            o = net(x)  # Forward pass
            optimizer.zero_grad()  # Reset gradients
            loss = criterion(o, y)  # Compute Loss
            loss.backward()  # Propagate loss, compute gradients
            optimizer.step()  # Update weights

            cum_loss += loss.item()

            # tqdm.write((
            #     f"Batch {batch_n+1}:"
            #     f"\tLoss: {loss.item():.4f}"
            #     f"\tPrediction: {o.argmax()}"
            #     f" \t Label: {y.item()}"
            # ))

            # PERFORM SOME VALIDATION METRIC
            _, predicted = torch.max(o.data, 1)
            tr_total += y.size(0)
            tr_correct += (predicted == y).sum().item()

        # scheduler.step(metric)  # Update the learning rate

        print(f"Training loss: {cum_loss:.2f}")

        with torch.no_grad():

            msg = f"Testing epoch {epoch+1}: "
            ttl = len(test_loader)  # Iter through batches
            for batch_n, (X, Y) in enumerate(test_loader):
                x, y = X.to(device), Y.to(device)  # Move batch samples to gpu
                o = net(x)  # Forward pass

                # PERFORM SOME VALIDATION METRIC
                _, predicted = torch.max(o.data, 1)
                total += y.size(0)
                correct += (predicted == y).sum().item()

            print(f"Epoch {epoch}:")
            if epoch % 10 == 0:
                print('Accuracy of the network on the train images: %d %%' % (
                    100 * tr_correct / tr_total))
                print('Accuracy of the network on the test images: %d %%' % (
                    100 * correct / total))
                correct = 0
                total = 0
                tr_correct = 0
                tr_total = 0

        scheduler.step(correct / total)


if __name__ == '__main__':
    train()
