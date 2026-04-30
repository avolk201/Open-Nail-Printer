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
    h, w = image.shape[:2]
    map_x = np.zeros((h, w), dtype=np.float32)
    map_y = np.zeros((h, w), dtype=np.float32)
    
    for y in range(h):
        map_y[y, :] = y
        
    x = np.arange(w, dtype=np.float32)
    nx = (x - w / 2) / (w / 2)
    # Apply a gentle arcsin-like mapping via sine to stretch edges for printing
    nx_mapped = np.sin(nx * np.pi / 2.5) 
    map_x[:] = (nx_mapped * w / 2) + w / 2
    
    warped = cv2.remap(image, map_x, map_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
    return warped

def halftone_image(image):
    """Convert warped RGB image to CMY and apply Floyd-Steinberg error diffusion."""
    logger.info("Applying halftoning...")
    b, g, r = cv2.split(image)
    c = 255 - r
    m = 255 - g
    y_ch = 255 - b
    
    cmy = np.dstack((c, m, y_ch)).astype(np.float32) / 255.0
    h, w = cmy.shape[:2]
    
    for y_idx in range(h):
        for x_idx in range(w):
            old_pixel = cmy[y_idx, x_idx].copy()
            new_pixel = np.round(old_pixel)
            cmy[y_idx, x_idx] = new_pixel
            error = old_pixel - new_pixel
            
            if x_idx + 1 < w:
                cmy[y_idx, x_idx + 1] += error * 7 / 16
            if y_idx + 1 < h:
                if x_idx > 0:
                    cmy[y_idx + 1, x_idx - 1] += error * 3 / 16
                cmy[y_idx + 1, x_idx] += error * 5 / 16
                if x_idx + 1 < w:
                    cmy[y_idx + 1, x_idx + 1] += error * 1 / 16
                    
    cmy = np.clip(cmy, 0, 1)
    binary_cmy = (cmy * 255).astype(np.uint8)
    return binary_cmy

def packetize(halftoned_image):
    """Pack binary dots into raw byte arrays for ESP32."""
    logger.info("Packetizing data...")
    # Convert from 0/255 to 0/1 bits
    binary_data = (halftoned_image > 127).astype(np.uint8)
    flat_data = binary_data.flatten()
    packed_bytes = np.packbits(flat_data)
    
    payloads = []
    for i in range(0, len(packed_bytes), 42):
        chunk = packed_bytes[i:i+42]
        if len(chunk) < 42:
            chunk = np.pad(chunk, (0, 42 - len(chunk)), mode='constant')
        payloads.append(chunk.tobytes())
    return payloads

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
