import argparse
import pickle
from collections import Counter
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np
import face_recognition

DEFAULT_ENCODINGS_PATH = Path("../output/encodings.pkl")
BOUNDING_BOX_COLOR = "blue"
TEXT_COLOR = "white"

#CLI 설정
parser = argparse.ArgumentParser(description="Recognize faces in an image")
parser.add_argument("--train", action="store_true", help="Train on input data")
parser.add_argument("--validate", action="store_true", help="Validate trained model")
parser.add_argument("--test", action="store_true", help="Test the model with an unknown image")
parser.add_argument("-m", action="store", default="hog", choices=["hog", "cnn"], help="Which model to use for training: hog (CPU), cnn (GPU)")
parser.add_argument("-f", action="store", help="Path to an image with an unknown face")
parser.add_argument("--compare", action="store_true", help="Compare faces between two images")
parser.add_argument("--image1", action="store", help="Path to the first image")
parser.add_argument("--image2", action="store", help="Path to the second image")
args = parser.parse_args()

#저장소 생성
Path("../training").mkdir(exist_ok=True)
Path("../output").mkdir(exist_ok=True)
Path("../validation").mkdir(exist_ok=True)

#이미지 형식 변경 함수
def load_image(file_path):
    image = Image.open(file_path)
    print(f"Image mode before conversion: {image.mode}")
    if image.mode != 'RGB':
        image = image.convert('RGB')
    print(f"Image mode after conversion: {image.mode}")
    return np.array(image)

#학습 데이터 인코딩
def encode_known_faces(model: str = "hog", encodings_location: Path = DEFAULT_ENCODINGS_PATH) -> None:
    names = []
    encodings = []
    for filepath in Path("../training").glob("*/*"):
        name = filepath.parent.name
        image = load_image(filepath)
        face_locations = face_recognition.face_locations(image, model=model)
        face_encodings = face_recognition.face_encodings(image, face_locations)
        for encoding in face_encodings:
            names.append(name)
            encodings.append(encoding)
    name_encodings = {"names": names, "encodings": encodings}
    with encodings_location.open(mode="wb") as f:
        pickle.dump(name_encodings, f)

#비교 인식 함수
def recognize_faces(image_location: str, model: str = "hog", encodings_location: Path = DEFAULT_ENCODINGS_PATH) -> None:
    with encodings_location.open(mode="rb") as f:
        loaded_encodings = pickle.load(f)
    input_image = load_image(image_location)
    input_face_locations = face_recognition.face_locations(input_image, model=model)
    input_face_encodings = face_recognition.face_encodings(input_image, input_face_locations)
    pillow_image = Image.fromarray(input_image)
    draw = ImageDraw.Draw(pillow_image)
    for bounding_box, unknown_encoding in zip(input_face_locations, input_face_encodings):
        name = _recognize_face(unknown_encoding, loaded_encodings)
        if not name:
            name = "Unknown"
        _display_face(draw, bounding_box, name)
    del draw
    pillow_image.show()

#이름 매칭 함수
def _recognize_face(unknown_encoding, loaded_encodings):
    boolean_matches = face_recognition.compare_faces(loaded_encodings["encodings"], unknown_encoding)
    votes = Counter(name for match, name in zip(boolean_matches, loaded_encodings["names"]) if match)
    if votes:
        return votes.most_common(1)[0][0]

#얼굴 범위 표시 함수
def _display_face(draw, bounding_box, name): 
    top, right, bottom, left = bounding_box
    draw.rectangle(((left, top), (right, bottom)), outline=BOUNDING_BOX_COLOR)
    text_left, text_top, text_right, text_bottom = draw.textbbox((left, bottom), name)
    draw.rectangle(((text_left, text_top), (text_right, text_bottom)), fill="blue", outline="blue")
    draw.text((text_left, text_top), name, fill="white")

#validate 안의 사진 파일 전부 검증
def validate(model: str = "hog"):
    for filepath in Path("../validation").rglob("*"):
        if filepath.is_file():
            recognize_faces(image_location=str(filepath.absolute()), model=model)

#두 인물 대조 함수
def compare_faces(image1_path: str, image2_path: str, model: str = "hog", # 얼굴 비교 검증 함수
                  encodings_location: Path = DEFAULT_ENCODINGS_PATH) -> None:
    with encodings_location.open(mode="rb") as f:
        loaded_encodings = pickle.load(f)

    # 첫 번째 이미지 로드 및 인코딩
    image1 = load_image(image1_path)
    face_locations1 = face_recognition.face_locations(image1, model=model)
    face_encodings1 = face_recognition.face_encodings(image1, face_locations1)

    # 두 번째 이미지 로드 및 인코딩
    image2 = load_image(image2_path)
    face_locations2 = face_recognition.face_locations(image2, model=model)
    face_encodings2 = face_recognition.face_encodings(image2, face_locations2)

    # 얼굴 비교
    for encoding1 in face_encodings1:
        results = face_recognition.compare_faces(face_encodings2, encoding1)
        distances = face_recognition.face_distance(face_encodings2, encoding1)
        print(f"Results: {results}")
        print(f"Distances: {distances}")


#메인함수
if __name__ == "__main__":
    if args.train:
        encode_known_faces(model=args.m)
    if args.validate:
        validate(model=args.m)
    if args.test:
        recognize_faces(image_location=args.f, model=args.m)
