
import cv2
import glob
import matplotlib.pyplot as plt
import numpy as np
import pickle
from scipy.ndimage.measurements import label
from skimage.feature import hog
from sklearn.preprocessing import StandardScaler

from parameters import Prms

class dip:
    '''Digital Image Processing functions for vehicle detection'''

    def read_image(img):
        '''Returns an RGB image scaled from (0, 255) using cv2'''
        image = cv2.imread(img)
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    def convertImageForColorspace(image, color_space):
        '''Convert the image to the requested colorspace'''
        
        if color_space != 'RGB':
            if color_space == 'HSV':
                feature_image = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
            elif color_space == 'LUV':
                feature_image = cv2.cvtColor(image, cv2.COLOR_RGB2LUV)
            elif color_space == 'HLS':
                feature_image = cv2.cvtColor(image, cv2.COLOR_RGB2HLS)
            elif color_space == 'YUV':
                feature_image = cv2.cvtColor(image, cv2.COLOR_RGB2YUV)
            elif color_space == 'YCrCb':
                feature_image = cv2.cvtColor(image, cv2.COLOR_RGB2YCrCb)
        else: feature_image = np.copy(image)
        
        # Return the converted image
        return feature_image

    def colorspace2RGB(image, color_space):
        '''Convert the image back to RGB'''
            
        # Convert the image to RGB from the its original colorspace
        if color_space != 'RGB':
            if color_space == 'HSV':
                feature_image = cv2.cvtColor(image, cv2.COLOR_HSV2RGB)
            elif color_space == 'LUV':
                feature_image = cv2.cvtColor(image, cv2.COLOR_LUV2RGB)
            elif color_space == 'HLS':
                feature_image = cv2.cvtColor(image, cv2.COLOR_HLS2RGB)
            elif color_space == 'YUV':
                feature_image = cv2.cvtColor(image, cv2.COLOR_YUV2RGB)
            elif color_space == 'YCrCb':
                feature_image = cv2.cvtColor(image, cv2.COLOR_YCrCb2RGB)
        else: feature_image = np.copy(image)
        
        # Return the RGB image
        return feature_image

    def draw_boxes(img, bboxes, color=(0, 0, 255), thick=6):
        '''
        Takes an image, a list of bounding boxes, and optional color tuple
        and line thickness as inputs then draws boxes in that color on
        the output
        '''

        # Make a copy of the image
        draw_img = np.copy(img)
        
        # Iterate through the bounding boxes
        for bbox in bboxes:
            # Draw a rectangle given bbox coordinates
            cv2.rectangle(draw_img, bbox[0], bbox[1], color, thick)
        
        # Return the image copy with boxes drawn
        return draw_img

    def find_matches(img, template_list):
        '''
        Searches for template matches and returns a list of bounding boxes
        '''
        
        # Define an empty list to take bbox coords
        bbox_list = []
        
        # Define matching method
        # Alternative options:
        # TM_CCORR_NORMED, TM_CCOEFF, TM_CCORR, TM_SQDIFF, TM_SQDIFF_NORMED
        method = cv2.TM_CCOEFF_NORMED
        
        # Iterate through template list
        for temp in template_list:
            # Read in templates one by one
            tmp = dip.read_image(temp)
            
            # Use cv2.matchTemplate() to search the image
            result = cv2.matchTemplate(img, tmp, method)
            
            # Use cv2.minMaxLoc() to extract the location of the best match
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            # Determine a bounding box for the match
            w, h = (tmp.shape[1], tmp.shape[0])
            if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
                top_left = min_loc
            else:
                top_left = max_loc
            bottom_right = (top_left[0] + w, top_left[1] + h)
            
            # Append bbox position to list
            bbox_list.append((top_left, bottom_right))
        
        # Return the list of bounding boxes
        return bbox_list

    def color_hist(img, nbins=32, bins_range=(0, 256)):
        '''Computes the color histogram features'''
        
        # Compute the histogram of the RGB channels separately
        channel1_hist = np.histogram(img[:,:,0], bins=nbins, range=bins_range)[0]
        channel2_hist = np.histogram(img[:,:,1], bins=nbins, range=bins_range)[0]
        channel3_hist = np.histogram(img[:,:,2], bins=nbins, range=bins_range)[0]
        
        # Stack the histograms into a single feature vector
        hist_features = np.hstack((channel1_hist, channel2_hist, channel3_hist))
        
        # Return the individual histograms, bin_centers and feature vector
        return hist_features

    def bin_spatial(image, size=(16, 16)):
        '''
        Computes color histogram features and returns the feature vector
        '''
        
        features = cv2.resize(image, size).ravel()
        return features

    #------------
    # hog
    #------------

    def get_hog_features(img, orient, pix_per_cell, cell_per_block, vis=False, feature_vec=True):
        '''Returns hog features and visualization'''
        
        if vis == True:
            features, hog_image = hog(img,
                                      orientations=orient,
                                      pixels_per_cell=(pix_per_cell, pix_per_cell),
                                      cells_per_block=(cell_per_block, cell_per_block),
                                      block_norm = 'L2-Hys',
                                      transform_sqrt=True,
                                      visualise=vis,
                                      feature_vector=feature_vec)
            return features, hog_image
        else:
            features = hog(img,
                           orientations=orient,
                           pixels_per_cell=(pix_per_cell, pix_per_cell),
                           cells_per_block=(cell_per_block, cell_per_block),
                           block_norm = 'L2-Hys',
                           transform_sqrt=True,
                           visualise=vis,
                           feature_vector=feature_vec)
            return features

    def combined_features(feature_image, spatial_feat, hist_feat, hog_feat, hist_bins, orient,
                          pix_per_cell, cell_per_block, hog_channel, spatial_size):
        '''Extracts features from an images'''
        
        # list to hold the image features
        file_features = []
        
        # Get the spatial features
        if spatial_feat == True:
            spatial_features = dip.bin_spatial(feature_image, size=spatial_size)
            file_features.append(spatial_features)
        
        # Get the histogram features
        if hist_feat == True:
            hist_features = dip.color_hist(feature_image, nbins=hist_bins)
            file_features.append(hist_features)
        
        # Get the hog features
        if hog_feat == True:
            if hog_channel == 'ALL':
                hog_features = []
                hog_feat1 = dip.get_hog_features(feature_image[:,:,0],
                                                 orient, pix_per_cell, cell_per_block,
                                                 vis=False, feature_vec=True)
                hog_feat2 = dip.get_hog_features(feature_image[:,:,1],
                                                 orient, pix_per_cell, cell_per_block,
                                                 vis=False, feature_vec=True)
                hog_feat3 = dip.get_hog_features(feature_image[:,:,2],
                                                 orient, pix_per_cell, cell_per_block,
                                                 vis=False, feature_vec=True)
                hog_features = np.hstack((hog_feat1, hog_feat2, hog_feat3))
            else:
                feature_image = dip.colorspace2RGB(feature_image, Prms.COLORSPACE)
                feature_image = cv2.cvtColor(feature_image, cv2.COLOR_RGB2GRAY)
                hog_features = dip.get_hog_features(feature_image[:,:], orient,
                                                    pix_per_cell, cell_per_block, vis=False,
                                                    feature_vec=True)
            file_features.append(hog_features)
        
        # Return the features as a list
        return file_features

    def extract_features(imgs, color_space='RGB', spatial_size=(32, 32),
                         hist_bins=32, orient=9,
                         pix_per_cell=8, cell_per_block=2, hog_channel=0,
                         spatial_feat=True, hist_feat=True, hog_feat=True):
        '''Extracts features from a list of images'''
        
        # Create a list to append feature vectors to
        features = []
        
        # Iterate through the list of images
        for file_p in imgs:
            file_features = []
            image = dip.read_image(file_p)

            # Convert the image to the selected colorspace
            feature_image = dip.convertImageForColorspace(image, color_space)
            
            # Get the image features and append them to the list
            file_features = dip.combined_features(feature_image, spatial_feat, hist_feat,
                                                  hog_feat,hist_bins, orient, pix_per_cell,
                                                  cell_per_block, hog_channel, spatial_size)
            features.append(np.concatenate(file_features))

            # Augment the dataset with flipped images and append them to the list
            feature_image=cv2.flip(feature_image, 1)
            file_features = dip.combined_features(feature_image, spatial_feat, hist_feat,
                                                  hog_feat, hist_bins, orient, pix_per_cell,
                                                  cell_per_block, hog_channel, spatial_size)
            features.append(np.concatenate(file_features))
        
        # Return the features as a list
        return features

    def single_img_features(img, color_space='RGB', spatial_size=(32, 32),
                            hist_bins=32, orient=9,
                            pix_per_cell=8, cell_per_block=2, hog_channel=0,
                            spatial_feat=True, hist_feat=True, hog_feat=True):
        '''
        Extracts features from a single image window. This function is very 
        similar to extract_features() just for a single image rather than
        list of images
        '''
        
        #1) Define an empty list to receive features
        img_features = []
        
        #2) Apply color conversion if other than 'RGB'
        feature_image = dip.convertImageForColorspace(img, color_space)
        
        #3) Compute spatial features if flag is set
        if spatial_feat == True:
            spatial_features = dip.bin_spatial(feature_image, size=spatial_size)
            
            #4) Append features to list
            img_features.append(spatial_features)
            
        #5) Compute histogram features if flag is set
        if hist_feat == True:
            hist_features = dip.color_hist(feature_image, nbins=hist_bins)

            #6) Append features to list
            img_features.append(hist_features)

        #7) Compute HOG features if flag is set
        if hog_feat == True:
            if hog_channel == 'ALL':
                hog_features = []
                for channel in range(feature_image.shape[2]):
                    hog_features.extend(dip.get_hog_features(feature_image[:,:,channel],
                                                             orient,
                                                             pix_per_cell,
                                                             cell_per_block,
                                                             vis=False,
                                                             feature_vec=True))
            else:
                hog_features = dip.get_hog_features(feature_image[:,:,hog_channel],
                                                    orient,
                                                    pix_per_cell,
                                                    cell_per_block,
                                                    vis=False,
                                                    feature_vec=True)
            #8) Append features to list
            img_features.append(hog_features)

        #9) Return concatenated array of features
        return np.concatenate(img_features)

    #---------------------
    # Detecion functions
    #---------------------

    def slide_window(img, x_start_stop=[None, None], y_start_stop=[None, None],
                     xy_window=(64, 64), xy_overlap=(0.5, 0.5)):
        '''
        Takes an image, start and stop positions in both x and y,
        window size (x and y dimensions), and overlap
        fraction (for both x and y)
        '''
        
        # If x and/or y start/stop positions not defined, set to image size
        if x_start_stop[0] == None:
            x_start_stop[0] = 0
        if x_start_stop[1] == None:
            x_start_stop[1] = img.shape[1]
        if y_start_stop[0] == None:
            y_start_stop[0] = 0
        if y_start_stop[1] == None:
            y_start_stop[1] = img.shape[0]
        
        # Compute the span of the region to be searched
        xspan = x_start_stop[1] - x_start_stop[0]
        yspan = y_start_stop[1] - y_start_stop[0]

        # Compute the number of pixels per step in x/y
        nx_pix_per_step = np.int(xy_window[0]*(1 - xy_overlap[0]))
        ny_pix_per_step = np.int(xy_window[1]*(1 - xy_overlap[1]))
        
        # Compute the number of windows in x/y
        nx_buffer = np.int(xy_window[0]*(xy_overlap[0]))
        ny_buffer = np.int(xy_window[1]*(xy_overlap[1]))
        nx_windows = np.int((xspan-nx_buffer)/nx_pix_per_step)
        ny_windows = np.int((yspan-ny_buffer)/ny_pix_per_step)

        # Initialize a list to append window positions to
        window_list = []
        
        # Loop through finding x and y window positions
        # Note: you could vectorize this step, but in practice
        # you'll be considering windows one by one with your
        # classifier, so looping makes sense
        for ys in range(ny_windows):
            for xs in range(nx_windows):
                # Calculate window position
                startx = xs*nx_pix_per_step + x_start_stop[0]
                endx = startx + xy_window[0]
                starty = ys*ny_pix_per_step + y_start_stop[0]
                endy = starty + xy_window[1]
                
                # Append window position to list
                window_list.append(((startx, starty), (endx, endy)))

        # Return the list of windows
        return window_list

    def search_windows(img, windows, clf, scaler, color_space='RGB',
                       spatial_size=(32, 32), hist_bins=32, hist_range=(0, 256),
                       orient=9, pix_per_cell=8, cell_per_block=2, hog_channel=0,
                       spatial_feat=True, hist_feat=True, hog_feat=True):
        '''
        Pass an image and the list of windows to be searched (output of slide_windows())
        '''
            
        #1) Create an empty list to receive positive detection windows
        on_windows = []
        
        #2) Iterate over all windows in the list
        for window in windows:
            #3) Extract the test window from original image
            test_img = cv2.resize(img[window[0][1]:window[1][1], window[0][0]:window[1][0]], (64, 64),
                                  interpolation=cv2.INTER_AREA)

            #4) Extract features for that window using single_img_features()
            features = dip.single_img_features(test_img, color_space=color_space,
                                               spatial_size=spatial_size, hist_bins=hist_bins,
                                               orient=orient, pix_per_cell=pix_per_cell,
                                               cell_per_block=cell_per_block,
                                               hog_channel=hog_channel,
                                               spatial_feat=spatial_feat,
                                               hist_feat=hist_feat, hog_feat=hog_feat)
            
            #5) Scale extracted features to be fed to classifier
            test_features = scaler.transform(np.array(features).reshape(1, -1))
            
            #6) Predict using your classifier
            prediction = clf.predict(test_features)
                
            #7) If positive (prediction == 1) then save the window
            if prediction == 1:
                on_windows.append(window)
                    
        #8) Return windows for positive detections
        return on_windows

    def find_cars(img, ystart, ystop, scale, svc, X_scaler, hog_channel,
                  orient, pix_per_cell, cell_per_block, spatial_size, hist_bins,
                  xstart=0, xstop=1280):
        '''
        Extracts features using hog sub-sampling and make predictions
        Returns the detection boxes coordinates as well as an image showing
        the cars that are detected
        '''
        
        # Caution: If the image is comming from the video it is RGB. However, if the
        # image is imported with cv2 it is BGR. This logic is captured in the
        # convert_color() function above.
        
        draw_img = np.copy(img)
        box_list = []
        
        # Crop the image to the prefered search area
        img_tosearch = img[ystart:ystop,xstart:xstop,:]
        ctrans_tosearch = dip.convertImageForColorspace(img_tosearch, Prms.COLORSPACE)
        
        if scale != 1:
            imshape = ctrans_tosearch.shape
            ctrans_tosearch = cv2.resize(ctrans_tosearch, (np.int(imshape[1]/scale), np.int(imshape[0]/scale)))

        # Get the hog channel depending on selection
        if hog_channel == 0 or hog_channel == 'ALL':
            ch1 = ctrans_tosearch[:,:,0]
        if hog_channel == 1 or hog_channel == 'ALL':
            ch2 = ctrans_tosearch[:,:,1]
        if hog_channel == 2 or hog_channel == 'ALL':
            ch3 = ctrans_tosearch[:,:,2]

        # Define blocks and steps as above
        nxblocks = (ch1.shape[1] // pix_per_cell) - cell_per_block + 1
        nyblocks = (ch1.shape[0] // pix_per_cell) - cell_per_block + 1
        nfeat_per_block = orient*cell_per_block**2
        
        # 64 was the orginal sampling rate, with 8 cells and 8 pix per cell
        window = 64
        nblocks_per_window = (window // pix_per_cell) - cell_per_block + 1
        cells_per_step = 2  # Instead of overlap, define how many cells to step
        nxsteps = (nxblocks - nblocks_per_window) // cells_per_step
        nysteps = (nyblocks - nblocks_per_window) // cells_per_step
        
        # Compute individual channel HOG features for the entire image and for the selected channel(s)
        if hog_channel == 0 or hog_channel == 'ALL':
            hog1 = dip.get_hog_features(ch1, orient, pix_per_cell, cell_per_block, feature_vec=False)
        if hog_channel == 1 or hog_channel == 'ALL':
            hog2 = dip.get_hog_features(ch2, orient, pix_per_cell, cell_per_block, feature_vec=False)
        if hog_channel == 2 or hog_channel == 'ALL':
            hog3 = dip.get_hog_features(ch3, orient, pix_per_cell, cell_per_block, feature_vec=False)
        
        for xb in range(nxsteps):
            for yb in range(nysteps):
                ypos = yb*cells_per_step
                xpos = xb*cells_per_step
                
                # Extract HOG for this patch
                if hog_channel == 0 or hog_channel == 'ALL':
                    hog_feat1 = hog1[ypos:ypos+nblocks_per_window, xpos:xpos+nblocks_per_window].ravel()
                    hog_single_channel = hog_feat1
                if hog_channel == 1 or hog_channel == 'ALL':
                    hog_feat2 = hog2[ypos:ypos+nblocks_per_window, xpos:xpos+nblocks_per_window].ravel()
                    hog_single_channel = hog_feat2
                if hog_channel == 2 or hog_channel == 'ALL':
                    hog_feat3 = hog3[ypos:ypos+nblocks_per_window, xpos:xpos+nblocks_per_window].ravel()
                    hog_single_channel = hog_feat3

                # Get the single channel or multi-channel hog features
                if hog_channel == 'ALL':
                    hog_features = np.hstack((hog_feat1, hog_feat2, hog_feat3))
                else:
                    hog_features = hog_single_channel
                
                xleft = xpos*pix_per_cell
                ytop = ypos*pix_per_cell
                
                # Extract the image patch
                subimg = cv2.resize(ctrans_tosearch[ytop:ytop+window, xleft:xleft+window], (64,64))
                
                # Get color features
                spatial_features = dip.bin_spatial(subimg, size=Prms.SPATIAL_SIZE)
                hist_features = dip.color_hist(subimg, nbins=Prms.N_BINS)
                
                # Scale features and make a prediction
                test_features = X_scaler.transform(np.hstack((spatial_features, hist_features, hog_features)).reshape(1, -1))
                test_prediction = svc.predict(test_features)
                
                if test_prediction == 1:
                    xbox_left = np.int(xleft*scale)+xstart
                    ytop_draw = np.int(ytop*scale)
                    win_draw = np.int(window*scale)

                    # Draw the box on the image
                    cv2.rectangle(draw_img,(xbox_left, ytop_draw+ystart),(xbox_left+win_draw,ytop_draw+win_draw+ystart),Prms.LINE_COLOR,Prms.LINE_THICKNESS)

                    # Extract the bbox coordinates
                    box = (xbox_left, ytop_draw+ystart),(xbox_left+win_draw,ytop_draw+win_draw+ystart)
                    box_list.append(box)

        # Return the image with the vehicle detection overlay
        return draw_img, box_list

    #---------
    # Heatmap
    #---------

    def add_heat(heatmap, bbox_list):
        # Iterate through list of bboxes
        for box in bbox_list:
            # Add += 1 for all pixels inside each bbox
            # Assuming each "box" takes the form ((x1, y1), (x2, y2))
            heatmap[box[0][1]:box[1][1], box[0][0]:box[1][0]] += 1
        
        # Return updated heatmap
        return heatmap # Iterate through list of bboxes

    def apply_threshold(heatmap, threshold):
        # Zero out pixels below the threshold
        heatmap[heatmap <= threshold] = 0
        
        # Return thresholded map
        return heatmap

    def draw_labeled_bboxes(img, labels):
        # Iterate through all detected cars
        for car_number in range(1, labels[1]+1):
            # Find pixels with each car_number label value
            nonzero = (labels[0] == car_number).nonzero()
            
            # Identify x and y values of those pixels
            nonzeroy = np.array(nonzero[0])
            nonzerox = np.array(nonzero[1])
            
            # Define a bounding box based on min/max x and y
            bbox = ((np.min(nonzerox), np.min(nonzeroy)), (np.max(nonzerox), np.max(nonzeroy)))
            
            # Draw the box on the image
            cv2.rectangle(img, bbox[0], bbox[1], Prms.LINE_COLOR, Prms.LINE_THICKNESS)
        
        # Return the image
        return img
