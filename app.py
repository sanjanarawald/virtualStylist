from flask import Flask, render_template, request, jsonify, send_from_directory
import google.generativeai as genai
import os
from werkzeug.utils import secure_filename
from PIL import Image
import io
import base64
import json

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configure the Gemini API
GOOGLE_API_KEY = 'AIzaSyCMk9d5Td3hSLTAGY9rAhz3Af-nwsBtucs'
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Set generation config for better responses
generation_config = {
    'temperature': 0.7,
    'top_p': 0.95,
    'top_k': 40,
    'max_output_tokens': 2048,
}

# System prompt for fashion and beauty analysis
SYSTEM_PROMPT = """You are a professional fashion stylist and beauty consultant with expertise in body type analysis, 
face shape recognition, and personalized style recommendations. Analyze the provided images and provide detailed, 
practical advice including:

1. Body Type Analysis:
   - Identify body shape (hourglass, pear, apple, rectangle, inverted triangle)
   - Note proportions and features to highlight or balance
   - Provide specific clothing recommendations based on body type

2. Face Shape Analysis:
   - Identify face shape (oval, round, square, heart, diamond)
   - Recommend flattering hairstyles, glasses, and makeup techniques
   - Suggest accessories that complement the face shape

3. Color Analysis:
   - Determine skin undertones from the images
   - Recommend flattering color palettes
   - Suggest makeup colors that would work well

4. Personal Style Recommendations:
   - Suggest clothing styles that would be most flattering
   - Recommend specific clothing items and where to find them
   - Provide seasonal wardrobe suggestions

Be specific, practical, and encouraging in your recommendations. If the image quality is insufficient for certain analyses, 
be honest about the limitations and provide general advice that could be helpful."""

@app.route('/')
def home():
    return render_template('index.html')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'webp'}

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_message = request.form.get('message', '')
        uploaded_files = request.files.getlist('images')
        
        image_parts = []
        saved_files = []
        
        # Process uploaded images
        for file in uploaded_files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                saved_files.append(filepath)
                
                # Read and process the image
                with Image.open(filepath) as img:
                    # Convert to RGB if necessary
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Resize if too large while maintaining aspect ratio
                    max_size = (1024, 1024)
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    
                    # Convert to base64
                    buffered = io.BytesIO()
                    img.save(buffered, format="JPEG", quality=85)
                    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    image_parts.append({
                        'mime_type': 'image/jpeg',
                        'data': img_str
                    })
        
        # Prepare the prompt for Gemini
        if not user_message and not image_parts:
            return jsonify({'error': 'No message or images provided'}), 400
        
        # Create the content parts
        parts = [
            {
                'text': SYSTEM_PROMPT + "\n\nUser's message: " + user_message
            }
        ]
        
        # Add images to content parts
        for img in image_parts:
            parts.append({
                'inline_data': {
                    'mime_type': img['mime_type'],
                    'data': img['data']
                }
            })
        
        # Generate response
        response = model.generate_content({
            'parts': parts
        })
        
        # Clean up uploaded files
        for filepath in saved_files:
            try:
                os.remove(filepath)
            except:
                pass
        
        return jsonify({
            'response': response.text,
            'image_count': len(image_parts)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
