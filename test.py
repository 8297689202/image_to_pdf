import os
import streamlit as st
from PIL import Image
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
import pillow_heif
import pikepdf
from io import BytesIO

pillow_heif.register_heif_opener()


def convert_svg_to_pdf(svg_path):
    """
    Convert an SVG file to a PDF using svglib and reportlab.
    """
    drawing = svg2rlg(svg_path)
    output_pdf = BytesIO()
    renderPDF.drawToFile(drawing, output_pdf)
    output_pdf.seek(0)
    return output_pdf


def compress_image(image_file, target_ratio=0.7, quality=50):
    """
    Compress an image and return a compressed BytesIO object.
    """
    output_image = BytesIO()
    try:
        with Image.open(image_file) as img:
            # Handle PNG with transparency by converting to RGB
            if img.mode == 'RGBA':
                img = img.convert('RGB')  # Converts PNG to RGB

            img = img.resize((int(img.width * target_ratio),
                              int(img.height * target_ratio)))
            img.save(output_image, format='JPEG', quality=quality)
            output_image.seek(0)
        return output_image
    except Exception as e:
        st.error(f"Error compressing image: {str(e)}")


def create_single_pdf_from_images(images, file_names):
    """
    Convert images (compressed or not) to a single PDF.
    """
    output_pdf = BytesIO()
    try:
        with pikepdf.Pdf.new() as pdf:
            for image, file_name in zip(images, file_names):
                img = Image.open(image)

                # Handle PNG with transparency by converting to RGB
                if img.mode == 'RGBA':
                    img = img.convert('RGB')  # Converts PNG to RGB

                img_pdf = BytesIO()
                img.convert('RGB').save(img_pdf, format='PDF', resolution=100)
                img_pdf.seek(0)
                img_pdf_doc = pikepdf.open(img_pdf)
                pdf.pages.extend(img_pdf_doc.pages)
            if len(pdf.pages) > 0:
                pdf.save(output_pdf)
                output_pdf.seek(0)
                return output_pdf
            else:
                st.error("No pages were added to the PDF.")
                return None
    except Exception as e:
        st.error(f"Error creating PDF: {str(e)}")
        return None


def create_individual_pdfs_from_images(images, file_names):
    pdfs = []
    try:
        for image, file_name in zip(images, file_names):
            img_pdf = BytesIO()
            img = Image.open(image)

            # Handle PNG with transparency by converting to RGB
            if img.mode == 'RGBA':
                img = img.convert('RGB')  # Converts PNG to RGB

            img.convert('RGB').save(img_pdf, format='PDF', resolution=100)
            img_pdf.seek(0)
            pdfs.append((img_pdf, file_name))
        return pdfs
    except Exception as e:
        st.error(f"Error creating individual PDFs: {str(e)}")
        return None


st.subheader("Input")

uploaded_files = st.file_uploader(
    "Choose Images",
    accept_multiple_files=True,
    type=["png", "jpeg", "jpg", "heif", "bmp", "tiff", "jfif", "webp"])

if uploaded_files:
    unique_files = {}
    duplicates = False
    for uploaded_file in uploaded_files:
        file_name = uploaded_file.name
        if file_name in unique_files:
            duplicates = True
            break
        unique_files[file_name] = uploaded_file

    if duplicates:
        st.error(
            "Duplicate files detected! Please ensure all uploaded files are unique."
        )
        uploaded_files = []
    else:
        uploaded_files = list(unique_files.values())

compress_option = st.checkbox("Compress images before generating PDF")
compression_ratio = st.number_input("Compression Ratio (%)",
                                    min_value=10,
                                    max_value=100,
                                    value=70)

compression_quality = st.number_input(
    "Select Compression Quality (lower value means more compression but quality will suffer)",
    min_value=10,
    max_value=100,
    value=50)

pdf_option = st.radio(
    "Choose PDF option",
    ("Single PDF for all images", "Individual PDFs for each image"))

if 'compression_changed' not in st.session_state:
    st.session_state.compression_changed = False

if compress_option != st.session_state.compression_changed or pdf_option != st.session_state.get(
        'last_pdf_option', None):
    st.session_state.compression_changed = compress_option
    st.session_state.last_pdf_option = pdf_option
    if 'single_pdf' in st.session_state:
        del st.session_state.single_pdf
    if 'individual_pdfs' in st.session_state:
        del st.session_state.individual_pdfs
    if 'compressed_images' in st.session_state:
        del st.session_state.compressed_images
    if 'file_names' in st.session_state:
        del st.session_state.file_names

if 'processing_complete' not in st.session_state:
    st.session_state.processing_complete = False

st.subheader("Output")

if st.button("Generate PDF") and uploaded_files:
    st.write(f"Number of images uploaded: {len(uploaded_files)}")

    final_images = []
    compressed_images = []
    file_names = [
        os.path.splitext(uploaded_file.name)[0]
        for uploaded_file in uploaded_files
    ]

    if compress_option:
        for image in uploaded_files:
            compressed_img = compress_image(image,
                                            target_ratio=compression_ratio /
                                            100,
                                            quality=compression_quality)
            final_images.append(compressed_img)
            compressed_images.append(compressed_img)
    else:
        final_images = uploaded_files

    if pdf_option == "Single PDF for all images":
        pdf = create_single_pdf_from_images(final_images, file_names)
        if pdf:
            st.session_state.single_pdf = pdf

    else:
        pdfs = create_individual_pdfs_from_images(final_images, file_names)
        if pdfs:
            st.session_state.individual_pdfs = pdfs

    if compress_option and compressed_images:
        st.session_state.compressed_images = compressed_images
        st.session_state.file_names = file_names

    st.session_state.processing_complete = True

if st.session_state.processing_complete:
    if pdf_option == "Single PDF for all images" and 'single_pdf' in st.session_state:
        st.download_button(label="Download Generated PDF",
                           data=st.session_state.single_pdf,
                           file_name="all_images.pdf",
                           mime="application/pdf")

    if pdf_option == "Individual PDFs for each image" and 'individual_pdfs' in st.session_state:
        for i, (pdf, file_name) in enumerate(st.session_state.individual_pdfs):
            st.download_button(label=f"Download {file_name}.pdf",
                               data=pdf,
                               file_name=f"{file_name}.pdf",
                               mime="application/pdf",
                               key=f"pdf_{i}")

    if 'compressed_images' in st.session_state and 'file_names' in st.session_state:
        for i, (img, file_name) in enumerate(
                zip(st.session_state.compressed_images,
                    st.session_state.file_names)):
            st.download_button(label=f"Download Compressed {file_name}.jpg",
                               data=img.getvalue(),
                               file_name=f"{file_name}.jpg",
                               mime="image/jpeg",
                               key=f"compressed_img_{i}")
