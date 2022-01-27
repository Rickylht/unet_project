from torch.utils.data import Dataset, DataLoader
import torch
import cv2
import numpy as np
import pandas as pd
import json
import os
from torchvision import transforms, utils
import time
import math
from torch.utils.tensorboard import SummaryWriter
from torchvision import transforms
from torch.utils.data import Dataset
from prepocessing import *

def AppendtoFrame():
    list = []
    with open('img_sample_path.json', 'r') as f:
        bmp_list = json.load(f)
    for i in range(len(bmp_list)):
        
        list.append([id, '.\\data\\imgs\\{}'.format(bmp_list[i]), '.\\data\\masks\\{}'.format(bmp_list[i])])
    
    print("list length: ", len(list))
    frame = None
    frame = pd.DataFrame(list, columns = ['id', 'img_path', 'mask_path'])
    print(frame)
    return frame

class TeethDataset(Dataset):
    def __init__(self, frame, transform):
        self.frame = frame
        self.transform = transform
    
    def __len__(self):
        return len(self.frame)
    
    def __getitem__(self,idx):
        img_name = os.path.join(self.frame.iloc[idx]['img_path'])
        image = cv2.imread(img_name, cv2.IMREAD_GRAYSCALE)
        mask_name = os.path.join(self.frame.iloc[idx]['mask_path'])
        mask = cv2.imread(mask_name, cv2.IMREAD_GRAYSCALE)
        sample = {'image': image, 'mask': mask}

        if self.transform:
            sample = self.transform(sample)
        
        return sample

class ToPILImage(object):
    def __init__(self):
        self.transform = transforms.ToPILImage()
    def __call__(self, sample):
        image, mask = sample['image'], sample['mask']
              
        return {'image': self.transform(image), 'mask': self.transform(mask)}

class Normalize(object):
    
    def __call__(self, sample):
        image, mask = sample['image'], sample['mask']
        
        img_max = torch.max(image)
        img_min = torch.min(image)

        img = (image - img_min)/(img_max - img_min)

        msk_max = torch.max(mask)
        msk_min = torch.min(mask)

        msk = (mask - msk_min)/(msk_max - msk_min)
        
        return {'image': img, 'mask': msk}

class Rescale(object):

    def __init__(self, output_size):
        assert isinstance(output_size, (int, tuple))
        self.output_size = output_size

    def __call__(self, sample):
        image, mask = sample['image'], sample['mask']

        new_h, new_w = self.output_size
        new_h, new_w = int(new_h), int(new_w)

        trnsf = transforms.Resize((self.output_size[0], self.output_size[1]))
        img = trnsf(image)
        msk = trnsf(mask)

        return {'image': img, 'mask': msk}

class ToTensor(object):
    
    def __init__(self):
      self.transform = transforms.ToTensor()
    def __call__(self, sample):
        image, mask = sample['image'], sample['mask']

        return {'image': self.transform(image),
                'mask': self.transform(mask)}

class Contrast_Enhance(object):
    def __init__(self, alpha, beta):
        self.alpha = alpha
        self.beta = beta
    def __call__(self, sample):
        image, mask = sample['image'], sample['mask']
        gaussian_3 = cv2.GaussianBlur(image, (0, 0), 2.0)
        unsharp_image = cv2.addWeighted(image, self.alpha, gaussian_3, self.beta, 0, image)
        return {'image': unsharp_image, 'mask': mask}

class Random_Rotation(object):

    def __init__(self):
        self.angle = 0.0
    def __call__(self, sample):
        seed = int(torch.rand(1) * 120)
        self.angle = float(seed - 50)
        image, mask = sample['image'], sample['mask']
        # grab the dimensions of the image and then determine the
        # centre
        h, w = image.shape[:2]
        (cX, cY) = (w // 2, h // 2)
        # grab the rotation matrix (applying the negative of the
        # angle to rotate clockwise), then grab the sine and cosine
        # (i.e., the rotation components of the matrix)
        M = cv2.getRotationMatrix2D((cX, cY), self.angle, 1.0)

        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])

        # compute the new bounding dimensions of the image
        nW = int((h * sin) + (w * cos))
        nH = int((h * cos) + (w * sin))

        # adjust the rotation matrix to take into account translation
        M[0, 2] += (nW / 2) - cX
        M[1, 2] += (nH / 2) - cY
        # perform the actual rotation and return the image
        image = cv2.warpAffine(image, M, (nW, nH))
        mask = cv2.warpAffine(mask, M, (nW, nH))
        
        #    image = cv2.resize(image, (w,h))
        return {'image': image, 'mask': mask}

class Random_Shift(object):
    def __init__(self):
        self.shift = [0, 0]

    def __call__(self, sample):
        seed = int(torch.rand(1) * 100)
        rng = np.random.default_rng(seed)
        self.shift[0] = rng.integers(low=-100, high=100, size=1)
        self.shift[1] = rng.integers(low=-100, high=100, size=1)
        image, mask = sample['image'], sample['mask']
        # Translation matrix
        M = np.float32([[1, 0, self.shift[0]], [0, 1, self.shift[1]]])

        try:
            rows, cols = image.shape[:2]

            # warpAffine does appropriate shifting given the
            # translation matrix.
            image = cv2.warpAffine(image, M, (cols, rows))
            mask = cv2.warpAffine(mask, M, (cols, rows))

            return {'image': image, 'mask': mask}

        except IOError:
            print('Error while reading files !!!')
