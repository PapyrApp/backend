import logging
from flask import request, jsonify, send_file, Blueprint
from mongoengine.errors import DoesNotExist
from marshmallow import ValidationError

from file_manager.ifile_manager import IFileManager
from errors import AuthorizationError
from auth.decorators import token_required
from services import document_service
from services import user_service
from models.user import User
from models.pdf_document import PDFDocument
from schemas.pdf_document_schema import CreatePDFDocumentSchema, UpdatePDFDocumentSchema


def create_document_bp(file_manager: IFileManager):
    document_bp = Blueprint('document', __name__, url_prefix='/api/documents')

    @document_bp.route('/<document_id>', methods=['GET'])
    @token_required
    def get_document(user: User, document_id: int):
        try:
            document = document_service.get_document_check_access(document_id, user.id)
            return jsonify({'data': document.to_mongo().to_dict()}), 200
        except AuthorizationError as e:
            return jsonify({'error': str(e)}), 403
        except DoesNotExist:
            return jsonify({'error': 'Document not found'}), 404
        except Exception as e:
            logging.error(e)
            return jsonify({'error': str(e)}), 500

    @document_bp.route('/<document_id>/download', methods=['GET'])
    @token_required
    def download_document(user: User, document_id: str):
        try:
            document = document_service.get_document_check_access(document_id, user.id)
            document_key = f'{str(document.id)}.pdf'

            if not file_manager.file_exists(document_key):
                return jsonify({'error': 'File not found'}), 404

            file_stream = file_manager.download_file(document_key)
            if not file_stream:
                return jsonify({'error': 'File not found'}), 404

            return send_file(
                file_stream,
                download_name=document_key,
                as_attachment=True
            )
            return jsonify({'data': document.to_mongo().to_dict()}), 200
        except AuthorizationError as e:
            return jsonify({'error': str(e)}), 403
        except DoesNotExist:
            return jsonify({'error': 'Document not found'}), 404
        except Exception as e:
            logging.error(e)
            return jsonify({'error': str(e)}), 500

    @document_bp.route('', methods=['POST'])
    @token_required
    def create_document(user: User):
        file = request.files.get('file')
        data = request.form

        if not file:
            return jsonify({'error': 'Missing file'}), 400

        if not file.filename.endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are allowed'}), 400

        schema = CreatePDFDocumentSchema()
        try:
            validated_data = schema.load(data)
            document = document_service.create_document(
                    str(user.id),
                    **validated_data
            )

            document_key = f'{str(document.id)}.pdf'
            upload_succeeded = file_manager.upload_file(file, document_key)

            if upload_succeeded:
                return jsonify({'data': document.to_mongo().to_dict()}), 201
            else:
                document_service.delete_document(document)
                return jsonify({'error': 'Upload failed'}), 500
        except ValidationError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logging.error(e)
            return jsonify({'error': str(e)}), 500

    @document_bp.route('/<document_id>', methods=['PATCH'])
    @token_required
    def update_document(user: User, document_id: int):
        data = request.get_json()
        schema = UpdatePDFDocumentSchema()
        try:
            validated_data = schema.load(data)
            document = document_service.get_document_check_access(document_id, user.id)

            if user != document.owner:
                return jsonify({'error': 'Only the owner can edit the document'}), 403

            document = document_service.update_document(document, validated_data)
            return jsonify({'data': document.to_mongo().to_dict()}), 201
        except ValidationError as e:
            return jsonify({'error': str(e)}), 400
        except AuthorizationError as e:
            return jsonify({'error': str(e)}), 403
        except DoesNotExist:
            return jsonify({'error': 'Document not found'}), 404
        except Exception as e:
            logging.error(e)
            return jsonify({'error': str(e)}), 500

    @document_bp.route('/<document_id>', methods=['DELETE'])
    @token_required
    def delete_document(user: User, document_id: int):
        try:
            document = document_service.get_document_check_access(document_id, user.id)
            file_path = document.file_path

            if not file_manager.file_exists(file_path):
                return jsonify({'error': 'File not found'}), 404

            if user != document.owner:
                return jsonify({'error': 'Only the owner can delete the document'}), 403

            delete_succeeded = file_manager.delete_file(file_path)

            if not delete_succeeded:
                return jsonify({'error': 'Delete failed'}), 500

            document_service.delete_document(document)
            return jsonify({'data': 'Document deleted successfully'}), 200
        except AuthorizationError as e:
            return jsonify({'error': str(e)}), 403
        except DoesNotExist:
            return jsonify({'error': 'Document not found'}), 404
        except Exception as e:
            logging.error(e)
            return jsonify({'error': str(e)}), 500

    @document_bp.route('/<document_id>/add_collaborator', methods=['POST'])
    @token_required
    def add_collaborator(user: User, document_id: int):
        data = request.get_json()
        email = data.get('email')

        if not email:
            return jsonify({'error': 'Missing required field'}), 400

        try:
            document = document_service.get_document_check_access(document_id, user.id)
            user = user_service.get_user_by_email(email)

            if user in document.collaborators:
                return jsonify({'error': 'User is already a collaborator'}), 400

            if user == document.owner:
                return jsonify({'error': 'User owns the document'}), 400

            document_service.add_collaborator(user, document)
            return jsonify({'data': 'Collaborator added'}), 201
        except PDFDocument.DoesNotExist:
            return jsonify({'error': 'Document not found'}), 404
        except User.DoesNotExist:
            return jsonify({'error': 'User not found'}), 404
        except AuthorizationError as e:
            return jsonify({'error': str(e)}), 403
        except Exception as e:
            logging.error(e)
            return jsonify({'error': str(e)}), 500

    @document_bp.route('/<document_id>/remove_collaborator', methods=['POST'])
    @token_required
    def remove_collaborator(user: User, document_id: int):
        data = request.get_json()
        email = data.get('email')

        if not email:
            return jsonify({'error': 'Missing required field'}), 400

        try:
            document = document_service.get_document_check_access(document_id, user.id)
            user = user_service.get_user_by_email(email)

            if user not in document.collaborators:
                return jsonify({'error': 'User is not a collaborator'}), 400

            if user == document.owner:
                return jsonify({'error': 'User owns the document'}), 400

            document_service.remove_collaborator(user, document)
            return jsonify({'data': 'Collaborator removed'}), 201
        except PDFDocument.DoesNotExist:
            return jsonify({'error': 'Document not found'}), 404
        except User.DoesNotExist:
            return jsonify({'error': 'User not found'}), 404
        except AuthorizationError as e:
            return jsonify({'error': str(e)}), 403
        except Exception as e:
            logging.error(e)
            return jsonify({'error': str(e)}), 500

    @document_bp.route('/<document_id>/share', methods=['GET'])
    @token_required
    def get_share_token(user: User, document_id: int):
        try:
            document = document_service.get_document_check_access(document_id, user.id)
            if document.can_share:
                return jsonify({'data': document.share_token}), 201
            else:
                return jsonify({'error': 'Document is not shareable'}), 400
        except PDFDocument.DoesNotExist:
            return jsonify({'error': 'Document not found'}), 404
        except User.DoesNotExist:
            return jsonify({'error': 'User not found'}), 404
        except AuthorizationError as e:
            return jsonify({'error': str(e)}), 403
        except Exception as e:
            logging.error(e)
            return jsonify({'error': str(e)}), 500

    @document_bp.route('/share/<share_token>', methods=['POST'])
    @token_required
    def use_share_token(user: User, share_token: str):
        try:
            user = user_service.get_user_by_id(user.id)
            document = document_service.get_document_by_share_token(share_token)

            if user in document.collaborators:
                return jsonify({'error': 'User is already a collaborator'}), 400

            if user == document.owner:
                return jsonify({'error': 'User owns the document'}), 400

            if not document.can_share or share_token != document.share_token:
                return jsonify({'error': 'Document is not shareable or token is incorrect'}), 400

            document_service.add_collaborator(user, document)
            return jsonify({'data': 'User added as collaborator'}), 201
        except AuthorizationError as e:
            return jsonify({'error': str(e)}), 403
        except PDFDocument.DoesNotExist:
            return jsonify({'error': 'Document not found'}), 404
        except User.DoesNotExist:
            return jsonify({'error': 'User not found'}), 404
        except Exception as e:
            logging.error(e)
            return jsonify({'error': str(e)}), 500

    return document_bp
