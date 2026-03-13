import numpy as np
from PIL import Image
import os
import cv2
from database_entry import add_data, get_local_session, add_damage_detection_data, add_detection_data, get_local_session_uvision, get_image_id

# import some common detectron2 utilities
# import detectron2
from detectron2 import model_zoo
from detectron2.engine import DefaultPredictor, launch
from detectron2.config import get_cfg
from detectron2.utils.visualizer import Visualizer, ColorMode
# from .det2_draw_bbox import Visualizer, ColorMode
from detectron2.data import MetadataCatalog, DatasetCatalog

# from detectron2.engine import DefaultTrainer
from detectron2.data.datasets import register_coco_instances
from gps_data import get_gps_data
import logging
from concat_l1_l2 import concat_output
import pkg_resources
import argparse
import json
import torch


logging.basicConfig(level=logging.INFO)

def detectron2_inference(src, dest, conf_data, image_id_list):
    conf_data['asset_name'] = dest.split("/")[-1]
    
    try:
        ALLOWED_EXTENSIONS = conf_data.get('ALLOWED_EXTENSIONS', None)
        
        MODEL_DIR = conf_data.get('MODEL_DIR', None)
        MODEL_YAML = conf_data.get('MODEL_YAML', 'COCO-Detection/faster_rcnn_R_101_FPN_3x.yaml')
        MODEL_WEIGHTS = conf_data.get('MODEL_WEIGHTS', None)
        
        
        PADDING = conf_data.get('PADDING', None)
        FONT_SCALE = conf_data.get('FONT_SCALE', 2)
        FONT_THICKNESS =  conf_data.get('FONT_THICKNESS', 8)
        BOUNDING_BOX_THICKNESS =  conf_data.get('BOUNDING_BOX_THICKNESS', 5)
        MIN_THRESHOLD = conf_data.get('MIN_THRESHOLD', None)
        LABEL_LIST = conf_data.get('LABEL_LIST', None)
        NUM_CLASSES = len(LABEL_LIST)

        THRESHOLD_DICT = conf_data.get('THRESHOLD_DICT', None)
        COLOR_LIST = conf_data.get('COLOR_LIST', None)
        COLOR_TEXT_DICT = conf_data.get('COLOR_TEXT_DICT', None)
        COLOR_DICT = conf_data.get('COLOR_DICT', None)
        COLOR_TEXT_LIST = conf_data.get('COLOR_TEXT_LIST', None)    
        COLOR_TEXT_DICT= conf_data.get('COLOR_TEXT_DICT', None)
        VISIBLE_LABELS = conf_data.get('VISIBLE_LABELS', None)        
        GET_CROP = conf_data.get('GET_CROP', None)
        STORE_CROPS_IN_DIFFERENT_FOLDER = conf_data.get('STORE_CROPS_IN_DIFFERENT_FOLDER', None)
        GET_WHOLE_IMAGE = conf_data.get('GET_WHOLE_IMAGE', None)
        GET_DAMAGE_CSV = conf_data.get('GET_DAMAGE_CSV', None)
        DAMAGE_CLASSES = conf_data.get('DAMAGE_CLASSES', None)
        
        STORE_GPS_DATA = conf_data.get('STORE_GPS_DATA', None)
        STORE_IN_MERGED_FOLDER = conf_data.get('STORE_IN_MERGED_FOLDER', False)
        DATASET_NAME= conf_data.get('DATASET_NAME', False)
        DEVICE= conf_data.get('DEVICE', 'cpu')
        ALL_IMAGE_STORE_PATH = conf_data.get('ALL_IMAGE_STORE_PATH', os.path.join(dest, 'all'))
        CROP_IMAGE_STORE_PATH = conf_data.get('CROP_IMAGE_STORE_PATH', os.path.join(dest, 'all'))
        VISIBILITY = conf_data.get('visible', True)
        DETECTION_TYPE = conf_data.get('detection_type')
        ANNOTATION_TYPE = conf_data.get('annotation_type')
        UTILITY_NAME = conf_data.get('utility_name')
        DATA_FROM_DB = conf_data.get('data_from_db')

    except Exception as e:
        logging.error("Conf Data Error : ", e)
        return
    try:
        register_coco_instances(DATASET_NAME, {}, "","")
    except Exception as e:
        logging.error("Failed to register COCO instances : ", str(e))

    print(f'ALL_IMAGE_STORE_PATH 1st :{ALL_IMAGE_STORE_PATH}')
    print(f'CROP_IMAGE_STORE_PATH 1st :{CROP_IMAGE_STORE_PATH}')
    print(f'dest 1st :{dest}')

    cfg = get_cfg()
    cfg.merge_from_file(model_zoo.get_config_file(MODEL_YAML))
    cfg.DATASETS.TEST = ()
    cfg.MODEL.DEVICE=DEVICE
    cfg.MODEL.WEIGHTS = MODEL_WEIGHTS
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = NUM_CLASSES 
    
    # input_images = os.listdir(src)
    
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = MIN_THRESHOLD
    predictor = DefaultPredictor(cfg)

    MetadataCatalog.get(DATASET_NAME).set(thing_classes=LABEL_LIST)
    MetadataCatalog.get(DATASET_NAME).set(thing_colors=COLOR_DICT)
    
    os.makedirs(dest, exist_ok=True)
    os.makedirs(ALL_IMAGE_STORE_PATH, exist_ok=True)
    with open(os.path.join(ALL_IMAGE_STORE_PATH, "data.csv"), "w+") as f:
        f.write("image_name,class_name,cropped_name,left,right,top,bottom,score\n")
    # changes for testing
    if GET_CROP :
        if (not STORE_CROPS_IN_DIFFERENT_FOLDER): 
            if CROP_IMAGE_STORE_PATH == "":
                CROP_IMAGE_STORE_PATH = dest
            os.makedirs(CROP_IMAGE_STORE_PATH, exist_ok=True)
            os.makedirs(os.path.join(CROP_IMAGE_STORE_PATH,'all_crops'),exist_ok=True)
        else:
            if CROP_IMAGE_STORE_PATH == "":
                CROP_IMAGE_STORE_PATH = dest
            os.makedirs(CROP_IMAGE_STORE_PATH, exist_ok=True)
            for i in LABEL_LIST:
                os.makedirs(os.path.join(CROP_IMAGE_STORE_PATH,i), exist_ok=True)

    # input_images = [row["raw_image_name"] for row in image_id_list] # changed

    # if (not STORE_CROPS_IN_DIFFERENT_FOLDER): 
    #     os.makedirs(os.path.join(CROP_IMAGE_STORE_PATH,'all_crops'),exist_ok=True)
    # else:
    #     for i in LABEL_LIST:
    #         os.makedirs(os.path.join(CROP_IMAGE_STORE_PATH,i), exist_ok=True)
    
    if conf_data.get('level')=='2':
        os.makedirs(f"{dest}/",exist_ok=True)

    if GET_DAMAGE_CSV:
        with open(os.path.join(dest, "damage_calc.csv"), "a+") as damage_csv:
            damage_csv.write(f"image_name,2,3,4,5,6,damage_per,damage_found\n")
    
    
    for row in image_id_list:

        file_name = row["raw_image_name"]

        detection_list = []
        damage_consolidation_list = []   

        # if not (file_name.endswith(".jpg") or file_name.endswith(".JPG")):
        #     continue
        if not (file_name.split(".")[-1].lower() in ALLOWED_EXTENSIONS):
            logging.info(f"Extension Not Allowed : Skipping {file_name}....")
            continue
        """
        Load an image from file into a numpy array.
        Puts image into numpy array to feed into tensorflow graph.
        Note that by convention we put it into a numpy array with shape
        (height, width, channels), where channels=3 for RGB.
        uint8 numpy array with shape (img_height, img_width, 3)
        """
        logging.info(f"Processing {file_name} ....")
        
        try:

            im = cv2.imread(os.path.join(src, file_name))

            if DATA_FROM_DB:
                crop_left = int(row['x_min'])
                crop_top = int(row['y_min'])
                crop_right = int(row['x_max'])
                crop_bottom = int(row['y_max'])

                crop_image = im[crop_top:crop_bottom,crop_left:crop_right,:]
                outputs = predictor(crop_image) 

            else:
                outputs = predictor(im)  # format is documented at https://detectron2.readthedocs.io/tutorials/models.html#model-output-format
            # v = Visualizer(im[:, :, ::-1],
            #             scale=0.5, 
            #             metadata = MetadataCatalog.get(DATASET_NAME),
            #             instance_mode=ColorMode(1)
            # )
            # logging.info(outputs["instances"])
            # out = v.draw_instance_predictions(outputs["instances"].to("cpu"))
            
            '''
            crops
            '''

            instances = outputs["instances"]
            # det_Count = instances.num_instances
            boxes = list(instances.pred_boxes)
            scores = instances.scores.tolist()
            pred_classes = instances.pred_classes.tolist()
            det_Count = len(boxes)
            logging.info(f"det_Count: {det_Count}")
            count_dict={}

            image_np_with_detections = im.copy()
            print(image_np_with_detections.shape)
            height_image,width_image,_ = image_np_with_detections.shape
            got_crops = False
            image_pil = Image.open(os.path.join(src, file_name))
            gps_data = None
            if STORE_GPS_DATA:
                gps_data = get_gps_data(image_pil)

            temp = row["unique_id"]

            for s in range(det_Count):
                x_min, y_min, x_max, y_max = list(map(round, boxes[s].tolist()))
                left, top, right, bottom = x_min, y_min, x_max, y_max
                # if w>h:
                #     left,right,top,bottom = top,bottom,left,right
                if PADDING is not None:
                    #left, top, right, bottom = x_min, y_min, x_max, y_max
                #else:
                    # x = lambda a, b : a * b
                    padding_x = round((right - left)*(PADDING/100))
                    padding_y = round((bottom - top)*(PADDING/100))
                    left = left - padding_x
                    right = right + padding_x
                    top = top - padding_y
                    bottom = bottom + padding_y

                    left = 0 if left <= 0 else left
                    top = 0 if top <= 0 else top
                    right = width_image if right >= width_image else right
                    bottom = height_image if bottom >= height_image else bottom
                
                if pred_classes[s] >= NUM_CLASSES:
                    print('label_id error', file_name, pred_classes[s], left, top, right, bottom)
                    with open(os.path.join(ALL_IMAGE_STORE_PATH, f"data.csv"), "a+") as f:
                        f.write(f"{file_name},,{str(left)},{str(right)},{str(top)},{str(bottom)},{str(scores[s])}\n")    
                    continue
                else:
                    class_name = LABEL_LIST[pred_classes[s]]
                    
                if scores[s] < THRESHOLD_DICT[class_name]:
                    continue
                if not VISIBLE_LABELS[class_name]:
                    continue

                color = COLOR_DICT[class_name]
                color_text = COLOR_TEXT_DICT[class_name]
                score = int(scores[s] * 100)
                if class_name not in count_dict.keys():
                    count_dict[class_name]=1
                else:
                    count_dict[class_name]+=1
                
                image_np_with_detections = cv2.rectangle(image_np_with_detections, (int(left), int(
                                top)), (int(right), int(bottom)), color, BOUNDING_BOX_THICKNESS)
                # cv2.putText(image_np_with_detections, ("("+str(score)+"%)"+class_name+str(count_dict[class_name])), (int(left),
                                    # int(top+30*FONT_SCALE)), cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE, color_text, FONT_THICKNESS)
                top = int(top-int(15*FONT_SCALE))
                if top <= 0:
                    top=int(top+int(15*FONT_SCALE))
                if int(left) > image_np_with_detections.shape[1]/2:
                    # cv2.putText(image_np_with_detections, (class_name+str(count_dict[class_name])), (int(left), int(top-int(15*FONT_SCALE))), cv2.FONT_HERSHEY_SIMPLEX, int(FONT_SCALE), (0,255,0), int(FONT_THICKNESS))
                    cv2.putText(image_np_with_detections, ("("+str(score)+"%)"+class_name+str(count_dict[class_name])), (int(left), int(top-int(15*FONT_SCALE))), cv2.FONT_HERSHEY_SIMPLEX, int(FONT_SCALE), (0,255,0), int(FONT_THICKNESS))
                    # cv2.putText(image_np_with_detections, ("("+str(score)+"%)"+class_name+str(count_dict[class_name])), (int(left), int(top-int(10*FONT_SCALE))), cv2.FONT_HERSHEY_SIMPLEX, int(10*FONT_SCALE), (0,255,0), int(FONT_THICKNESS))
                else:
                    # cv2.putText(image_np_with_detections, (class_name+str(count_dict[class_name])), (int(left), int(top-int(15*FONT_SCALE))), cv2.FONT_HERSHEY_SIMPLEX, int(FONT_SCALE), (0,255,0), int(FONT_THICKNESS))
                    cv2.putText(image_np_with_detections, ("("+str(score)+"%)"+class_name+str(count_dict[class_name])), (int(left), int(top-int(15*FONT_SCALE))), cv2.FONT_HERSHEY_SIMPLEX, int(FONT_SCALE), (0,255,0), int(FONT_THICKNESS))
                    # cv2.putText(image_np_with_detections, ("("+str(score)+"%)"+class_name+str(count_dict[class_name])), (int(left), int(top-int(10*FONT_SCALE))), cv2.FONT_HERSHEY_SIMPLEX, int(10*FONT_SCALE), (0,255,0), int(FONT_THICKNESS))
                with open(os.path.join(ALL_IMAGE_STORE_PATH, f"data2.csv"), "a+") as f:
                    f.write(f"{file_name},{class_name},{str(left)},{str(right)},{str(top)},{str(bottom)},{str(score)}\n")    
                got_crops = True
                # if GET_CROP:
                if True:
                    
                    # crop_name = f'{file_name}__{class_name}_{1}.png'
                    crop_name = f'{file_name}__{class_name}_{count_dict[class_name]}.png'
                    with open(os.path.join(ALL_IMAGE_STORE_PATH, f"data.csv"), "a+") as f:
                        f.write(f"{file_name},{class_name},{crop_name},{str(left)},{str(right)},{str(top)},{str(bottom)},{str(scores[s])}\n")
                    
                    if DATA_FROM_DB:
                        left = int(left) + row["x_min"]
                        top = int(top) + row["y_min"]
                        right = int(right) + row["x_min"]
                        bottom = int(bottom) + row["y_min"]
                        visual_name = f"{row["visual_name"]}__{class_name}_{count_dict[class_name]}"

                    else:    
                        row["raw_image_id"] = temp
                        row["unique_id"] = None
                        visual_name = f'{class_name}_{count_dict[class_name]}'

                    detection_list.append({
                            "raw_image_id": row["raw_image_id"],
                            "detected_asset_id": row["unique_id"],                            
                            "class_name": class_name,
                            "x_min": left,
                            "y_min": top,
                            "x_max": right,
                            "y_max": bottom,
                            "score": float(scores[s]),
                            "visible": VISIBILITY,
                            "mask": None,
                            "detection_type": DETECTION_TYPE,
                            "annotation_type": ANNOTATION_TYPE,
                            "visual_name": visual_name
                            }) 
                    
                    # image_pil = Image.open(os.path.join(src, file_name))
                    print("Processing ", file_name)
                    # gps_data = None
                    # if STORE_GPS_DATA:
                    #     gps_data = get_gps_data(image_pil)
                    #del image_pil
                    # if STORE_GPS_DATA and (gps_data != None):
                    #     if STORE_CROPS_IN_DIFFERENT_FOLDER :
                    #         image_pil.crop((left, top, right, bottom)).save(os.path.join(CROP_IMAGE_STORE_PATH, class_name, crop_name), exif=gps_data)
                    #     else:
                    #         image_pil.crop((left, top, right, bottom)).save(os.path.join(CROP_IMAGE_STORE_PATH, 'all_crops', crop_name), exif=gps_data)
                    # else:
                    #     if STORE_CROPS_IN_DIFFERENT_FOLDER :
                    #         image_pil.crop((left, top, right, bottom)).save(os.path.join(CROP_IMAGE_STORE_PATH, class_name, crop_name))
                    #     else:
                    #         image_pil.crop((left, top, right, bottom)).save(os.path.join(CROP_IMAGE_STORE_PATH, 'all_crops', crop_name))
                # if GET_DAMAGE_CSV:
                #     Damage_found = False
                #     if class_name in DAMAGE_CLASSES:
                #         Damage_found = True
                #     if Damage_found:
                #         with open(os.path.join(dest, "damage_calc.csv"), "a+") as damage_csv:
                #             damage_csv.write(f'{file_name},0,0,0,0,0,100, YES \n')
                #     else:
                #         with open(os.path.join(dest, "damage_calc.csv"), "a+") as damage_csv:
                #             damage_csv.write(f'{file_name},0,0,0,0,0,0, NO \n')
                        
                
            output_pil = Image.fromarray(image_np_with_detections[:, :, ::-1])
                
            if got_crops == True and GET_WHOLE_IMAGE: 
                output_pil.save(os.path.join(ALL_IMAGE_STORE_PATH, file_name))
                   

        except Exception as e:
            logging.error("Image Processing Error", file_name, e)
            continue
        

        if GET_DAMAGE_CSV:
            Damage_found = False
            for i in range(det_Count):
                label = LABEL_LIST[pred_classes[i]]
                if label in DAMAGE_CLASSES:
                    Damage_found = True
                    break
            if Damage_found:
                with open(os.path.join(dest, "damage_calc.csv"), "a+") as damage_csv:
                    damage_csv.write(f'{file_name},0,0,0,0,0,100, YES \n')
            else:
                with open(os.path.join(dest, "damage_calc.csv"), "a+") as damage_csv:
                    damage_csv.write(f'{file_name},0,0,0,0,0,0, NO \n')
            if conf_data.get('level')=='2' and Damage_found:
                os.makedirs(f"{dest}/concat/",exist_ok=True)
                concat_name =os.path.join(dest, "concat", file_name)
                # concat_output(file_name,ALL_IMAGE_STORE_PATH,conf_data['project_name'], conf_data['asset_type'],conf_data['asset_name'],"NA",concat_name)

            # damaged_or_not = "Yes" if Damage_found else "No"
            # damage_consolidation_list.append({
            #     "raw_image_id": row["unique_id"],
            #     "detected_asset_id": None,
            #     "good_portion_percentage": None,
            #     "severe_damage_percentage": None,
            #     "moderate_damage_percentage": None,
            #     "total_damage_percentage": None,
            #     "low_damage_percentage": None,
            #     "damaged_or_not": damaged_or_not,
            #     "tilt": None,
            #     "visible": VISIBILITY,
            #     "damage_type": DETECTION_TYPE,
            #     "particular_damage_data": None
            #     }) 
            
        # if damage_consolidation_list:
        #     logging.info(f"detection_dict of {file_name}: {damage_consolidation_list}")    
        #     SessionLocalUvision, engineUvision = get_local_session_uvision()    
        #     add_damage_detection_data(SessionLocal=SessionLocalUvision, detection_list=damage_consolidation_list, model_path=MODEL_WEIGHTS, utility_name=UTILITY_NAME)       


        if detection_list:
            logging.info(f"detection_list of {file_name}: {detection_list}")    
            SessionLocalUvision, engineUvision = get_local_session_uvision()    
            add_detection_data(SessionLocal=SessionLocalUvision, detection_list=detection_list, model_path=MODEL_WEIGHTS, utility_name=UTILITY_NAME)               


