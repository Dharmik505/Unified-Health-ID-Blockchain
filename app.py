from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import hashlib
import json
import qrcode
from io import BytesIO
import base64
from functools import wraps

app = Flask(__name__)
app.secret_key = 'unified-health-id-secret-key'

# In-memory storage (replace with database in production)
patients = {}
doctors = {}
temporary_accesses = {}
medical_records = {}
blockchain_ledger = []

# Blockchain hash function
def create_block_hash(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

# Add to blockchain ledger
def add_to_ledger(action, patient_id, doctor_id, timestamp, details):
    block = {
        'action': action,
        'patient_id': patient_id,
        'doctor_id': doctor_id,
        'timestamp': timestamp,
        'details': details,
        'previous_hash': blockchain_ledger[-1]['hash'] if blockchain_ledger else '0',
    }
    block['hash'] = create_block_hash(block)
    blockchain_ledger.append(block)
    return block['hash']

# Generate QR Code
def generate_qr_code(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format='PNG')
    img_str = base64.b64encode(buf.getvalue()).decode()
    return img_str

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/register-patient', methods=['POST'])
def register_patient():
    data = request.json
    patient_id = f"PT{len(patients) + 1000}"
    patients[patient_id] = {
        'id': patient_id,
        'name': data.get('name'),
        'age': data.get('age'),
        'gender': data.get('gender'),
        'contact': data.get('contact'),
        'blood_group': data.get('blood_group'),
        'allergies': data.get('allergies', []),
        'created_at': datetime.now().isoformat()
    }
    medical_records[patient_id] = []
    return jsonify({'success': True, 'patient_id': patient_id})

@app.route('/api/register-doctor', methods=['POST'])
def register_doctor():
    data = request.json
    doctor_id = f"DR{len(doctors) + 5000}"
    doctors[doctor_id] = {
        'id': doctor_id,
        'name': data.get('name'),
        'specialty': data.get('specialty'),
        'contact': data.get('contact'),
        'hospital': data.get('hospital'),
        'registration': data.get('registration'),
        'created_at': datetime.now().isoformat()
    }
    return jsonify({'success': True, 'doctor_id': doctor_id})

@app.route('/api/add-record', methods=['POST'])
def add_medical_record():
    data = request.json
    patient_id = data.get('patient_id')
    
    if patient_id not in patients:
        return jsonify({'success': False, 'error': 'Patient not found'}), 404
    
    record = {
        'id': f"REC{len(medical_records.get(patient_id, [])) + 1}",
        'type': data.get('type'),
        'description': data.get('description'),
        'date': data.get('date'),
        'doctor_notes': data.get('doctor_notes'),
        'timestamp': datetime.now().isoformat()
    }
    
    medical_records[patient_id].append(record)
    
    # Add to blockchain
    add_to_ledger('ADD_RECORD', patient_id, None, datetime.now().isoformat(), record)
    
    return jsonify({'success': True, 'record_id': record['id']})

@app.route('/api/generate-qr', methods=['POST'])
def generate_qr():
    data = request.json
    patient_id = data.get('patient_id')
    duration = int(data.get('duration', 30))  # minutes
    
    if patient_id not in patients:
        return jsonify({'success': False, 'error': 'Patient not found'}), 404
    
    qr_code_id = f"QR{len(temporary_accesses) + 1}"
    expiry_time = datetime.now() + timedelta(minutes=duration)
    
    temporary_accesses[qr_code_id] = {
        'patient_id': patient_id,
        'created_at': datetime.now().isoformat(),
        'expires_at': expiry_time.isoformat(),
        'accessed_by': [],
        'access_token': create_block_hash(f"{patient_id}{qr_code_id}{datetime.now()}")
    }
    
    qr_data = json.dumps({
        'qr_id': qr_code_id,
        'patient_id': patient_id,
        'token': temporary_accesses[qr_code_id]['access_token'],
        'expires_at': expiry_time.isoformat()
    })
    
    qr_image = generate_qr_code(qr_data)
    
    # Add to blockchain
    add_to_ledger('GENERATE_QR', patient_id, None, datetime.now().isoformat(), {'qr_id': qr_code_id})
    
    return jsonify({
        'success': True,
        'qr_id': qr_code_id,
        'qr_image': qr_image,
        'expires_at': expiry_time.isoformat()
    })

@app.route('/api/verify-qr', methods=['POST'])
def verify_qr():
    data = request.json
    qr_id = data.get('qr_id')
    doctor_id = data.get('doctor_id')
    
    if qr_id not in temporary_accesses:
        return jsonify({'success': False, 'error': 'Invalid QR code'}), 404
    
    access = temporary_accesses[qr_id]
    
    if datetime.fromisoformat(access['expires_at']) < datetime.now():
        return jsonify({'success': False, 'error': 'QR code expired'}), 401
    
    patient_id = access['patient_id']
    patient = patients.get(patient_id)
    records = medical_records.get(patient_id, [])
    
    access['accessed_by'].append({
        'doctor_id': doctor_id,
        'access_time': datetime.now().isoformat()
    })
    
    # Add to blockchain
    add_to_ledger('VIEW_RECORDS', patient_id, doctor_id, datetime.now().isoformat(), {'qr_id': qr_id})
    
    return jsonify({
        'success': True,
        'patient': patient,
        'records': records,
        'verified': True
    })

@app.route('/api/blockchain', methods=['GET'])
def get_blockchain():
    return jsonify({
        'success': True,
        'ledger': blockchain_ledger
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
