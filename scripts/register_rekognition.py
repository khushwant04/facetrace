"""Register students with AWS Rekognition."""
import sys
sys.path.insert(0, '/home/khushwant/student-face-recognition-saas/backend')

from app.services.aws_rekognition_service import aws_rekognition_service

STUDENTS = {
    "2da68276-ecb5-46f3-86ed-2da4b68d3814": "../images/1AM23CI062.jpg",
    "02bd4a46-d1cc-4677-b47f-327d72467a3f": "../images/1AM23CI038.png",
    "ef54f17b-60ca-4314-a3a5-9a817fc57046": "../images/1AM23CI015.png"
}

def main():
    print("📸 Registering students with AWS Rekognition...\n")
    
    aws_rekognition_service.ensure_collection()
    
    for student_id, image_path in STUDENTS.items():
        print(f"Registering {image_path}...", end=" ")
        
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
        
        result = aws_rekognition_service.index_face(image_bytes, student_id)
        
        if result and result.get('success'):
            print(f"✅ Success!")
        else:
            print(f"❌ Failed")
    
    print("\n✅ Registration complete!")

if __name__ == "__main__":
    main()
