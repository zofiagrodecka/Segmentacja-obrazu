# Author: Jan Prokop, Zofia Grodecka
# OS: WINDOWS

import cv2 as cv
import numpy as np
import sys
import pathlib
from copy import deepcopy
from PIL import Image
from numpy import ma
from skimage.filters import threshold_otsu
import tkinter.filedialog
from tkinter import Tk


class SegmentationManager:
    def __init__(self):
        self.BLUR_PARAM = 0  # pole prywatne (name mangling)

    @staticmethod
    def converting_to_gray_scale(image, show=False):
        gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
        if show:
            cv.imshow('ORIGINAL', image)
            cv.imshow('GRAY_SCALE', gray)
        return gray

    def gaussian_blurring(self, image, show=False):
        gaussed = cv.GaussianBlur(image, (self.BLUR_PARAM, self.BLUR_PARAM), 1, 1, borderType=0)
        if show:
            cv.imshow('BLURRED', gaussed)
        return gaussed

    def split_into_tones(self, image, brackets, show=False, has_beginning=True):
        # Preparing shade sections
        if has_beginning:
            division = brackets
        else:
            division = [0]
            if len(brackets) != 0:
                for i in brackets:
                    division.append(i)
            division.append(255)

        if len(division) == 2:
            tones = [[]]
            for y in range(image.shape[1]):
                for x in range(image.shape[0]):
                    tones[0].append([x, y])
            return tones

        tones = [[] for _ in range(len(division) - 1)]
        for y in range(image.shape[1]):
            for x in range(image.shape[0]):
                intensity = image[x, y]
                for i in range(1, len(division)):
                    if division[i - 1] <= intensity <= division[i]:
                        tones[i - 1].append([x, y])
                        break
        if show:
            self.print_by_tones(image, tones, division)
        return tones

    @staticmethod
    def print_by_tones(image, tones, division):
        masks = []
        N = len(tones)
        for i in range(N):
            copy = deepcopy(image)
            for (x, y) in tones[i]:
                copy[x, y] = 255
            copy_scaled = cv.resize(copy, None, fx=0.2, fy=0.2, interpolation=cv.INTER_LINEAR)
            cv.imshow(f"Tone {i + 1} - {division[i]}:{division[i + 1]}", copy_scaled[:, :])
            masks.append(copy_scaled[:, :])
        all = np.concatenate(masks, axis=1)
        cv.imshow("Tonal sections", all)

    @staticmethod
    def apply_threshold(blurred_image, gray_image, tones):
        n = len(tones)
        mask = np.zeros(blurred_image.shape[:2], np.uint8)
        masked = []
        results = []
        threshold_values = []
        empty_tones = []
        for i in range(n):
            for (x, y) in tones[i]:
                mask[x, y] = 255
            masked_img = cv.bitwise_and(gray_image, gray_image, mask=mask)
            thr_masked = ma.masked_array(masked_img, mask == 0)  # w masce z np. sa 1 tam gdzie sa 0 (czern) w mask
            if thr_masked.compressed().shape[0] != 0:
                value = threshold_otsu(thr_masked.compressed())
                threshold_values.append(value)
                threshold, image_result = cv.threshold(masked_img, value, 255, cv.THRESH_BINARY)
                results.append(image_result)
            else:
                empty_tones.append(i)
                results.append(None)
                threshold_values.append(None)
            masked.append(masked_img)
            mask = np.zeros(blurred_image.shape[:2], np.uint8)
        return masked, threshold_values, results, empty_tones

    @staticmethod
    def change_threshold(image, new_value, show=False):
        threshold, image_result = cv.threshold(image, new_value, 255, cv.THRESH_BINARY)
        if show:
            cv.imshow("After change of threshold", image_result)
        return image_result

    @staticmethod
    def change_blur(image, new_value, show=False):
        gaussed = cv.GaussianBlur(image, (0, 0), new_value, new_value, borderType=0)
        if show:
            cv.imshow('After change of blur parameters', gaussed)
        return gaussed

    @staticmethod
    def merge_pictures(results, show=False):
        n = len(results)
        if n < 2:
            if show:
                cv.imshow("Result", results[0])
            return results[0]

        i = 0
        while i < n and results[i] is None:
            i += 1

        j = i + 1
        while j < n and results[j] is None:
            j += 1

        merged = cv.bitwise_or(results[i], results[j])

        i = j + 1
        while i < n:
            while i < n and results[i] is None:
                i += 1
            if i < n:
                merged = cv.bitwise_or(merged, results[i])
                i += 1

        if show:
            cv.imshow("Result", merged)

        return merged

    @staticmethod
    def convert_from_array(image):
        return Image.fromarray(image.astype(np.uint8))


if __name__ == "__main__":

    if len(sys.argv) < 2:
        sys.exit("This program needs arguments: Photo_FILEname(obligatory) or \"explore\", [Thresholds](optional)")

    if sys.argv[1] == "explore":
        Tk().withdraw()
        file_name = tkinter.filedialog.askopenfilename(initialdir="./")
    else:
        file_name = sys.argv[1]

    # Getting array of divisions
    gray_scale_div = []
    for i in range(2, len(sys.argv)):
        parameter = sys.argv[i]
        gray_scale_div.append(int(parameter))

    # Converting image

    manager = SegmentationManager()

    image = cv.imread(file_name)

    gray = manager.converting_to_gray_scale(image, show=True)

    gaussed = manager.gaussian_blurring(gray, show=True)

    Tones = manager.split_into_tones(gaussed, brackets=gray_scale_div, show=True, has_beginning=True)

    masked, thresholded_values, thresholded, empty = manager.apply_threshold(gaussed, gray, Tones)

    result = manager.merge_pictures(thresholded, show=True)

    cv.waitKey()
    cv.destroyAllWindows()

    # Saving result image
    usr_wants_to_save = "_"
    while usr_wants_to_save.upper() != "Y" or usr_wants_to_save.upper() != "N":
        usr_wants_to_save = input("Do you want to save the result? [Y/n]:\n> ")

        if usr_wants_to_save.upper() == "Y":
            # result_file_name = input("Put result file name:\n> ")
            # cv.imwrite(f"Results/{result_file_name}", result, [cv.IMWRITE_PNG_BILEVEL, 1])
            f = tkinter.filedialog.asksaveasfile(mode='w', defaultextension='bmp', initialdir="./")
            cv.imwrite(f.name, result, [cv.IMWRITE_PNG_BILEVEL, 1])
            f.close()
            break
        elif usr_wants_to_save.upper() == "N":
            break
        else:
            print("Wrong response character!")