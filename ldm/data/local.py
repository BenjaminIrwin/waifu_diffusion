import os
import numpy as np
import PIL
from PIL import Image
from torch.utils.data import Dataset
from torchvision import transforms

import glob

import random


class LocalBase(Dataset):
    def __init__(self,
                 data_root,
                 size=None,
                 interpolation="bicubic",
                 flip_p=0.5
                 ):
        super().__init__()

        print('Fetching data.')

        ext = ['png', 'jpg', 'jpeg', 'bmp']
        self.image_files = []
        [self.image_files.extend(glob.glob(f'{data_root}/img/' + '*.' + e)) for e in ext]

        print('Constructing image-caption map.')

        self.examples = {}
        self.hashes = []
        for i in self.image_files:
            hash = i[len(f'{data_root}/img/'):].split('.')[0]
            self.examples[hash] = {
                'image': i,
                'text': f'{data_root}/txt/{hash}.txt'
            }
            self.hashes.append(hash)

        print(f'image-caption map has {len(self.examples.keys())} examples')

        self.size = size
        self.interpolation = {"linear": PIL.Image.LINEAR,
                              "bilinear": PIL.Image.BILINEAR,
                              "bicubic": PIL.Image.BICUBIC,
                              "lanczos": PIL.Image.LANCZOS,
                              }[interpolation]
        self.flip = transforms.RandomHorizontalFlip(p=flip_p)

    def random_sample(self):
        return self.__getitem__(random.randint(0, self.__len__() - 1))
    
    def sequential_sample(self, i):
        if i >= self.__len__() - 1:
            return self.__getitem__(0)
        return self.__getitem__(i + 1)

    def skip_sample(self, i):
        if self.shuffle:
            return self.random_sample()
        return self.sequential_sample(i=i)

    def get_caption(self, i):
        example = self.examples[self.hashes[i]]
        caption = open(example['text'], 'r').read()
        caption = caption.replace('  ', ' ').replace('\n', ' ').lstrip().rstrip()
        return caption

    def __len__(self):
        return len(self.image_files)

    def __getitem__(self, i):
        example_ret = {}
        try:
            image_file = self.examples[self.hashes[i]]['image']
            image = Image.open(image_file)
            if not image.mode == "RGB":
                image = image.convert("RGB")
        except (OSError, ValueError) as e:
            print(f'Error with {image_file} -- skipping {i}')
            return self.skip_sample(i)
        
        try:
            caption = self.get_caption(i)
            if caption == None:
                raise ValueError
        except (OSError, ValueError) as e:
            print(f'Error with caption of {image_file} -- skipping {i}')
            return self.skip_sample(i)

        example_ret['caption'] = caption

        # default to score-sde preprocessing
        img = np.array(image).astype(np.uint8)
        crop = min(img.shape[0], img.shape[1])
        h, w, = img.shape[0], img.shape[1]
        img = img[(h - crop) // 2:(h + crop) // 2,
              (w - crop) // 2:(w + crop) // 2]

        image = Image.fromarray(img)
        if self.size is not None:
            image = image.resize((self.size, self.size), resample=self.interpolation)

        image = self.flip(image)
        image = np.array(image).astype(np.uint8)
        example_ret["image"] = (image / 127.5 - 1.0).astype(np.float32)
        return example_ret


if __name__ == "__main__":
    dataset = LocalBase('../250k_data-0', size=512)
    example = dataset.__getitem__(137)
    print(example['caption'])
    image = example['image']
    image = ((image + 1) * 127.5).astype(np.uint8)
    image = Image.fromarray(image)
    image.save('example.png')