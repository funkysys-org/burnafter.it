from flask import Blueprint, send_file, jsonify
import qrcode
import io

utils_bp = Blueprint('utils', __name__, url_prefix='/api/utils')

@utils_bp.route('/qr', methods=['GET'])
def generate_qr():
    """Generate QR code for a URL"""
    from flask import request

    url = request.args.get('url', '')

    if not url:
        return jsonify({'error': 'URL parameter required'}), 400

    try:
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4
        )
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to bytes
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)

        return send_file(img_buffer, mimetype='image/png')

    except Exception as e:
        return jsonify({'error': f'Failed to generate QR code: {str(e)}'}), 500


@utils_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'burnafterit-api'
    }), 200
