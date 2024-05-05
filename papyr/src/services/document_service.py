from typing import List, Dict
from datetime import datetime
from models.pdf_document import PDFDocument


def get_document(document_id: int) -> PDFDocument:
    return PDFDocument.objects(id=document_id).get()


def get_documents(user_id: int) -> List[PDFDocument]:
    return list(PDFDocument.objects(user_id=user_id).all())


def create_document(document_data: Dict) -> PDFDocument:
    if PDFDocument.objects(title=document_data['title']).first():
        raise ValueError('Document with this title already exists')

    new_document = PDFDocument(
        owner_id=document_data['owner_id'],
        file_path=document_data['file_path'],
        title=document_data['title'],
        description=document_data.get('description', '')
    )
    new_document.save()
    return new_document


def update_document(document: PDFDocument, document_data: Dict) -> PDFDocument:
    document.title = document_data.get('title', document.title)
    document.description = document_data.get('description', document.description)
    document.file_path = document_data.get('file_path', document.file_path)
    document.updated_at = datetime.now()
    document.save()


def delete_document(document_id: int):
    document = PDFDocument.objects(id=document_id).get()
    document.delete()
