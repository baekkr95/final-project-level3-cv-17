import os
import sys
import random
import numpy as np
from PIL import Image

import torch
from torchvision.transforms import Compose, ToTensor, Normalize


def correct_gt_name(data_name, gt_name):
    if data_name == 'RESIDE-OTS':
        gt_name = gt_name.split('_')[0] + '.jpg'
    elif data_name == 'BeDDE':
        gt_name = gt_name.split('_')[0] + '_clear.png'
    elif data_name == 'MRFID':
        gt_name = gt_name[:-5] + '0.jpg'
    elif data_name == 'O_HAZE':
        gt_name = gt_name[:-6] + 'GT' + gt_name[-4:]
    
    return gt_name


def resize_before_crop(haze_img, gt_img, resize_size, crop_size):
    width, height = haze_img.size

    if width > resize_size or height > resize_size:
        if width < height:
            haze_img = haze_img.resize((int(resize_size * (width/height)), resize_size), Image.ANTIALIAS)
            gt_img = gt_img.resize((int(resize_size * (width/height)), resize_size), Image.ANTIALIAS)
        elif width >= height:
            haze_img = haze_img.resize((resize_size, int(resize_size * (height/width))), Image.ANTIALIAS)
            gt_img = gt_img.resize((resize_size, int(resize_size * (height/width))), Image.ANTIALIAS)
        width, height = haze_img.size
    
    if width < crop_size or height < crop_size:
        if width < height:
            haze_img = haze_img.resize((260, int(260 * (height/width))), Image.ANTIALIAS)
            gt_img = gt_img.resize((260, int(260 * (height/width))), Image.ANTIALIAS)
        elif width >= height:
            haze_img = haze_img.resize((int(260 * (width/height)), 260), Image.ANTIALIAS)
            gt_img = gt_img.resize((int(260 * (width/height)), 260), Image.ANTIALIAS)
    
    return haze_img, gt_img


class TrainData_label(torch.utils.data.Dataset):
    def __init__(self, crop_size, resize_size, train_data_dir):
        super().__init__()

        self.data_name = train_data_dir.split('/')[-1]
        if self.data_name == 'RESIDE-OTS':
            self.haze_folder = 'hazy/part1'
        else:
            self.haze_folder = 'hazy'
        self.gt_folder = 'gt'

        self.haze_dir = os.path.join(train_data_dir, self.haze_folder)
        self.gt_dir = os.path.join(train_data_dir, self.gt_folder)
        self.haze_names = sorted(list(os.walk(self.haze_dir))[0][2])
        
        self.label_index_list = [i for i in range(len(self.haze_names))]

        self.crop_size = crop_size
        self.resize_size = resize_size

    def get_images(self, index):
        crop_size = self.crop_size

        haze_name = self.haze_names[index]
        haze_name = os.path.join(self.haze_dir,haze_name)
        gt_name = haze_name.replace(self.haze_folder, self.gt_folder)
        gt_name = correct_gt_name(self.data_name, gt_name)

        haze_img = Image.open(haze_name).convert('RGB')
        gt_img = Image.open(gt_name).convert('RGB')

        haze_img, gt_img = resize_before_crop(haze_img, gt_img, self.resize_size, crop_size)
        width, height = haze_img.size
        
        # --- random crop --- #
        x, y = random.randrange(0, width - crop_size + 1), random.randrange(0, height - crop_size + 1)
        haze_crop_img = haze_img.crop((x, y, x + crop_size, y + crop_size))
        gt_crop_img = gt_img.crop((x, y, x + crop_size, y + crop_size))
        
        transform_haze = Compose([ToTensor(), Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))])
        transform_gt = Compose([ToTensor()])

        haze = transform_haze(haze_crop_img)
        gt = transform_gt(gt_crop_img)

        return haze, gt

    def __getitem__(self, index):
        res = self.get_images(index % len(self.label_index_list))
        return res

    def __len__(self):
        return len(self.haze_names)


