import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

def capture_image(mock=True, mock_image_path=None):
    """Captures an image of the finger. Uses mock image if mock=True."""
    logger.info("Capturing image...")
    if mock:
        if mock_image_path:
            return cv2.imread(mock_image_path)
        else:
            # Return a blank white image if no mock image is provided
            return np.ones((480, 640, 3), dtype=np.uint8) * 255
    else:
        # TODO: Implement libcamera or picamera2 capture here
        pass

def segment_nail(image, bbox=None):
    """Isolate the nail bed from the finger cradle, bounded by bbox."""
    logger.info("Segmenting nail bed...")
    if bbox:
        logger.info(f"Using manual bounding box: {bbox}")
    return image

def apply_transformation(image, transform: dict):
    """Apply manual user adjustments: scale, rotation, and translation."""
    if not transform:
        return image
        
    logger.info(f"Applying transformation: {transform}")
    scale = transform.get('scale', 1.0)
    rotation = transform.get('rotation', 0)
    tx = transform.get('x_offset', 0)
    ty = transform.get('y_offset', 0)

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)

    # CSS rotation is clockwise, OpenCV getRotationMatrix2D is counter-clockwise, so we negate rotation
    M = cv2.getRotationMatrix2D(center, -rotation, scale)
    M[0, 2] += tx
    M[1, 2] += ty

    # Warp affine, pad with white border
    transformed = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
    return transformed

def apply_warping(image):
    """Apply 1D Sine-wave pre-distortion to account for nail curvature."""
    logger.info("Applying pre-distortion warping...")
    return image

def halftone_image(image):
    """Convert warped RGB image to CMY and apply Floyd-Steinberg error diffusion."""
    logger.info("Applying halftoning...")
    return np.random.randint(0, 2, size=(image.shape[0], image.shape[1]), dtype=np.uint8)

def packetize(halftoned_image):
    """Pack binary dots into raw byte arrays for ESP32."""
    logger.info("Packetizing data...")
    return [b'\xAA\xBB\xCC' for _ in range(10)]

def run_pipeline(user_image_path: str, bbox: dict = None, transform: dict = None):
    """Runs the full computer vision pipeline."""
    # 1. Capture finger image (to determine nail boundaries if not manual, but here we just use the manual bbox)
    finger_img = capture_image(mock=True)
    
    # 2. Segment nail bed using the manual bbox
    segmented = segment_nail(finger_img, bbox)

    # 3. Load user image
    user_img = cv2.imread(user_image_path)
    if user_img is None:
        raise ValueError(f"Could not read user image from {user_image_path}")

    # Apply manual user transformations
    transformed_img = apply_transformation(user_img, transform)

    # 4. Warp user image to fit nail
    warped = apply_warping(transformed_img)

    # 5. Halftone
    halftoned = halftone_image(warped)

    # 6. Packetize
    packets = packetize(halftoned)

    return packets
