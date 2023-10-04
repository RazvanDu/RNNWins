import os
import json
import torch
from torch import optim
from torch.utils.data import DataLoader

os.environ['RWKV_RUN_DEVICE'] = 'cpu'

# Your existing imports
from src.model_run import RWKV_RNN, GREBE_RNN
from src.utils import TOKENIZER

# Define constants
MODEL_NAME = 'RWKV-4-Pile-169M-20220807-8023'
WORD_NAME = ['20B_tokenizer.json', '20B_tokenizer.json']
DATA_FILE = '../winogrande_1.1/train_s.jsonl'
N_LAYER = 12
N_EMBD = 768
CTX_LEN = 1024
SEQ_LEN = 100  # You may adjust this
BATCH_SIZE = 1  # You may adjust this

# Initialize model and tokenizer
model = GREBE_RNN(MODEL_NAME, 'cpu', 'RWKV', N_LAYER, N_EMBD, CTX_LEN)
tokenizer = TOKENIZER(WORD_NAME, UNKNOWN_CHAR=None)


def load_winogrande_data(file_path):
    data = []
    with open(file_path, 'r') as f:
        for line in f:
            item = json.loads(line.strip())
            data.append(item)
    return data


class WinograndeDataset(torch.utils.data.Dataset):
    def __init__(self, data, tokenizer):
        self.data = data
        self.tokenizer = tokenizer

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]

        sentence = item['sentence'].replace('_', '{}')
        option1, option2 = item['option1'], item['option2']
        context1 = "Who is referred to by the blank space? " + sentence.format(
            option1) + " Who is referred to by the blank space?"
        context2 = "Who is referred to by the blank space? " + sentence.format(
            option2) + " Who is referred to by the blank space?"

        tokenized1 = tokenizer.tokenizer.encode(context1)
        tokenized2 = tokenizer.tokenizer.encode(context2)

        label = int(item['answer']) - 1  # Converting 1-indexed to 0-indexed

        return tokenized1, tokenized2, label


dataset = WinograndeDataset(load_winogrande_data(DATA_FILE), tokenizer)
train_loader = DataLoader(dataset, shuffle=True, batch_size=BATCH_SIZE)

optimizer = optim.Adam(model.parameters(), lr=0.005)
loss_fn = torch.nn.CrossEntropyLoss()

# Training loop
n_epochs = 40
for epoch in range(n_epochs):
    for i, (tokenized1, tokenized2, label) in enumerate(train_loader):
        logits1 = model(tokenized1)
        logits2 = model(tokenized2)

        logits = torch.stack([logits1, logits2], dim=1)
        loss = loss_fn(logits, label)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if i % 50 == 0:
            print(f"Epoch {epoch + 1}, Iteration {i}, Loss: {loss.item()}")

print("Training complete")