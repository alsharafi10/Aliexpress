import cv2
import mediapipe as mp
import numpy as np

def analyze_body_type(image_path: str):
    """
    Analyze the uploaded human image to estimate body shape (H-shape, O-shape, etc.)
    using MediaPipe pose landmarks.
    """
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(static_image_mode=True, min_detection_confidence=0.5)
    
    try:
        image = cv2.imread(image_path)
        if image is None:
            return "Unknown (Invalid Image)"
            
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = pose.process(image_rgb)
        
        if not results.pose_landmarks:
            return "Unknown (No person detected)"
            
        landmarks = results.pose_landmarks.landmark
        
        # Get shoulder coordinates
        left_shoulder = np.array([landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
                                  landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y])
        right_shoulder = np.array([landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x,
                                   landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y])
                                   
        # Get hip coordinates
        left_hip = np.array([landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x,
                             landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y])
        right_hip = np.array([landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x,
                              landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y])

        shoulder_width = np.linalg.norm(left_shoulder - right_shoulder)
        hip_width = np.linalg.norm(left_hip - right_hip)
        
        # Prevent division by zero
        if hip_width == 0:
            return "H-shape (Default)"
            
        ratio = shoulder_width / hip_width
        
        # Basic Body Shape Logic
        body_type = "H-shape (Rectangle)"
        if ratio > 1.2:
            body_type = "Inverted Triangle"
        elif ratio < 0.85:
            body_type = "A-shape (Pear)"
            
        return body_type
        
    except Exception as e:
        print(f"Error analyzing image: {e}")
        return "Unknown"
    finally:
        pose.close()

def analyze_face_shape(image_path: str):
    """Mock implementation of Face Shape / Skin Tone analysis."""
    # In a full app, MediaPipe Face Mesh could be used to extract contours
    return "Warm Skin Tone / Oval Face"
