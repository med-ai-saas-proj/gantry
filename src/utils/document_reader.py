import io

# from docx import Document


class DocumentReader:

    @classmethod
    async def extract_content(cls, content: bytes) -> str:
        # Basic validation - check if it's a ZIP-based file (DOCX format)
        if not content.startswith(b"PK"):
            raise ValueError(
                "File is not a valid Word document (.docx). Only .docx format is supported."
            )

        try:
            return cls._read_docx(content)
        except Exception as e:
            error_msg = str(e).lower()
            if "no relationship" in error_msg or "officeDocument" in error_msg:
                raise ValueError(
                    "File is not a valid Word document (.docx). Please ensure it's a proper .docx file."
                )
            elif "corrupted" in error_msg or "bad zipfile" in error_msg:
                raise ValueError(
                    "Word document is corrupted or damaged. Please try with a different file."
                )
            else:
                raise ValueError(f"Failed to read Word document: {str(e)}")

    @classmethod
    def _read_docx(cls, file_bytes: bytes) -> str:
        """Read Word document with proper error handling"""
        doc = Document(io.BytesIO(file_bytes))
        paragraphs = []

        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                paragraphs.append(paragraph.text)

        if not paragraphs:
            return "Document appears to be empty or contains no readable text."

        return "\n".join(paragraphs)