if __name__ == '__main__':
    # src = '/mnt/disks/data/uvision/input/CLP/Photos_for_PoC/TOHL_photo_samples_TCS/TOHL photo samples/Defects/Insulator/Insulator/'
    # dest = '/mnt/disks/data/uvision/input/CLP/Photos_for_PoC/TOHL_photo_samples_TCS/TOHL photo samples/Defects/Insulator/Insulator/out/'
    parser = argparse.ArgumentParser(description="My CLI script")
    parser.add_argument("--src", help="Path to the input file")
    parser.add_argument("--dest",  help="Path to the output file")
    parser.add_argument("--device",  help="device to run code ('cuda' for gpu, default is 'cpu')", default='cpu')
    parser.add_argument("--config",  help="Path to the config file")

    parser.add_argument("--assets",  help="List of all the assets to process in pipeline")
    parser.add_argument("--grouped_assets",  help="List of all the assets to process in current task")

    parser.add_argument("--workflow_name",  help="workflow name", default="workflow")
    parser.add_argument("--folder_name",  help="folder name", default="folder")
    parser.add_argument("--start_msg",   help="Array as a string containing names of asset to do Started entry in database jobstatus, e.g-> '[]', '[\"pole\"]'",default='[]')
    parser.add_argument("--end_msg",   help="Array as a string containing names of asset to do Completed entry in database jobstatus, e.g-> '[]', '[\"pole\"]'",default='[]')

    args = parser.parse_args()
    src = args.src 
    dest = args.dest
    device = args.device
    config_path = args.config

    workflow_name = args.workflow_name #'' #{{workflow.name}}
    folder_name = args.folder_name #'' #{{workflow.name}}
    start_msg = json.loads(args.start_msg) #[]
    end_msg = json.loads(args.end_msg) #[]

    assets = json.loads(args.assets)
    grouped_assets = json.loads(args.grouped_assets)

    if grouped_assets != []:
        assets_for_code = list(set(assets).intersection(set(grouped_assets)))
    else:
        assets_for_code = []

    with open(config_path, 'r') as file:
       conf_data = json.load(file)

    if  conf_data.get('DEVICE'):
        conf_data['DEVICE'] = device

    # if conf_data.get('project_name'):
    conf_data['project_name'] = folder_name

    if  conf_data.get('ALL_IMAGE_STORE_PATH'):
        conf_data['ALL_IMAGE_STORE_PATH'] = os.path.join(dest, conf_data.get('ALL_IMAGE_STORE_PATH'))

    if conf_data.get('CROP_IMAGE_STORE_PATH'):
        conf_data['CROP_IMAGE_STORE_PATH'] = os.path.join(dest, conf_data.get('CROP_IMAGE_STORE_PATH'))

    if conf_data.get('SRC_POSTFIX'):
        src = os.path.join(dest, conf_data.get('SRC_POSTFIX'))

    if device != "cuda":
        os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

    if not conf_data["asset"]:
        conf_data["asset"] = grouped_assets

    workorder_id = int(folder_name[:4])

    SessionLocalUvision, engineUvision = get_local_session_uvision()
    image_id_list = get_image_id(SessionLocalUvision, workorder_id, detection_type=conf_data["detection_type"], class_name=conf_data["asset"], data_from_db=conf_data["data_from_db"])
    logging.info(f"image_id_list: {image_id_list}")

    SessionLocal, engine = get_local_session()
    # logging.info(f"start_end_msg: {type(start_msg)}, {type(end_msg)}")
    if start_msg:
        for asset in start_msg:
            add_data(SessionLocal=SessionLocal, project=folder_name , job_name=workflow_name, status=f'{asset.replace("_"," ").title()} Started !')

    try:        
        detectron2_inference(src, dest, conf_data, image_id_list)
        if end_msg:
            for asset in end_msg:
                add_data(SessionLocal=SessionLocal, project=folder_name , job_name=workflow_name, status=f'{asset.replace("_"," ").title()} Completed !')

    except Exception as e: 
        logging.error(str(e))
        if end_msg:
            for asset in end_msg:
                add_data(SessionLocal=SessionLocal, project=folder_name , job_name=workflow_name, status=f'{asset.replace("_"," ").title()} Completed !')

    

    
    # dest_l1 = os.path.join(dest, "Level1")
    # dest_all_folder = os.path.join(dest, "Level2", 'all_big_assets')
    
    # conf_data = {
    #     'MODEL_WEIGHTS': os.path.join('/mnt/disks/infengine-dev/inference_engine/uv_inference/run_inference/inference_codes/windmill/models/windmill_damage/windmill_damage.pth'),
    #     'MODEL_YAML': 'COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml',
    #     'ALLOWED_EXTENSIONS': ["jpg", "png", "jpeg"],

    #     'PADDING': 0,
    #     'FONT_SCALE':1,
    #     'FONT_THICKNESS':2,
    #     'BOUNDING_BOX_THICKNESS':2,
    #     'MIN_THRESHOLD': 0.8,
    #     # Put All Labels
    #     'LABEL_LIST': ['dirt', 'damage'],

    #     # Set value True for the labels we want and false for labels we don't want to show
    #     'VISIBLE_LABELS': {'dirt': True, 'damage': True},
    #     'THRESHOLD_DICT': {'dirt': 0.8, 'damage': 0.8},
    #     'COLOR_DICT': {'dirt':(0,0,0), 'damage':(255,255,255)},
    #     'COLOR_TEXT_DICT': {'dirt':(0,0,0), 'damage':(255,255,255)},
        

    #     'GET_CROP': True,  # normal foldername,
    #     'GET_WHOLE_IMAGE': True,

    #     'GET_DAMAGE_CSV': True,  # damage_calc.csv,
    #     'DAMAGE_CLASSES': ['dirt', 'damage'],
    #     'STORE_IN_MERGED_FOLDER': True,

    #     'STORE_GPS_DATA': True,
    #     'DATASET_NAME': 'wind_mill',
    #     'ALL_IMAGE_STORE_PATH': dest_all_folder,
    #     # 'level':'2',
    #     # 'asset_name': dest.split("/")[-1],
    #     # 'asset_type':'big',
    #     'project_name':'windmill',
    #     'STORE_CROPS_IN_DIFFERENT_FOLDER' : True
    
    # }

    # conf_data = {
    #     'MODEL_WEIGHTS': 'run_inference/inference_codes/ukpn_v2/models/disc_damage_l2/disc_damage_l2.pth',
    #     'MODEL_YAML': 'COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml',
    #     'ALLOWED_EXTENSIONS': ["jpg", "png", "jpeg"],
    #     'DATASET_NAME': 'disc_damage_all',
 
    #     'PADDING': 0,
    #     'MIN_THRESHOLD': 0.5,
    #     # Put All Labels
    #     'LABEL_LIST': ['disc_no_damage', 'disc_chipped', 'disc_chipped_part', 'disc_flashover', 'disc_missing', 'disc_bird_dropping', 'disc_cap_rusted', 'disc_cap_good', 'disc_damage'],
 
    #     # Set value True for the labels we want and false for labels we don't want to show
    #     'VISIBLE_LABELS': {'disc_no_damage': True, 'disc_chipped': True, 'disc_chipped_part': True, 'disc_flashover': True, 'disc_missing': True, 'disc_bird_dropping': True, 'disc_cap_rusted': True, 'disc_cap_good': True, 'disc_damage': True},
    #     'THRESHOLD_DICT': {'disc_no_damage': 0.5, 'disc_chipped': 0.5, 'disc_chipped_part': 0.5, 'disc_flashover': 0.5, 'disc_missing': 0.1, 'disc_bird_dropping': 0.5, 'disc_cap_rusted': 0.5, 'disc_cap_good': 0.5, 'disc_damage': 0.5},
    #     'COLOR_DICT': {'disc_no_damage': (0,255,0), 'disc_chipped': (0,0,0), 'disc_chipped_part': (0,0,255), 'disc_flashover': (255,0,0), 'disc_missing': (255,0,255), 'disc_bird_dropping': (0,255,255), 'disc_cap_rusted': (255,255,255), 'disc_cap_good': (95,158,160), 'disc_damage': (148,0,211)},
    #     'COLOR_TEXT_DICT': {'disc_no_damage': (0,255,0), 'disc_chipped': (0,0,0), 'disc_chipped_part': (0,0,255), 'disc_flashover': (255,0,0), 'disc_missing': (255,0,255), 'disc_bird_dropping': (0,255,255), 'disc_cap_rusted': (255,255,255), 'disc_cap_good': (95,158,160), 'disc_damage': (148,0,211)},
    #     # 'COLOR_LIST': [(0,255,0),(0,0,0),(0,0,255),(255,0,0),(255,0,255),(0,255,255),(255,255,255),(95,158,160),(148,0,211),],
    #     'GET_CROP': True,  # normal foldername,
    #     'GET_WHOLE_IMAGE': False,
 
    #     'GET_DAMAGE_CSV': False,  # damage_calc.csv,
    #     # 'DAMAGE_CLASSES': [],
    #     'STORE_IN_MERGED_FOLDER': False,
 
    #     'STORE_GPS_DATA': True,
    #     'DATASET_NAME': 'disc_damage_l2',
    #     'ALL_IMAGE_STORE_PATH': dest_all_folder,
    #     'level':'2',
    #     'asset_name': dest.split("/")[-1],
    #     'asset_type':'small_assets_model1',
    #     # 'project_name':data_base_entry_config['project']
    # }
    # detectron2_inference(src, dest_l1, conf_data)