class TrainData_unlabel(torch.utils.data.Dataset):
    # Hidden
    # RESIDE_RTTS
    def __init__(self, crop_size, resize_size, train_data_dir, gt_type, unlabel_index_dir):
        super().__init__()
        
        self.data_name = train_data_dir.split('/')[-1]
        self.haze_folder = 'hazy'
        self.gt_folder = gt_type

        self.haze_dir = os.path.join(train_data_dir, self.haze_folder)
        self.gt_dir = os.path.join(train_data_dir, self.gt_folder)
        self.haze_names = sorted(list(os.walk(self.haze_dir))[0][2])
        
        if unlabel_index_dir != '':
            self.unlabel_index_list = np.load(unlabel_index_dir)
        else:
            self.unlabel_index_list = [i for i in range(len(self.haze_names))]
        
        self.crop_size = crop_size
        self.resize_size = resize_size

    def get_images(self, index):
        crop_size = self.crop_size
        
        haze_name = self.haze_names[self.unlabel_index_list[index]]
        haze_name = os.path.join(self.haze_dir,haze_name)
        gt_name = haze_name.replace(self.haze_folder, self.gt_folder)

        haze_img = Image.open(haze_name).convert('RGB')
        gt_img = Image.open(gt_name).convert('RGB')

        haze_img, gt_img = resize_before_crop(haze_img, gt_img, self.resize_size, crop_size)
        width, height = haze_img.size
        
        # --- x,y coordinrate of left-top coner --- #
        x, y = random.randrange(0, width - crop_size + 1), random.randrange(0, height - crop_size + 1)
        haze_crop_img = haze_img.crop((x, y, x + crop_size, y + crop_size))
        gt_crop_img = gt_img.crop((x, y, x + crop_size, y + crop_size))
        
        transform_haze = Compose([ToTensor(), Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))])
        transform_gt = Compose([ToTensor()])

        haze = transform_haze(haze_crop_img)
        gt = transform_gt(gt_crop_img)

        return haze, gt

    def __getitem__(self, index):
        res = self.get_images(index % len(self.unlabel_index_list))
        return res

    def __len__(self):
        return len(self.haze_names)


class ValData_label(torch.utils.data.Dataset):
    def __init__(self, val_data_dir):
        super().__init__()

        self.data_name = val_data_dir.split('/')[-1]
        if self.data_name == 'RESIDE-OTS':
            self.haze_folder = 'hazy/part1'
        else:
            self.haze_folder = 'hazy'
        self.gt_folder = 'gt'

        self.haze_dir = os.path.join(val_data_dir, self.haze_folder)
        self.gt_dir = os.path.join(val_data_dir, self.gt_folder)
        self.haze_names = sorted(list(os.walk(self.haze_dir))[0][2])

    def get_images(self, index):
        haze_name = self.haze_names[index]
        gt_name = haze_name.replace(self.haze_folder, self.gt_folder)
        gt_name = correct_gt_name(self.data_name, gt_name)
        
        haze_img = Image.open(os.path.join(self.haze_dir,haze_name)).convert('RGB')
        gt_img = Image.open(os.path.join(self.gt_dir,gt_name)).convert('RGB')

        haze_reshaped = haze_img
        haze_reshaped = haze_reshaped.resize((512, 512), Image.ANTIALIAS)

        # --- Transform to tensor --- #
        transform_haze = Compose([ToTensor(), Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))])
        transform_gt = Compose([ToTensor()])
        haze = transform_haze(haze_img)
        haze_reshaped = transform_haze(haze_reshaped)
        gt = transform_gt(gt_img)
        
        return haze, haze_reshaped, gt, haze_name

    def __getitem__(self, index):
        res = self.get_images(index)
        return res

    def __len__(self):
        return len(self.haze_names)


class ETCDataset(torch.utils.data.Dataset):
    def __init__(self, val_data_dir):
        super().__init__()

        self.haze_dir = val_data_dir
        self.haze_names = sorted(list(os.walk(self.haze_dir))[0][2])

    def get_images(self, index):
        haze_name = self.haze_names[index]

        haze_img = Image.open(os.path.join(self.haze_dir,haze_name)).convert('RGB')
        haze_reshaped = haze_img
        haze_reshaped = haze_reshaped.resize((512, 512), Image.ANTIALIAS)
        
        # --- Transform to tensor --- #
        transform_haze = Compose([ToTensor(), Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))])
        transform_gt = Compose([ToTensor()])
        haze = transform_haze(haze_img)
        haze_reshaped = transform_haze(haze_reshaped)
        #haze_edge_data = edge_compute(haze)
        #haze = torch.cat((haze, haze_edge_data), 0)

        return haze, haze_reshaped, haze_name

    def __getitem__(self, index):
        res = self.get_images(index)
        return res

    def __len__(self):
        return len(self.haze_names)



if __name__=='__main__':
    
    test_data_dir = '/opt/ml/final-project-level3-cv-17/data/RESIDE_SOTS_OUT/hazy'
    test_data_loader = torch.utils.data.DataLoader(ETCDataset(test_data_dir), batch_size=1, shuffle=False, num_workers=8) # For FFA and MSBDN
    
    for i, data in enumerate(test_data_loader):
       print(f'rst[0] : {data[0].shape}')
       print(f'rst[1] : {data[1].shape}')
       print(f'rst[2] : {data[2]}')