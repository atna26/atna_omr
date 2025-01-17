import cv2
import math
import numpy as np
from operator import itemgetter
import os
from midiutil.MidiFile import MIDIFile
from collections import defaultdict
import time
import sys


def omr2(image):
    tic = time.time()
    image_path = image

    img = cv2.imread(image_path)
    img = cv2.resize(img, None, fx=0.7, fy=0.7, interpolation=cv2.INTER_CUBIC)

    img_copy = img.copy()
    h_img, w_img, c_img = img_copy.shape
    white_bg = np.full([2*h_img, w_img, c_img], (255,255,255), dtype=np.uint8)
    white_bg[:h_img][:w_img] = img_copy

    img_copy = white_bg
    no_staff_img = img.copy()
    image_height, image_width, _ = img.shape
    thresholded_image = None

    staff_lines = []
    staff_line_width = 0
    staff_space_height = 0

    templates = {
        "whole_note_template" : cv2.imread("resources/templates/Whole-Note/1.png"),
        "half_note_template" : [cv2.imread(f"resources/templates/Half-Note/{i}.png")for i in range(1,4)],
        "half_rest_template" : cv2.imread("resources/templates/Whole-Half-Rest/1.png"),    #possible to find this in beamed notes
        "quarter_note_template" : cv2.imread(f"resources/templates/Quarter-Note/1.png"),     #possible to find this in eigth and sixteenth
        "quarter_rest_template" : cv2.imread("resources/templates/Quarter-Rest/1.png"),
        "eigth_note_templates" : [cv2.imread(f"resources/templates/Eigth-Note/{i}.png") for i in range(1,6)],
        "eigth_rest_template" : cv2.imread("resources/templates/Eigth-Rest/1.png"),
        "sixteenth_note_templates" : [cv2.imread(f"resources/templates/Sixteenth-Note/{i}.png") for i in range(1,5)],
        "sixteenth_rest_template" : cv2.imread("resources/templates/Sixteenth-Rest/1.png"),
        "timesignature_template" : [cv2.imread("resources/templates/Time-Signature/4-4-Time.png"), cv2.imread("resources/templates/Time-Signature/Common-Time.png")],
        "clef_templates" : [cv2.imread("resources/templates/Clef/Bass-Clef.png"), cv2.imread("resources/templates/Clef/Treble-Clef.png")],
        "barline_template" : cv2.imread("resources/templates/Bar-Line.png"),
    # "dot_template" : cv2.imread("resources/templates/Dot.png"),
        "sharp_template" : cv2.imread("resources/templates/Sharp/1.png")
    }
    templates_demo = {
        "whole_note_template" : cv2.imread("resources/templates/Whole-Note/1.png"),
        "half_note_template" : [cv2.imread(f"resources/templates/Half-Note/{i}.png") for i in range (1,3)],
        "quarter_note_template" : cv2.imread(f"resources/templates/Quarter-Note/1.png"),     #possible to find this in eigth and sixteenth
        "half_rest_template" : cv2.imread("resources/templates/Whole-Half-Rest/1.png"),    #possible to find this in beamed notes
        "quarter_rest_template" : cv2.imread("resources/templates/Quarter-Rest/1.png"),
        "eigth_rest_template" : cv2.imread("resources/templates/Eigth-Rest/1.png"),
        "eigth_note_template" : [cv2.imread(f"resources/templates/Eigth-Note/{i}.png") for i in range(1,6)],
        "sharp_template" : cv2.imread("resources/templates/Sharp/1.png"),
        "timesignature_template" : cv2.imread("resources/templates/Time-Signature/4-4-Time.png"),
        "clef_template" : [cv2.imread("resources/templates/Clef/Treble-Clef.png"), cv2.imread("resources/templates/Clef/Bass-Clef.png")],
        #"barline_template" : cv2.imread("resources/templates/Bar-Line.png"),
        #"dot_template" : cv2.imread("resources/templates/Dot.png")
    }
    template_thresholds = {
        "whole_note_template" : [0.75],
        "half_note_template" : [0.8, 0.7],
        "half_rest_template" : [0.9],    
        "quarter_note_template" : [0.8],    
        "quarter_rest_template" : [0.66],
        "eigth_note_template" : [0.85, 0.85, 0.8, 0.85, 0.85],
        "eigth_rest_template" : [0.8],
        "sixteenth_note_template" : [0.8],
        "sixteenth_rest_template" : [0.8],
        "timesignature_template" : [0.8],
        "clef_template" : [0.7, 0.8],
        "barline_template" : [0.93],
        "dot_template" : [0.9],
        "sharp_template" : [0.8]
    }

    matched_symbols = []

    treble_notes = {
        "G5": 79,
        "F5": 77,
        "E5": 76,
        "D5": 74,
        "C5": 72,
        "B4": 71,
        "A4": 69,
        "G4": 67,
        "F4": 65,
        "E4": 64,
        "D4": 62,
        "C4": 60
    }

    staffs = []
    staffs_to_symbol = []


    class MatchedSymbol:

        def __init__(self, symbol_type, x_loc, y_loc, height, width, isRest=False):
            self.symbol_type = symbol_type
            self.x = x_loc
            self.y = y_loc
            self.height = height
            self.width = width
            self.centroid = [0, 0]
            self.boundingBox = None
            self.staff_num = 0
            self.staff_line_num = 0

            self.isNote = True
            self.isRest = isRest
            self.pitch = ""
            self.note_length = 0

            self.staff_line_to_pitch = {
                -1.0 : "A5",
                -0.5 : "G5",
                0.0 : "F5",
                0.5 : "E5",
                1.0 : "D5",
                1.5 : "C5",
                2.0 : "B4",
                2.5 : "A4",
                3.0 : "G4",
                3.5 : "F4",
                4.0 : "E4",
                4.5 : "D4",
                5.0 : "E4",
                5.5 : "D4",
                6.0 : "C4"
            }

        def createBoundingBox(self, image):
            self.boundingBox = image[self.y:self.y + self.height, self.x:self.x + self.width]

        def setPitch(self):
            if not self.isRest:
                self.pitch = self.staff_line_to_pitch[self.staff_line_num]

        def draw(self,index):
            cv2.rectangle(img_copy, (self.x, self.y), (self.x + self.width, self.y + self.height), (0,0,255), 2)
            cv2.putText(img_copy, str(index), (self.x, self.y-11), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 00), 1)
            # if not self.isRest and self.pitch != None:
            #     cv2.putText(img_copy, f"{self.symbol_type}: {self.pitch}", (self.x, self.y-11), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 00), 1)
            # elif self.isRest:
            #     cv2.putText(img_copy, self.symbol_type, (self.x, self.y-11), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 00), 1)


    def findStaffLines():
        
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        edges = cv2.Canny(gray_img, 50, 150, apertureSize = 3)
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 500)

        temp_lines = []
        for idx, line in enumerate(lines):
            rho, theta = line[0]

            x0 = rho * np.cos(theta)
            y0 = rho * np.sin(theta)
        
            x1 = 0
            x2 = image_width

            staff_lines.append([x1, y0, x2, y0])

        staff_lines.sort(key=lambda x: x[1])
        
        for idx, line in enumerate(staff_lines):
            temp_lines.append(line)

            if (idx+1) % 10 == 0 and idx != 0:
                temp_lines.sort(key = lambda l: l[1])
                staff_center_lines = [(temp_lines[i][1] + temp_lines[i-1][1]) / 2 for i in range(1, len(temp_lines), 2)]   #get the center of the staff line by averaging the two edges of the line
                staffs.append(staff_center_lines)
                temp_lines = []

        for x in staffs:
            print(x)
        
        print("Number of Staffs: ", len(staffs))

    
        staff_line_width = staff_lines[1][1] - staff_lines[0][1]
        global staff_space_height
        staff_space_height = staffs[0][1] - staffs[0][0]


    def removeStaffLines():

        for i in range(1, len(staff_lines), 2):
        
            bottom_y_val = int(staff_lines[i][1])
            top_y_val = int(staff_lines[i-1][1])
        
            for x_val in range(0, image_width):
            
                if thresholded_image[top_y_val-1][x_val] == 255 and thresholded_image[bottom_y_val+1][x_val] == 255:
                    for j in range(top_y_val, bottom_y_val+1):
                        no_staff_img[j][x_val] = 255


    def findSymbols():

        for current_template_type in templates_demo.keys():

            print(current_template_type)
            current_template_type = current_template_type[:-9]
            templates = templates_demo[current_template_type + "_template"]
            if not type(templates) is list:
                templates = [templates]

            for idx,template in enumerate(templates):

                threshold = template_thresholds[current_template_type + "_template"][idx]

                best_scale = 0
                most_symbols = 0
                best_locations = []
                best_template = None
                new_symbols = []

                stop_percent = 101
                start_percent = 30

                for scale in [i/100.0 for i in range(start_percent, stop_percent, 5)]:
                    gray_no_staff_img = cv2.cvtColor(no_staff_img, cv2.COLOR_BGR2GRAY)  #do this for mask part below

                    temp_template = cv2.resize(template, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

                    res = cv2.matchTemplate(no_staff_img, temp_template, cv2.TM_CCOEFF_NORMED)
                    temp_symbol_locations = np.where(res >= threshold)    #this will return the upper-left corner of everywhere the template is matched
                    
                    symbol_locations = [[], []]
                    for pt in zip(*temp_symbol_locations):
                        if gray_no_staff_img[pt[0]][pt[1]] == 99:           #this symbol is already represented by a location
                            continue
                        for x in range(-15, 15):
                            for y in range(-15, 15):
                                gray_no_staff_img[pt[0]+y][pt[1]+x] = 99

                        symbol_locations[0].append(pt[0])
                        symbol_locations[1].append(pt[1])

                    num_symbols = len(symbol_locations[0])
                    print(str(scale) + " : " + str(num_symbols) + " : " + str(symbol_locations[1]))

                    if num_symbols > most_symbols:
                        new_symbols = []

                        most_symbols = num_symbols
                        best_scale = scale
                        best_locations = symbol_locations
                        best_template = temp_template

    
                        h, w = best_template.shape[:-1]
                        for pt in zip(*best_locations):
                            if "rest" in current_template_type:
                                new_symbols.append( MatchedSymbol(current_template_type, pt[1], pt[0], h, w, True) )
                            else:
                                new_symbols.append( MatchedSymbol(current_template_type, pt[1], pt[0], h, w) )

                if len(new_symbols) == 0:
                    continue

            
                h, w = best_template.shape[:-1]
                for pt in zip(*best_locations[::-1]):
                    cv2.rectangle(img_copy, pt, (pt[0] + w, pt[1] + h), (0,0,255), 2)

                for new_symbol in new_symbols:
                    matched_symbols.append(new_symbol)


    def findNoteCentroids(thresholded_no_staff_img):
        
        flagged_centroid_found = False
        flagged_centroid = []
        for symbol in matched_symbols:
            symbol.createBoundingBox(thresholded_no_staff_img)

            
            pixel_found = False
            if symbol.isNote:
                if symbol.symbol_type == "whole_note": 
                    symbol.centroid = [int(symbol.height/2), int(symbol.width/2)]   
                
                else:
                
                    if not flagged_centroid_found:
                        for y in range(int(symbol.height/2), symbol.height):
                            if pixel_found: break
                            for x in range(int(symbol.width / 2)):
                                if symbol.boundingBox[y][x] != 255:  
                                    y_centroid_pos = int((symbol.height + y)/2)
                                    flagged_centroid = [y_centroid_pos, int(symbol.width/2)]

                                    pixel_found = True
                                    break

                    symbol.centroid = flagged_centroid


            cv2.circle(img_copy, (symbol.x + symbol.centroid[1], symbol.y + symbol.centroid[0]), 4, (255, 0, 0), -1)



    def assignNotePitches():
        distance_thresh = 5 

        staffs_to_symbol = [[] for i in range(len(staffs))]
        for symbol in matched_symbols:
            symbol_y_loc = symbol.y + symbol.centroid[0]
        
            if symbol.isNote:
                for staff_num, staff in enumerate(staffs):
                    min_distance = 1000
                    for staff_line_num in range(len(staff)):

                        if staff_line_num == 0: 
                            if (abs(symbol_y_loc - (staff[0] - int(staff_space_height/2))) < distance_thresh and
                                    abs(symbol_y_loc - (staff[0] - int(staff_space_height/2))) < min_distance):
                                min_distance = abs(symbol_y_loc - (staff[0] - int(staff_space_height/2)))

                                symbol.staff_num = staff_num
                                symbol.staff_line_num = -0.5
                                symbol.setPitch()

                        
                            if (abs(symbol_y_loc - (staff[4] + staff_space_height)) < distance_thresh and
                                    abs(symbol_y_loc - (staff[4] + staff_space_height)) < min_distance):
                                min_distance = abs(symbol_y_loc - (staff[4] + staff_space_height))

                                symbol.staff_num = staff_num
                                symbol.staff_line_num = 5.0
                                symbol.setPitch()
                    
                        if (abs(symbol_y_loc - staff[staff_line_num]) < distance_thresh and
                                abs(symbol_y_loc - staff[staff_line_num]) < min_distance):
                            min_distance = abs(symbol_y_loc - staff[staff_line_num])

                            symbol.staff_num = staff_num
                            symbol.staff_line_num = staff_line_num
                            symbol.setPitch()

                        if (abs(symbol_y_loc - (staff[staff_line_num] + int(staff_space_height/2))) < distance_thresh and
                                abs(symbol_y_loc - (staff[staff_line_num] + int(staff_space_height/2))) < min_distance):
                            min_distance = abs(symbol_y_loc - (staff[staff_line_num] + int(staff_space_height/2)))

                            symbol.staff_num = staff_num
                            symbol.staff_line_num = staff_line_num + 0.5
                            symbol.setPitch()


        matched_symbols.sort(key=lambda k: [k.staff_num, k.x])
        count = 0
        pos_x = 0
        pos_y = 0

        for symbol in matched_symbols:
            symbol.draw(count)
            # print(str(symbol.x) + " : " + str(symbol.staff_num))

            if symbol.symbol_type == "whole_note":
                symbol.note_length = 4
            elif symbol.symbol_type == "1/2_note":
                symbol.note_length = 2
            elif symbol.symbol_type == "1/4_note":
                symbol.note_length = 1
            elif symbol.symbol_type == "1/8_note":
                symbol.note_length = 0.5
            elif symbol.symbol_type == "1/4_rest":
                symbol.note_length = 1
            elif symbol.symbol_type == "1/8_rest":
                symbol.note_length = 0.5

            if pos_y*20 >= h_img - 20:
                pos_y = 0
                pos_x = pos_x + 180
            if symbol.symbol_type[-4:] != "note":
                cv2.putText(img_copy, f"{count}: {symbol.symbol_type}", (20+pos_x, 20*pos_y+h_img+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 00), 1)
                print(str(count) + " : " + symbol.symbol_type)
            elif not symbol.isRest and symbol.pitch != None:
                cv2.putText(img_copy, f"{count}: {symbol.symbol_type}: {symbol.pitch}", (20+pos_x, 20*pos_y+h_img+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 00), 1)
                print(str(count) + " : " + f"{symbol.symbol_type}: {symbol.pitch}")
            elif symbol.isRest:
                cv2.putText(img_copy, f"{count}: {symbol.symbol_type}", (20+pos_x, 20*pos_y+h_img+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 00), 1)
                print(str(count) + " : " + symbol.symbol_type)
            count = count + 1
            pos_y = pos_y + 1

    findStaffLines()

    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresholded_image = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)

    removeStaffLines()

    gray_no_staff_img = cv2.cvtColor(no_staff_img, cv2.COLOR_BGR2GRAY)
    _, thresholded_no_staff_img = cv2.threshold(gray_no_staff_img, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)


    findSymbols()
    findNoteCentroids(thresholded_no_staff_img)
    assignNotePitches()


    cv2.imwrite("detected.png", img_copy)
    print("Gambar Berhasil Diproses")


